"""Monitoring integration API v1. No Mage/dbt process launch or business DML.

Legacy manual TEST hooks stay unchanged. New orchestration imports this module.
Lifecycle calls use dedicated autocommit connections. COMMITTED metrics require
the caller's active business transaction; this module never commits that handle.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import os
import re
from uuid import UUID

from etl_monitoring import connection as legacy
from etl_monitoring.runtime import execute
from etl_monitoring.transaction import ExecutionContext, Inputs, Actions

SERVER = r'DESKTOP-OBDFK6B\SQLEXPRESS'
TERMINAL = {'SUCCEEDED', 'FAILED', 'CANCELLED', 'SKIPPED', 'ABANDONED'}


def redact(message):
    text = str(message)
    text = re.sub(r'(?i)\bauthorization\s*[:=]\s*(?:Bearer|Basic)\s+[^\s;,]+', 'authorization=[REDACTED]', text)
    text = re.sub(r'''(?i)\b(password|pwd|token|secret|authorization|api[_-]?key)\s*[:=]\s*(\{[^}]*\}|"[^"]*"|'[^']*'|[^;\s,]+)''', r'\1=[REDACTED]', text)
    return text[:16000]


@dataclass(frozen=True)
class Settings:
    environment: str
    server: str
    database: str
    primary_writes_approved: bool = False
    primary_principal: str | None = None

    def __post_init__(self):
        expected = {'TEST': 'AmazonDeliveryBI_TEST', 'PRIMARY': 'AmazonDeliveryBI'}
        if self.environment not in expected or self.database != expected[self.environment]:
            raise ValueError('Explicit environment/database pair required; no fallback')
        if self.server.lower() not in {SERVER.lower(), r'localhost\sqlexpress', r'.\sqlexpress'}:
            raise ValueError('Unexpected SQL Server')
        if self.primary_principal is not None and (self.environment!='PRIMARY' or self.primary_principal!='AmazonDeliveryBI_Monitoring_Runtime'):
            raise ValueError('Unexpected monitoring-only PRIMARY principal')

    @classmethod
    def from_env(cls):
        return cls(os.environ['ETL_MONITORING_ENV'], os.environ['ETL_MONITORING_SERVER'],
                   os.environ['ETL_MONITORING_DATABASE'],
                   os.environ.get('ETL_MONITORING_PRIMARY_WRITES') == 'APPROVED_PRIMARY',
                   os.environ.get('ETL_MONITORING_PRINCIPAL') or None)

    def verify(self, c):
        row = c.execute("""SELECT CONVERT(nvarchar(128),SERVERPROPERTY('ServerName')),DB_NAME(),
          CONVERT(nvarchar(128),(SELECT value FROM sys.extended_properties
          WHERE class=0 AND name='ETLMonitoring.Environment')),
          IS_SRVROLEMEMBER('sysadmin'),IS_MEMBER('etl_monitoring_writer')""").fetchone()
        if tuple(row[:3]) != (SERVER, self.database, 'APPROVED_' + self.environment):
            raise RuntimeError('Monitoring target/environment marker mismatch')
        if self.environment == 'PRIMARY' and (not self.primary_writes_approved or row[3] != 0 or row[4] != 1):
            raise RuntimeError('PRIMARY requires approval and a non-sysadmin monitoring writer')
        if self.primary_principal and c.execute('SELECT SUSER_SNAME()').fetchone()[0]!=self.primary_principal:
            raise RuntimeError('Monitoring principal mismatch')
        contract=c.execute("""SELECT CASE WHEN COL_LENGTH('monitoring.etl_errors','event_key') IS NOT NULL
          AND EXISTS(SELECT 1 FROM sys.parameters WHERE object_id=OBJECT_ID('monitoring.usp_finish_step') AND name='@artifact_sha256')
          AND (SELECT COUNT(*) FROM sys.views WHERE schema_id=SCHEMA_ID('monitoring')
            AND name IN ('vw_etl_run_summary','vw_etl_record_metrics','vw_etl_step_status','vw_etl_error_details'))=4
          THEN 1 ELSE 0 END""").fetchone()[0]
        if contract != 1:
            raise RuntimeError('Monitoring infrastructure contract incomplete; deploy and validate before logging')

    def connect(self, autocommit=True):
        if self.environment == 'PRIMARY' and not self.primary_writes_approved:
            raise RuntimeError('PRIMARY monitoring writes not approved')
        if self.environment == 'PRIMARY' and os.environ.get('AMAZON_TEST_CONNECTIONS') == '1':
            raise RuntimeError('A TEST-guarded process cannot open PRIMARY')
        if self.environment == 'TEST':
            c = legacy.connect(autocommit=autocommit)
        else:
            # Windows auth only; no persisted credentials, profile fallback or impersonation.
            legacy.pyodbc.pooling = False
            c = legacy._original_connect(
                f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={self.server};'
                f'DATABASE={self.database};Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;',
                autocommit=True, timeout=5)
            if self.primary_principal:
                try:
                    if c.execute('SELECT SUSER_SNAME()').fetchone()[0]!=self.primary_principal:
                        # NO REVERT must be an ad-hoc batch, not a parameterized
                        # sp_prepexec. __post_init__ accepts this one identity only.
                        c.execute("EXECUTE AS LOGIN='AmazonDeliveryBI_Monitoring_Runtime' WITH NO REVERT;")
                except BaseException:
                    c.close()
                    raise
        try:
            self.verify(c)
            c.execute('''SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000; SET QUOTED_IDENTIFIER ON;
                SET ANSI_NULLS ON; SET ANSI_PADDING ON; SET ANSI_WARNINGS ON; SET ARITHABORT ON;
                SET CONCAT_NULL_YIELDS_NULL ON; SET NUMERIC_ROUNDABORT OFF;''')
            c.autocommit=autocommit
            return c
        except BaseException:
            c.close()
            raise


class MonitoringAdapter:
    def __init__(self, settings):
        self.settings = settings

    @contextmanager
    def _connection(self):
        c = self.settings.connect()
        try:
            yield c
        finally:
            c.close()

    def _context(self, c, ctx):
        row = execute(c, 'SELECT run_id,attempt_id FROM monitoring.etl_runs WHERE execution_key=?', ctx.execution_key)
        if not row or str(row[0]['run_id']).lower() != ctx.run_id.lower() or row[0]['attempt_id'] != ctx.attempt_id:
            raise ValueError('Run/execution/attempt context mismatch')

    def start_run(self, *, run_id, execution_key, pipeline_name, batch_type,
                  native_mage_run_id=None, execution_kind='MAGE_DBT',source_file=None,source_checksum=None):
        # Caller persists both UUIDs BEFORE the call and reuses them after lost ACK.
        run_id, execution_key = str(UUID(str(run_id))), str(UUID(str(execution_key)))
        with self._connection() as c:
            row = execute(c, 'EXEC monitoring.usp_begin_execution ?,?,?,?,?,?,?',
                          execution_key, run_id, pipeline_name, batch_type,
                          'REAL' if self.settings.environment == 'PRIMARY' else 'TEST',
                          str(native_mage_run_id) if native_mage_run_id is not None else None,
                          execution_kind)[0]
            ctx=ExecutionContext(str(row['run_id']), str(row['execution_key']), row['attempt_id'])
        if source_file is not None or source_checksum is not None:
            self.bind_metadata(ctx,source_file=source_file,source_checksum=source_checksum)
        return ctx

    def bind_metadata(self, ctx, *, source_file=None,source_checksum=None,legacy_load_batch_id=None):
        """Bind observed source/legacy lineage once; identical ACK retry is allowed."""
        if source_checksum is not None and not re.fullmatch('[0-9a-fA-F]{64}',source_checksum):
            raise ValueError('Expected observed SHA-256 source checksum')
        with self._connection() as c:
            self._context(c,ctx)
            execute(c, '''UPDATE monitoring.etl_runs SET source_file=COALESCE(source_file,?),
                source_checksum=COALESCE(source_checksum,?),legacy_load_batch_id=COALESCE(legacy_load_batch_id,?)
                WHERE execution_key=? AND (source_file IS NULL OR ? IS NULL OR source_file=?)
                 AND (source_checksum IS NULL OR ? IS NULL OR source_checksum=?)
                 AND (legacy_load_batch_id IS NULL OR ? IS NULL OR legacy_load_batch_id=?);
                IF @@ROWCOUNT<>1 THROW 51000,'Conflicting source/lineage replay',1;''',
                source_file,source_checksum,legacy_load_batch_id,ctx.execution_key,
                source_file,source_file,source_checksum,source_checksum,legacy_load_batch_id,legacy_load_batch_id)

    def start_stage(self, ctx, stage, component, *, stage_attempt=1, external_id=None):
        with self._connection() as c:
            self._context(c, ctx)
            return execute(c, 'EXEC monitoring.usp_start_step ?,?,?,?,?',
                           ctx.execution_key, stage, stage_attempt, component, external_id)

    def finish_stage(self, ctx, stage, status, *, stage_attempt=1, dbt_evidence=None):
        """dbt success needs evidence returned by verify_dbt_artifacts(), never a bool."""
        evidence = dbt_evidence or {}
        if stage == 'dbt' and status == 'SUCCEEDED':
            if (not isinstance(dbt_evidence, VerifiedDbtEvidence) or dbt_evidence.context != ctx
                or dbt_evidence.get('status') != 'SUCCEEDED' or not dbt_evidence.get('complete_graph')):
                raise ValueError('Fresh verified artifacts for this execution required')
        if stage == 'dbt' and isinstance(dbt_evidence, VerifiedDbtEvidence):
            self.record_dbt_results(ctx, dbt_evidence)
        with self._connection() as c:
            self._context(c, ctx)
            old = execute(c, '''SELECT status,dbt_invocation_id,artifact_path FROM monitoring.etl_step_runs
                WHERE execution_key=? AND step_key=? AND step_attempt=?''', ctx.execution_key, stage, stage_attempt)
            if old and old[0]['status'] in TERMINAL:
                if old[0]['status'] != status or (stage == 'dbt' and status == 'SUCCEEDED' and
                    (str(old[0]['dbt_invocation_id']).lower() != evidence['invocation_id'].lower()
                     or old[0]['artifact_path'] != evidence['path'])):
                    raise ValueError('Conflicting terminal stage replay')
                return
            try:
                execute(c, 'EXEC monitoring.usp_finish_step ?,?,?,?,NULL,NULL,?,?,?,?,?,?,?,?',
                        ctx.execution_key, stage, stage_attempt, status, evidence.get('invocation_id'),
                        evidence.get('command'), evidence.get('exit_code'),
                        int(isinstance(dbt_evidence, VerifiedDbtEvidence)), evidence.get('path'),
                        evidence.get('start_time'),evidence.get('end_time'),evidence.get('sha256'))
            except Exception:
                # A concurrent identical request may have won after our initial read.
                current = execute(c, '''SELECT status,dbt_invocation_id,artifact_path FROM monitoring.etl_step_runs
                    WHERE execution_key=? AND step_key=? AND step_attempt=?''', ctx.execution_key, stage, stage_attempt)
                if not current or current[0]['status'] != status or stage == 'dbt':
                    raise

    def finish_run(self, ctx, status):
        with self._connection() as c:
            self._context(c, ctx)
            old = execute(c, 'SELECT status FROM monitoring.etl_runs WHERE execution_key=?', ctx.execution_key)[0]['status']
            if old == status:
                return
            if old in TERMINAL:
                raise ValueError('Conflicting terminal execution replay')
            try:
                execute(c, 'EXEC monitoring.usp_finish_execution ?,?', ctx.execution_key, status)
            except Exception:
                if execute(c, 'SELECT status FROM monitoring.etl_runs WHERE execution_key=?', ctx.execution_key)[0]['status'] != status:
                    raise

    def log_counters(self, ctx, *, connection, stage, scope, entity, values,
                     measurement_state='OBSERVED', stage_attempt=1):
        """Write using caller handle. COMMITTED becomes visible only at caller COMMIT.

        On commit ACK loss reconcile this exact metric key on a fresh connection;
        never repeat business DML or label the execution FAILED speculatively.
        """
        self.settings.verify(connection)
        self._context(connection, ctx)
        columns = ('records_read','records_valid','records_inserted','records_updated',
                   'records_unchanged','records_rejected','records_written')
        if set(values) - set(columns):
            raise ValueError('Unknown counter')
        vals = {k: values.get(k) for k in columns}
        if any(v is not None and (type(v) is not int or v < 0) for v in vals.values()):
            raise ValueError('Counters must be measured nonnegative integers or NULL')
        if measurement_state not in {'OBSERVED','COMMITTED'}:
            raise ValueError('Invalid measurement state')
        if measurement_state == 'COMMITTED':
            tx = connection.execute('SELECT @@TRANCOUNT,XACT_STATE()').fetchone()
            if connection.autocommit or tx[0] < 1 or tx[1] != 1:
                raise ValueError('COMMITTED witness requires the same active DML transaction')
            inputs = Inputs(vals['records_read'],vals['records_valid'],vals['records_rejected'])
            Actions(vals['records_inserted'], vals['records_updated'], vals['records_unchanged']).check(inputs)
            if vals['records_written'] != vals['records_inserted'] + vals['records_updated']:
                raise ValueError('Affected rows must equal inserted + updated')
        else:
            if any(vals[k] is not None for k in columns[2:5]+columns[6:]):
                raise ValueError('OBSERVED metrics cannot claim committed action counts')
            if all(vals[k] is not None for k in ('records_read','records_valid','records_rejected')):
                Inputs(vals['records_read'],vals['records_valid'],vals['records_rejected'])
        if stage == 'export' and (scope != 'STAGING_UPSERT' or entity != 'staging.raw_amazon_delivery'):
            raise ValueError('Canonical export scope/entity required')
        key = (ctx.execution_key,stage,stage_attempt,scope,entity)
        old = execute(connection, '''SELECT measurement_state,records_read,records_valid,records_inserted,
            records_updated,records_unchanged,records_rejected,records_written FROM monitoring.etl_record_metrics
            WITH(UPDLOCK,HOLDLOCK) WHERE execution_key=? AND step_key=? AND step_attempt=? AND metric_scope=? AND entity_name=?''', *key)
        expected = dict(measurement_state=measurement_state, **vals)
        if old:
            if old[0] != expected:
                raise ValueError('Conflicting counter replay; cannot overwrite measurements')
            return
        if measurement_state == 'COMMITTED':
            changed = execute(connection, '''UPDATE monitoring.etl_step_runs SET status='SUCCEEDED',end_time=SYSUTCDATETIME()
                OUTPUT inserted.status WHERE execution_key=? AND step_key=? AND step_attempt=? AND status='STARTED' ''', ctx.execution_key,stage,stage_attempt)
            if not changed:
                raise ValueError('Measured stage must be STARTED in this transaction')
        execute(connection, '''INSERT monitoring.etl_record_metrics(execution_key,step_key,step_attempt,
            metric_scope,entity_name,measurement_state,records_read,records_valid,records_inserted,
            records_updated,records_unchanged,records_rejected,records_written) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            *key, measurement_state, *(vals[k] for k in columns))

    def log_error(self, ctx, error, *, event_id, stage=None, stage_attempt=None,
                  severity='ERROR', error_code=None):
        """Best effort: never replace the original processing exception."""
        try:
            event_id = str(UUID(str(event_id)))
            message = redact(error)
            with self._connection() as c:
                self._context(c, ctx)
                execute(c, '''SET XACT_ABORT ON; BEGIN TRAN;
                    IF EXISTS(SELECT 1 FROM monitoring.etl_errors WITH(UPDLOCK,HOLDLOCK)
                        WHERE execution_key=? AND event_key=? AND
                        (message<>? OR severity<>? OR ISNULL(step_key,'')<>ISNULL(?,'') OR
                         ISNULL(step_attempt,0)<>ISNULL(?,0) OR ISNULL(error_code,'')<>ISNULL(?,'')))
                    BEGIN ROLLBACK; THROW 51000,'Conflicting error event replay',1; END;
                    IF NOT EXISTS(SELECT 1 FROM monitoring.etl_errors WITH(UPDLOCK,HOLDLOCK) WHERE execution_key=? AND event_key=?)
                      INSERT monitoring.etl_errors(execution_key,event_key,step_key,step_attempt,severity,error_code,message)
                      VALUES(?,?,?,?,?,?,?);
                    COMMIT;''',ctx.execution_key,event_id,message,severity,stage,stage_attempt,error_code,
                        ctx.execution_key,event_id,ctx.execution_key,event_id,stage,stage_attempt,severity,error_code,message)
            return True
        except Exception:
            return False  # Caller must preserve/re-raise original error and alert on False.

    def record_dbt_results(self, ctx, evidence):
        """Persist native model/test results and warning/error events, never counters.

        Call before finish_stage(dbt). Invocation binding and all nodes commit
        atomically; exact invocation/hash replay is a no-op. A new invocation
        belongs to a new execution attempt/ticket.
        """
        import hashlib
        from uuid import uuid5, NAMESPACE_URL
        from etl_monitoring.dbt_log import utc, sqltime
        if not isinstance(evidence, VerifiedDbtEvidence) or evidence.context != ctx:
            raise ValueError('Verified execution-specific artifact evidence required')
        c = self.settings.connect(autocommit=False)
        try:
            self._context(c, ctx)
            old = execute(c, '''SELECT dbt_invocation_id,artifact_sha256,status FROM monitoring.etl_step_runs
                WITH(UPDLOCK,HOLDLOCK) WHERE execution_key=? AND step_key='dbt' AND step_attempt=1''',ctx.execution_key)
            if not old or old[0]['status']=='NOT_STARTED':
                raise ValueError('Start dbt stage before recording its artifacts')
            if old[0]['dbt_invocation_id'] is not None:
                if (str(old[0]['dbt_invocation_id']).lower()!=evidence['invocation_id'].lower()
                    or old[0]['artifact_sha256']!=evidence['sha256']):
                    raise ValueError('Different invocation/artifacts require a new execution attempt')
                c.rollback()
                return
            execute(c, '''UPDATE monitoring.etl_step_runs SET dbt_invocation_id=?,artifact_sha256=?
                WHERE execution_key=? AND step_key='dbt' AND step_attempt=1''',
                evidence['invocation_id'],evidence['sha256'],ctx.execution_key)
            for node in evidence['nodes']:
                uid=node['unique_id']
                if len(uid)>512:raise ValueError('Native node identifier too long')
                step='dbt_node:'+hashlib.sha256(uid.encode()).hexdigest()
                native=node['status']
                status={'success':'SUCCEEDED','pass':'SUCCEEDED','warn':'SUCCEEDED',
                        'fail':'FAILED','error':'FAILED','runtime error':'FAILED','skipped':'SKIPPED'}[native]
                times=[(utc(t['started_at']),utc(t['completed_at'])) for t in node.get('timing',[])
                       if t.get('started_at') and t.get('completed_at')]
                start=min((t[0] for t in times),default=None);end=max((t[1] for t in times),default=None)
                if status=='SUCCEEDED' and (start is None or end is None):
                    raise ValueError('Successful node requires observed native timing')
                resource=evidence['resources'].get(uid,uid.split('.')[0])
                execute(c, '''INSERT monitoring.etl_step_runs(execution_key,step_key,step_attempt,component,
                    external_execution_id,dbt_invocation_id,native_status,resource_type,status,start_time,end_time,
                    native_duration_seconds,native_failures,artifact_path,artifact_sha256,artifact_verified)
                    VALUES(?,?,1,'DBT',?,?,?,?,?,?,?,?,?,?,?,1)''',
                    ctx.execution_key,step,uid,evidence['invocation_id'],native,resource,status,
                    sqltime(start) if start else None,sqltime(end) if end else None,
                    node.get('execution_time'),node.get('failures'),evidence['path'],evidence['sha256'])
                if native in ('warn','fail','error','runtime error','skipped'):
                    severity='WARNING' if native=='warn' else 'INFO' if native=='skipped' else 'ERROR'
                    event=str(uuid5(NAMESPACE_URL,ctx.execution_key+uid+native))
                    execute(c, '''INSERT monitoring.etl_errors(execution_key,event_key,step_key,step_attempt,severity,error_code,message)
                        VALUES(?,?,?,1,?,?,?)''',ctx.execution_key,event,step,severity,native,redact(node.get('message') or native))
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    @contextmanager
    def failure_guard(self, ctx, stage, *, event_id, stage_attempt=1):
        try:
            yield
        except Exception as original:
            from etl_monitoring.transaction import CommitOutcomeUnknown
            try:
                self.log_error(ctx, original, event_id=event_id, stage=stage, stage_attempt=stage_attempt,
                               error_code=type(original).__name__)
            except Exception:
                pass
            try:
                self.finish_stage(ctx, stage, 'IN_DOUBT' if isinstance(original,CommitOutcomeUnknown) else 'FAILED', stage_attempt=stage_attempt)
            except Exception:
                pass
            if isinstance(original,CommitOutcomeUnknown):
                try:self.finish_run(ctx,'IN_DOUBT')
                except Exception:pass
            raise  # Original exception/traceback survives even a total logging outage.


class VerifiedDbtEvidence(dict):
    """Evidence capability produced by actual artifact verification, not process execution."""
    def __init__(self, ctx, **values):
        super().__init__(**values)
        self.context = ctx


def verify_dbt_artifacts(ctx, settings, ticket_path, exit_code):
    """Validate unique per-execution artifacts; never start dbt or infer a linkage."""
    import hashlib
    import json
    from pathlib import Path
    from etl_monitoring.dbt_log import validate_artifacts
    path = Path(ticket_path).resolve()
    ticket = json.loads(path.read_text(encoding='utf-8'))
    expected = {'run_id': ctx.run_id, 'execution_key': ctx.execution_key, 'attempt_id': ctx.attempt_id}
    if ticket.get('linked') != expected or ticket.get('database') != settings.database:
        raise ValueError('Explicit ticket target/run/execution/attempt required')
    target = Path(ticket['target_path']).resolve()
    if target != path.parent/'target':
        raise ValueError('Artifacts must be in the unique ticket directory')
    raw = (target/'run_results.json').read_bytes()
    result = json.loads(raw)
    manifest = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
    measured = validate_artifacts(ticket,result,manifest,exit_code,expected_database=settings.database)
    return VerifiedDbtEvidence(ctx, invocation_id=measured['invocation_id'], command='build',
                               exit_code=exit_code, path=str(target/'run_results.json'),
                               status=measured['dbt_status'],complete_graph=measured['complete_graph'],
                               nodes=measured['nodes'],resources={k:v.get('resource_type') for k,v in manifest.get('nodes',{}).items()},
                               start_time=measured['start'].replace(tzinfo=None),
                               end_time=measured['end'].replace(tzinfo=None),
                               sha256=hashlib.sha256(raw).hexdigest())


def prepare_dbt_ticket(ctx, settings, archive_root):
    """Allocate artifact paths/vars only; orchestration owns subprocess execution."""
    from datetime import datetime, timezone
    import json
    from pathlib import Path
    folder = Path(archive_root).resolve()/settings.environment.lower()/ctx.execution_key
    folder.mkdir(parents=True,exist_ok=False)  # Fail closed on an old attempt directory.
    variables = dict(ctx.variables(),monitoring_ticket_id=ctx.execution_key)
    ticket = {'ticket_id':ctx.execution_key,'database':settings.database,
              'prepared_at_utc':datetime.now(timezone.utc).isoformat(),
              'linked':dict(run_id=ctx.run_id,execution_key=ctx.execution_key,attempt_id=ctx.attempt_id),
              'target_path':str(folder/'target'),'log_path':str(folder/'logs'),
              'vars_json':json.dumps(variables)}
    path = folder/'ticket.json'
    path.write_text(json.dumps(ticket,indent=2),encoding='utf-8')
    return path,ticket
