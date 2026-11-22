"""Monitoring hooks for the two EXISTING Mage pipelines. Never invokes dbt."""
from datetime import datetime,timezone
import json
import os
from uuid import UUID,uuid4

from etl_monitoring.connection import connect as _legacy_test_connect
from etl_monitoring.transaction import (ExecutionContext,Inputs,CommitOutcomeUnknown,
    source_measurements,prepare_export_audit,transactional_export,publish_export,apply_existing_upsert)


def enabled():
    return os.environ.get('AMAZON_MONITORING_ENABLED')=='1'


def connect(autocommit=True):
    """Explicit new environment uses adapter guard; old manual TEST stays compatible."""
    if os.environ.get('ETL_MONITORING_ENV') == 'DEMO':
        from etl_monitoring.pipeline_bridge import DemoSettings
        return DemoSettings().connect(autocommit=autocommit)
    if os.environ.get('ETL_MONITORING_ENV'):
        from etl_monitoring.adapter import Settings
        return Settings.from_env().connect(autocommit=autocommit)
    if os.environ.get('MSSQL_DATABASE') not in (None,'AmazonDeliveryBI_TEST'):
        raise RuntimeError('Explicit ETL_MONITORING environment required for a non-TEST runtime; no fallback')
    return _legacy_test_connect(autocommit=autocommit)


def execute(connection,sql,*params):
    cursor=connection.cursor();result=[]
    try:
        cursor.execute(sql,*params)
        while True:
            if cursor.description:
                columns=[x[0] for x in cursor.description]
                result.extend(dict(zip(columns,row)) for row in cursor.fetchall())
            if not cursor.nextset():break
        return result
    finally:cursor.close()


def context(value):
    data=json.loads(value) if isinstance(value,str) else value
    return ExecutionContext(data['run_id'],data['execution_key'],int(data['attempt_id']))


def start(batch_type,kwargs):
    variables=kwargs.get('variables') or {}
    requested=kwargs.get('monitoring_run_id') or variables.get('monitoring_run_id')
    run_id=str(UUID(str(requested))) if requested else str(uuid4())
    execution_key=str(uuid4())
    pipeline='amazon_delivery_full_load' if batch_type=='FULL_LOAD' else 'amazon_delivery_incremental_load'
    engine_id=(kwargs.get('pipeline_run_id') or kwargs.get('monitoring_native_run_id')
               or (kwargs.get('logging_tags') or {}).get('pipeline_run_id'))
    if engine_id is None:
        engine_id = getattr(kwargs.get('pipeline_run'), 'id', None)
    c=connect()
    try:
        supplied_key=kwargs.get('monitoring_execution_key') or variables.get('monitoring_execution_key')
        supplied_attempt=kwargs.get('monitoring_attempt_id') or variables.get('monitoring_attempt_id')
        evidence_kind=('TEST' if os.environ.get('ETL_MONITORING_ENV')=='DEMO' else 'REAL' if os.environ.get('ETL_MONITORING_ENV')=='PRIMARY'
                       else os.environ.get('AMAZON_EVIDENCE_KIND','TEST'))
        if supplied_key is not None:
            if requested is None or supplied_attempt is None:
                raise ValueError('External execution requires explicit run_id/key/attempt; no time linkage')
            ctx=ExecutionContext(run_id,str(UUID(str(supplied_key))),int(supplied_attempt))
            rows=execute(c,'''SELECT run_id,execution_key,attempt_id FROM monitoring.etl_runs
                WHERE execution_key=? AND run_id=? AND attempt_id=? AND pipeline_name=? AND batch_type=?
                 AND evidence_kind=? AND status='STARTED';''',ctx.execution_key,ctx.run_id,ctx.attempt_id,pipeline,batch_type,evidence_kind)
            if not rows:raise ValueError('External monitoring context is not an active matching execution')
            row=rows[0]
        else:
            row=execute(c,'EXEC monitoring.usp_begin_execution ?,?,?,?,?,?;',execution_key,run_id,pipeline,
                 batch_type,evidence_kind,str(engine_id) if engine_id is not None else None)[0]
        ctx=ExecutionContext(str(row['run_id']),str(row['execution_key']),row['attempt_id'])
        if engine_id is not None:
            execute(c,'''UPDATE monitoring.etl_runs SET mage_pipeline_run_id=COALESCE(mage_pipeline_run_id,?)
                WHERE execution_key=? AND (mage_pipeline_run_id IS NULL OR mage_pipeline_run_id=?);
                IF @@ROWCOUNT<>1 THROW 51000,'Native Mage execution identity conflict',1;''',str(engine_id),ctx.execution_key,str(engine_id))
        start_step(ctx,'mage','MAGE',str(engine_id) if engine_id is not None else None)
        start_step(ctx,'source','SOURCE')
        source=kwargs.get('source_file_path') or variables.get('source_file_path') or 'data/raw/amazon_delivery.csv'
        execute(c,'UPDATE monitoring.etl_runs SET source_file=? WHERE execution_key=?;',str(source),ctx.execution_key)
        return json.dumps({'run_id':ctx.run_id,'execution_key':ctx.execution_key,'attempt_id':ctx.attempt_id})
    finally:c.close()


def start_step(ctx,step,component,external_id=None):
    c=connect()
    try:execute(c,'EXEC monitoring.usp_start_step ?,?,1,?,?;',ctx.execution_key,step,component,external_id)
    finally:c.close()


def finish_step(ctx,step,status,message=None):
    c=connect()
    try:execute(c,'EXEC monitoring.usp_finish_step ?,?,1,?,?;',ctx.execution_key,step,status,message)
    finally:c.close()


def event(ctx,step,severity,message,code=None):
    from etl_monitoring.adapter import redact
    from uuid import uuid5,NAMESPACE_URL
    message=redact(message)
    event_key=str(uuid5(NAMESPACE_URL,ctx.execution_key+step+severity+str(code)+message))
    c=connect()
    try:execute(c,'''IF NOT EXISTS(SELECT 1 FROM monitoring.etl_errors WHERE execution_key=? AND event_key=?)
           INSERT monitoring.etl_errors(execution_key,event_key,step_key,step_attempt,severity,error_code,message)
           VALUES(?,?,?,1,?,?,?);''',ctx.execution_key,event_key,ctx.execution_key,event_key,step,severity,code,message)
    finally:c.close()


def _fail(ctx,step,error):
    """Preserve committed export witnesses; close only steps still active."""
    c=connect()
    try:
        from etl_monitoring.adapter import redact
        from uuid import uuid5,NAMESPACE_URL
        message=redact(error)
        event_key=str(uuid5(NAMESPACE_URL,ctx.execution_key+step+type(error).__name__+message))
        execute(c,'''UPDATE monitoring.etl_step_runs SET status='FAILED',end_time=SYSUTCDATETIME()
          WHERE execution_key=? AND status='STARTED';''',ctx.execution_key)
        execute(c,'''UPDATE monitoring.etl_step_runs SET status='SKIPPED'
          WHERE execution_key=? AND status='NOT_STARTED';''',ctx.execution_key)
        execute(c,'''IF NOT EXISTS(SELECT 1 FROM monitoring.etl_errors WHERE execution_key=? AND event_key=?)
          INSERT monitoring.etl_errors(execution_key,event_key,step_key,step_attempt,severity,error_code,message)
          VALUES(?,?,?,1,'ERROR',?,?);''',ctx.execution_key,event_key,ctx.execution_key,event_key,step,type(error).__name__,message)
        execute(c,'''UPDATE audit.load_batch SET status='FAILED',finished_at=SYSUTCDATETIME(),error_message=?
          WHERE load_batch_id=(SELECT legacy_load_batch_id FROM monitoring.etl_runs WHERE execution_key=?)
            AND status='STARTED';''',message[:4000],ctx.execution_key)
        execute(c,"EXEC monitoring.usp_finish_execution ?,'FAILED';",ctx.execution_key)
    finally:c.close()


def fail(ctx,step,error):
    """Best effort: callers re-raise the original processing error, never this logger."""
    try:
        _fail(ctx,step,error)
        return True
    except Exception:
        import logging
        logging.getLogger(__name__).error('Monitoring failure; original processing exception preserved; reconcile execution')
        return False


def source_completed(value,payload):
    ctx=context(value)
    c=connect()
    try:execute(c,'UPDATE monitoring.etl_runs SET source_file=?,source_checksum=? WHERE execution_key=?;',
                payload['source_file_name'],payload['source_file_checksum'],ctx.execution_key)
    finally:c.close()
    if payload.get('read_error'):
        raise ValueError(payload['read_error'])
    finish_step(ctx,'source','SUCCEEDED')


def validation_completed(payload,result):
    value=payload.get('monitoring_context')
    if not value:return result
    ctx=context(value)
    result['monitoring_context']=value
    measured=source_measurements(payload,result)
    c=connect()
    try:execute(c,'''INSERT monitoring.etl_record_metrics(execution_key,step_key,step_attempt,
        metric_scope,entity_name,measurement_state,records_read,records_valid,records_rejected)
        VALUES(?,'validate',1,'TECHNICAL_VALIDATION','source_csv','OBSERVED',?,?,?);''',
        ctx.execution_key,measured['records_read'],measured['records_valid'],measured['records_rejected'])
    finally:c.close()
    if result.get('validation_error'):
        fail(ctx,'validate',ValueError(result['validation_error']))
    else:
        finish_step(ctx,'validate','SUCCEEDED')
        if result.get('rejection_summary'):event(ctx,'validate','WARNING',result['rejection_summary'])
    return result


def export(payload):
    from mage_project.amazon_delivery_repository import build_output
    ctx=context(payload['monitoring_context'])
    if payload.get('validation_error'):
        raise ValueError(payload['validation_error'])
    start_step(ctx,'export','MAGE')
    inputs=Inputs(int(payload['rows_read']),len(payload['data']),int(payload['rows_rejected']))
    batch_id=str(uuid4())
    c=connect(autocommit=False)
    try:
        prepare_export_audit(c.cursor(),ctx,inputs,payload,batch_id)
        c.commit()
        actions=transactional_export(c,ctx,inputs,
            lambda cur:apply_existing_upsert(cur,payload,batch_id,datetime.now(timezone.utc).replace(tzinfo=None)),
            lambda cur,ct,inp,act:publish_export(cur,ct,inp,act,batch_id))
    except CommitOutcomeUnknown:
        c.close()
        meta=None
        try:
            meta=connect()
            execute(meta,"UPDATE monitoring.etl_runs SET status='IN_DOUBT' WHERE execution_key=?;",ctx.execution_key)
            event(ctx,'export','ERROR','Commit outcome unknown; reconcile before any rerun','COMMIT_UNKNOWN')
        except Exception:
            import logging
            logging.getLogger(__name__).error('Monitoring unavailable during commit reconciliation; original CommitOutcomeUnknown preserved')
        finally:
            if meta is not None:meta.close()
        raise
    except Exception as error:
        c.rollback();fail(ctx,'export',error);raise
    finally:c.close()
    result=build_output(payload,batch_id,'SUCCEEDED',actions.inserted,actions.updated,actions.unchanged,
                        payload.get('rejection_summary') or None)
    result['monitoring_context']=payload['monitoring_context']
    print('MONITORING_EXECUTION '+payload['monitoring_context'])
    return result


def verified(value):
    ctx=context(value)
    finish_step(ctx,'verify','SUCCEEDED')
    finish_step(ctx,'mage','SUCCEEDED')
    c=connect()
    try:execute(c,"EXEC monitoring.usp_finish_execution ?,'WAITING_DBT';",ctx.execution_key)
    finally:c.close()
