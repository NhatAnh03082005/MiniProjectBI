"""Manual artifact recorder. This module NEVER starts Mage, dbt or any process.

prepare -> user runs dbt CLI -> import-result. Explicit IDs only; no time joins.
"""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import json
import math
from pathlib import Path
from uuid import UUID,uuid4
from etl_monitoring.connection import connect,DATABASE
from etl_monitoring.runtime import execute

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'.runtime_test'/'dbt'


def utc(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('UTC offset required')
    return result.astimezone(timezone.utc)


def sqltime(value):return value.astimezone(timezone.utc).replace(tzinfo=None)


def prepare(run_id=None,execution_key=None):
    linked=None;reason=None
    try:
        rid,key=str(UUID(str(run_id))),str(UUID(str(execution_key)))
        c=connect()
        try:
            records=execute(c,'''SELECT r.run_id,r.execution_key,r.attempt_id FROM monitoring.etl_runs r
                JOIN monitoring.etl_step_runs s ON s.execution_key=r.execution_key AND s.step_key='mage'
                WHERE r.run_id=? AND r.execution_key=? AND r.status='WAITING_DBT'
                  AND s.status='SUCCEEDED'
                  AND NOT EXISTS(SELECT 1 FROM monitoring.etl_step_runs d
                    WHERE d.execution_key=r.execution_key AND d.step_key='dbt' AND d.status<>'NOT_STARTED');''',rid,key)
        finally:c.close()
        if records:linked={'run_id':rid,'execution_key':key,'attempt_id':records[0]['attempt_id']}
        else:reason='Supplied IDs do not identify a Mage-success execution awaiting dbt'
    except (ValueError,TypeError):reason='No valid explicit run_id/execution_key pair; independent dbt execution'
    ticket_id=str(uuid4());folder=ARCHIVE/ticket_id
    folder.mkdir(parents=True,exist_ok=False)
    variables={'monitoring_ticket_id':ticket_id}
    if linked:variables.update(monitoring_run_id=linked['run_id'],monitoring_execution_key=linked['execution_key'])
    ticket={'ticket_id':ticket_id,'prepared_at_utc':datetime.now(timezone.utc).isoformat(),
        'target_path':str(folder/'target'),'log_path':str(folder/'logs'),
        'vars_json':json.dumps(variables),'linked':linked,'independent_reason':reason,'evidence_kind':'TEST'}
    path=folder/'ticket.json';path.write_text(json.dumps(ticket,indent=2),encoding='utf-8')
    return path,ticket


def validate_artifacts(ticket,results,manifest,exit_code,expected_database=DATABASE):
    args=results['args'];metadata=results['metadata']
    if args.get('which')!='build':raise ValueError('Recorder expects dbt build, not show/compile/old artifacts')
    variables=args.get('vars') or {}
    if isinstance(variables,str):variables=json.loads(variables)
    expected=json.loads(ticket['vars_json'])
    if any(variables.get(k)!=v for k,v in expected.items()):raise ValueError('Artifact ticket/run identity mismatch')
    invocation=str(UUID(metadata['invocation_id']))
    if invocation!=str(UUID(manifest['metadata']['invocation_id'])):raise ValueError('Manifest/results invocation mismatch')
    start=utc(metadata['invocation_started_at']);generated=utc(metadata['generated_at'])
    prepared=utc(ticket['prepared_at_utc']);now=datetime.now(timezone.utc)
    if not prepared-timedelta(seconds=1)<=start<=generated<=now+timedelta(seconds=1):
        raise ValueError('Stale or invalid artifact timestamps')
    elapsed=float(results['elapsed_time'])
    if not math.isfinite(elapsed) or elapsed<0 or start+timedelta(seconds=elapsed)>now+timedelta(seconds=1):
        raise ValueError('Invalid measured elapsed duration')
    if Path(args['target_path']).resolve()!=Path(ticket['target_path']).resolve():
        raise ValueError('Artifacts must be in the unique ticket target directory')
    for collection in [manifest.get('nodes',{}),manifest.get('sources',{})]:
        for node in collection.values():
            if node.get('database') not in (None,expected_database):raise ValueError('Manifest references a database outside the approved target')
    nodes=results['results']
    if not nodes or len({n['unique_id'] for n in nodes})!=len(nodes):raise ValueError('Empty/duplicate results')
    allowed={'success','pass','warn','error','fail','skipped','runtime error'}
    if any(n['status'] not in allowed for n in nodes):raise ValueError('Unknown dbt node status')
    required={key for key,node in manifest.get('nodes',{}).items()
              if node.get('resource_type') in ('model','test') and node.get('config',{}).get('enabled',True)}
    covered={n['unique_id'] for n in nodes}
    complete=bool(required) and required.issubset(covered)
    success=exit_code==0 and all(n['status'] in ('success','pass','warn') for n in nodes)
    return {'invocation_id':invocation,'start':start,'end':start+timedelta(seconds=float(results['elapsed_time'])),
        'dbt_status':'SUCCEEDED' if success else 'FAILED','complete_graph':complete,'nodes':nodes}


def import_result(ticket_path,exit_code):
    ticket_path=Path(ticket_path).resolve()
    if not ticket_path.is_relative_to(ARCHIVE.resolve()):raise ValueError('Ticket outside TEST archive')
    ticket=json.loads(ticket_path.read_text(encoding='utf-8'))
    target=Path(ticket['target_path']).resolve()
    if target!=ticket_path.parent/'target':raise ValueError('Ticket target path changed')
    result_bytes=(target/'run_results.json').read_bytes()
    manifest_bytes=(target/'manifest.json').read_bytes()
    results=json.loads(result_bytes);manifest=json.loads(manifest_bytes)
    observed=validate_artifacts(ticket,results,manifest,exit_code)
    digest=hashlib.sha256(result_bytes+manifest_bytes).hexdigest()
    c=connect(autocommit=False)
    try:
        duplicate=execute(c,'''SELECT execution_key,artifact_sha256 FROM monitoring.etl_step_runs
              WITH(UPDLOCK,HOLDLOCK) WHERE step_key='dbt' AND dbt_invocation_id=?;''',observed['invocation_id'])
        if duplicate:
            if duplicate[0]['artifact_sha256']!=digest:raise ValueError('Previously imported invocation artifacts changed')
            c.rollback()
            return {'execution_key':str(duplicate[0]['execution_key']),'already_imported':True}
        linked=ticket['linked']
        if linked:
            current=execute(c,'''SELECT r.execution_key FROM monitoring.etl_runs r WITH(UPDLOCK,HOLDLOCK)
                JOIN monitoring.etl_step_runs s ON s.execution_key=r.execution_key AND s.step_key='dbt'
                WHERE r.run_id=? AND r.execution_key=? AND r.status='WAITING_DBT' AND s.status='NOT_STARTED';''',
                linked['run_id'],linked['execution_key'])
            if not current:
                linked=None;ticket['independent_reason']='Explicit execution is no longer awaiting dbt; recorded independently'
        if linked:
            key=linked['execution_key']
        else:
            key=str(uuid4());rid=str(uuid4())
            execute(c,'''INSERT monitoring.etl_runs(execution_key,run_id,attempt_id,pipeline_name,batch_type,
                execution_kind,evidence_kind,status,start_time,metric_definition_version)
                VALUES(?,?,1,'manual_dbt_build','DBT_ONLY','DBT_ONLY',?,'STARTED',?,'DBT_ARTIFACT_V1');''',
                key,rid,ticket['evidence_kind'],sqltime(observed['start']))
            for step,component in [('source','SOURCE'),('mage','MAGE'),('dbt','DBT'),('warehouse','WAREHOUSE')]:
                execute(c,'''INSERT monitoring.etl_step_runs(execution_key,step_key,step_attempt,component,status)
                    VALUES(?,?,1,?,?);''',key,step,component,'SKIPPED' if step in ('source','mage') else 'NOT_STARTED')
        execute(c,'''UPDATE monitoring.etl_step_runs SET status=?,start_time=?,end_time=?,
            dbt_invocation_id=?,dbt_command='build',process_exit_code=?,artifact_verified=1,
            artifact_path=?,artifact_sha256=?,native_duration_seconds=?
            WHERE execution_key=? AND step_key='dbt' AND step_attempt=1 AND status='NOT_STARTED';
            IF @@ROWCOUNT<>1 THROW 51000,'dbt stage is not awaiting an import',1;''',observed['dbt_status'],
            sqltime(observed['start']),sqltime(observed['end']),observed['invocation_id'],exit_code,
            str(target),digest,float(results['elapsed_time']),key)
        for node in observed['nodes']:
            uid=node['unique_id'];step='dbt_node:'+hashlib.sha256(uid.encode()).hexdigest()
            if len(uid)>512:raise ValueError('Node identifier exceeds storage contract')
            times=[(utc(t['started_at']),utc(t['completed_at'])) for t in node.get('timing',[])
                   if t.get('started_at') and t.get('completed_at')]
            native=node['status'];status={'success':'SUCCEEDED','pass':'SUCCEEDED','warn':'SUCCEEDED',
                'fail':'FAILED','error':'FAILED','runtime error':'FAILED','skipped':'SKIPPED'}[native]
            starts=min((t[0] for t in times),default=None);ends=max((t[1] for t in times),default=None)
            if status=='SUCCEEDED' and (starts is None or ends is None):raise ValueError('Successful node has no observed timing')
            resource=manifest.get('nodes',{}).get(uid,{}).get('resource_type',uid.split('.')[0])
            execute(c,'''INSERT monitoring.etl_step_runs(execution_key,step_key,step_attempt,component,
                external_execution_id,dbt_invocation_id,native_status,resource_type,status,start_time,end_time,
                native_duration_seconds,native_failures)
                VALUES(?,?,1,'DBT',?,?,?,?,?,?,?,?,?);''',key,step,uid,observed['invocation_id'],native,resource,status,
                sqltime(starts) if starts else None,sqltime(ends) if ends else None,
                node.get('execution_time'),node.get('failures'))
            if native in ('warn','fail','error','runtime error','skipped'):
                severity='WARNING' if native=='warn' else ('INFO' if native=='skipped' else 'ERROR')
                execute(c,'''INSERT monitoring.etl_errors(execution_key,step_key,step_attempt,severity,error_code,message)
                    VALUES(?,?,1,?,?,?);''',key,step,severity,native,str(node.get('message') or native)[:4000])
        wh_start=c.execute('SELECT SYSUTCDATETIME();').fetchone()[0]
        warehouse_ok=False
        if observed['dbt_status']=='SUCCEEDED' and observed['complete_graph']:
            counts=c.execute('''SELECT (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery),
                (SELECT COUNT_BIG(*) FROM dw.fact_delivery),
                (SELECT COUNT_BIG(DISTINCT staging_row_id) FROM dw.delivery_rejections);''').fetchone()
            warehouse_ok=counts[0]==counts[1]+counts[2]
        wh_end=c.execute('SELECT SYSUTCDATETIME();').fetchone()[0]
        warehouse_status='SUCCEEDED' if warehouse_ok else 'FAILED'
        execute(c,'''UPDATE monitoring.etl_step_runs SET status=?,start_time=?,end_time=?
            WHERE execution_key=? AND step_key='warehouse';''',warehouse_status,wh_start,wh_end,key)
        if not warehouse_ok:
            execute(c,'''INSERT monitoring.etl_errors(execution_key,step_key,step_attempt,severity,error_code,message)
                VALUES(?,'warehouse',1,'ERROR','WAREHOUSE_NOT_VERIFIED',
                'Build failed, required graph incomplete, or raw/fact/rejection reconciliation failed');''',key)
        if ticket.get('independent_reason'):
            execute(c,'''INSERT monitoring.etl_errors(execution_key,severity,error_code,message)
                VALUES(?,'WARNING','INDEPENDENT_DBT',?);''',key,ticket['independent_reason'])
        overall='SUCCEEDED' if observed['dbt_status']=='SUCCEEDED' and warehouse_ok else 'FAILED'
        execute(c,'UPDATE monitoring.etl_runs SET status=?,end_time=? WHERE execution_key=?;',overall,wh_end,key)
        c.commit()
        receipt={'execution_key':key,'linked_to_mage':bool(linked),'invocation_id':observed['invocation_id'],
                 'dbt_status':observed['dbt_status'],'overall_status':overall,'node_count':len(observed['nodes']),
                 'artifact_sha256':digest}
        (ticket_path.parent/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        return receipt
    except BaseException:c.rollback();raise
    finally:c.close()


def record_failure(ticket_path,exit_code,started_at,ended_at,error_file):
    """Record an observed CLI failure without artifacts; no invented invocation ID."""
    path=Path(ticket_path).resolve();error_path=Path(error_file).resolve()
    if not path.is_relative_to(ARCHIVE.resolve()) or not error_path.is_relative_to(path.parent):
        raise ValueError('Failure evidence must reside in the unique TEST ticket directory')
    ticket=json.loads(path.read_text(encoding='utf-8'))
    start,end=utc(started_at),utc(ended_at)
    if exit_code==0 or not utc(ticket['prepared_at_utc'])-timedelta(seconds=1)<=start<=end<=datetime.now(timezone.utc)+timedelta(seconds=1):
        raise ValueError('A failure requires a nonzero exit code and observed timestamps')
    raw=error_path.read_bytes()
    if not raw or datetime.fromtimestamp(error_path.stat().st_mtime,timezone.utc)<utc(ticket['prepared_at_utc']):
        raise ValueError('Empty/stale failure evidence')
    message=raw.decode('utf-8',errors='replace')[-4000:]
    # Failed CLI invocations can still expose a genuine ID in JSON stdout/logs.
    log_ids=set();errors=[]
    for line in raw.decode('utf-8',errors='replace').splitlines():
        try:
            item=json.loads(line);candidate=item.get('info',{}).get('invocation_id')
            if candidate:log_ids.add(str(UUID(candidate)))
            if item.get('info',{}).get('level')=='error':errors.append(item['info'].get('msg',''))
        except (ValueError,TypeError,AttributeError):pass
    invocation=next(iter(log_ids)) if len(log_ids)==1 else None
    if errors:message='\n'.join(errors)[-4000:]
    digest=hashlib.sha256(raw).hexdigest();c=connect(autocommit=False)
    try:
        previous=execute(c,"SELECT execution_key,artifact_sha256 FROM monitoring.etl_step_runs WITH(UPDLOCK,HOLDLOCK) WHERE step_key='dbt' AND artifact_path=?;",str(error_path))
        if previous:
            if previous[0]['artifact_sha256']!=digest:raise ValueError('Failure evidence changed after import')
            c.rollback();return {'execution_key':str(previous[0]['execution_key']),'already_imported':True}
        linked=ticket['linked']
        if linked and not execute(c,'''SELECT r.execution_key FROM monitoring.etl_runs r WITH(UPDLOCK,HOLDLOCK)
            JOIN monitoring.etl_step_runs s ON s.execution_key=r.execution_key AND s.step_key='dbt'
            WHERE r.run_id=? AND r.execution_key=? AND r.status='WAITING_DBT' AND s.status='NOT_STARTED';''',linked['run_id'],linked['execution_key']):linked=None
        if linked:key=linked['execution_key']
        else:
            key=str(uuid4())
            execute(c,'''INSERT monitoring.etl_runs(execution_key,run_id,attempt_id,pipeline_name,batch_type,
                execution_kind,evidence_kind,status,start_time,metric_definition_version)
                VALUES(?,?,1,'manual_dbt_build','DBT_ONLY','DBT_ONLY',?,'STARTED',?,'DBT_ARTIFACT_V1');''',
                key,str(uuid4()),ticket['evidence_kind'],sqltime(start))
            for step,component in [('source','SOURCE'),('mage','MAGE'),('dbt','DBT'),('warehouse','WAREHOUSE')]:
                execute(c,'''INSERT monitoring.etl_step_runs(execution_key,step_key,step_attempt,component,status)
                    VALUES(?,?,1,?,?);''',key,step,component,'NOT_STARTED' if step=='dbt' else 'SKIPPED')
        execute(c,'''UPDATE monitoring.etl_step_runs SET status='FAILED',native_status='process_error',
            start_time=?,end_time=?,process_exit_code=?,dbt_invocation_id=?,artifact_verified=0,artifact_path=?,artifact_sha256=?
            WHERE execution_key=? AND step_key='dbt' AND status='NOT_STARTED';
            IF @@ROWCOUNT<>1 THROW 51000,'dbt step already recorded',1;''',sqltime(start),sqltime(end),exit_code,invocation,str(error_path),digest,key)
        execute(c,"UPDATE monitoring.etl_step_runs SET status='SKIPPED' WHERE execution_key=? AND step_key='warehouse' AND status='NOT_STARTED';",key)
        execute(c,'''INSERT monitoring.etl_errors(execution_key,step_key,step_attempt,severity,error_code,message)
            VALUES(?,'dbt',1,'ERROR','DBT_PROCESS_FAILED_NO_ARTIFACT',?);''',key,message)
        execute(c,"UPDATE monitoring.etl_runs SET status='FAILED',end_time=? WHERE execution_key=?;",sqltime(end),key)
        c.commit()
        return {'execution_key':key,'linked_to_mage':bool(linked),'dbt_status':'FAILED','invocation_id':invocation,'artifact_verified':False}
    except BaseException:c.rollback();raise
    finally:c.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    prep=commands.add_parser('prepare');prep.add_argument('--run-id');prep.add_argument('--execution-key')
    record=commands.add_parser('import-result');record.add_argument('--ticket',required=True)
    record.add_argument('--exit-code',type=int,required=True)
    failure=commands.add_parser('record-failure');failure.add_argument('--ticket',required=True)
    failure.add_argument('--exit-code',required=True,type=int);failure.add_argument('--started-at',required=True)
    failure.add_argument('--ended-at',required=True);failure.add_argument('--error-file',required=True)
    args=parser.parse_args()
    if args.command=='prepare':
        path,ticket=prepare(args.run_id,args.execution_key)
        print(json.dumps({'ticket_path':str(path),**ticket},indent=2))
    elif args.command=='import-result':print(json.dumps(import_result(args.ticket,args.exit_code),indent=2))
    else:print(json.dumps(record_failure(args.ticket,args.exit_code,args.started_at,args.ended_at,args.error_file),indent=2))


if __name__=='__main__':main()
