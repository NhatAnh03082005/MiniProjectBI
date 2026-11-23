"""Bridge the existing main pipeline to the monitoring contract on explicit DEMO or approved PRIMARY targets.

No DDL, process launch, new upsert implementation or source-target fallback.
The legacy isolated TEST adapter remains a separate deployment. No automatic DB writes on import.
"""
import json
import os
from uuid import uuid4


class PipelineSettings:

    def __init__(self):
        self.environment = os.environ.get('ETL_MONITORING_ENV')
        self.database = os.environ.get('MSSQL_DATABASE')
        targets = {'DEMO': 'AmazonDeliveryBI_Demo', 'PRIMARY': 'AmazonDeliveryBI'}
        if self.environment not in targets or self.database != targets[self.environment]:
            raise RuntimeError('Monitoring environment and business database do not match.')
        if self.environment == 'PRIMARY' and (
                os.environ.get('ETL_MONITORING_INTEGRATED') != '1' or
                os.environ.get('ETL_MONITORING_PRIMARY_WRITES') != 'APPROVED_PRIMARY'):
            raise RuntimeError('PRIMARY requires explicit integrated monitoring enablement.')

    def verify(self, connection):
        row = connection.execute("""SELECT DB_NAME(), CONVERT(nvarchar(128),
            (SELECT value FROM sys.extended_properties
             WHERE class=0 AND name='ETLMonitoring.Environment'))""").fetchone()
        if tuple(row) != (self.database, 'APPROVED_' + self.environment):
            raise RuntimeError('Deploy monitoring SQL and matching environment marker before enabling monitoring.')
        for name in ('etl_runs', 'etl_step_runs', 'etl_record_metrics', 'etl_errors'):
            if connection.execute("SELECT OBJECT_ID(?, 'U')", 'monitoring.' + name).fetchone()[0] is None:
                raise RuntimeError('Monitoring tables are incomplete.')

    def connect(self, autocommit=True):
        import pyodbc
        from mage_project.amazon_delivery_repository import get_connection_string
        connection = pyodbc.connect(get_connection_string(), autocommit=autocommit, timeout=10)
        try:
            self.verify(connection)
            connection.execute('SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS ON; SET LOCK_TIMEOUT 10000;')
            return connection
        except BaseException:
            connection.close()
            raise


def begin_export(payload):
    from etl_monitoring import runtime
    if not runtime.enabled():
        return None
    # Preflight before any business DML, including explicit target guard.
    settings = PipelineSettings()
    connection = settings.connect()
    connection.close()
    if not payload.get('monitoring_context'):
        raise RuntimeError('Missing monitoring context; rerun the whole pipeline.')
    ctx = runtime.context(payload['monitoring_context'])
    runtime.start_step(ctx, 'export', 'MAGE')
    return ctx


def bind_batch(ctx, payload, batch_id):
    if ctx is None:
        return
    from etl_monitoring.adapter import MonitoringAdapter
    MonitoringAdapter(PipelineSettings()).bind_metadata(
        ctx, legacy_load_batch_id=batch_id, source_file=payload['source_file_name'],
        source_checksum=payload['source_file_checksum'])


def publish_export(cursor, ctx, read, inserted, updated, unchanged, rejected):
    """Main DML and its COMMITTED witness share the SAME transaction/commit."""
    if ctx is None:
        return
    cursor.execute("""INSERT monitoring.etl_record_metrics
        (execution_key,step_key,step_attempt,metric_scope,entity_name,measurement_state,
         records_read,records_valid,records_inserted,records_updated,records_unchanged,
         records_rejected,records_written)
        VALUES(?,'export',1,'STAGING_UPSERT','staging.raw_amazon_delivery','COMMITTED',?,?,?,?,?,?,?);
        UPDATE monitoring.etl_step_runs SET status='SUCCEEDED',end_time=SYSUTCDATETIME()
        WHERE execution_key=? AND step_key='export' AND step_attempt=1 AND status='STARTED';
        IF @@ROWCOUNT<>1 THROW 51000,'Monitoring export stage not started',1;
        """, ctx.execution_key, read, read-rejected, inserted, updated, unchanged, rejected,
        inserted+updated, ctx.execution_key)


def export_failed(ctx, error, commit_attempted=False):
    if ctx is None:
        return
    from etl_monitoring import runtime
    if not commit_attempted:
        runtime.fail(ctx, 'export', error)
        return
    # A lost COMMIT acknowledgement is not proof of rollback. Preserve witness.
    connection = None
    try:
        connection = PipelineSettings().connect()
        runtime.execute(connection, """UPDATE monitoring.etl_runs SET status='IN_DOUBT',end_time=NULL
            WHERE execution_key=? AND status IN ('STARTED','WAITING_DBT');""", ctx.execution_key)
        runtime.event(ctx, 'export', 'ERROR', 'COMMIT outcome unknown; reconcile witness before rerun', 'COMMIT_UNKNOWN')
    except Exception:
        import logging
        logging.getLogger(__name__).error('Could not record IN_DOUBT; inspect durable export witness before rerun.')
    finally:
        if connection is not None:
            connection.close()


class DbtSession:
    def __init__(self, verified):
        from etl_monitoring import runtime
        from etl_monitoring.adapter import MonitoringAdapter
        self.stage = 'dbt'
        self.settings = PipelineSettings()
        if 'monitoring_context' not in verified or len(verified) != 1:
            raise RuntimeError('No monitoring context for dbt; rerun whole pipeline from Loader.')
        self.ctx = runtime.context(str(verified.iloc[0]['monitoring_context']))
        self.adapter = MonitoringAdapter(self.settings)

    def prepare(self, work):
        from etl_monitoring.adapter import prepare_dbt_ticket
        self.path, self.ticket = prepare_dbt_ticket(self.ctx, self.settings, work / 'monitoring')
        self.adapter.start_stage(self.ctx, 'dbt', 'DBT')
        return self.ticket

    def record_dbt(self, exit_code):
        from etl_monitoring.adapter import verify_dbt_artifacts
        evidence = verify_dbt_artifacts(self.ctx, self.settings, self.path, exit_code)
        self.adapter.finish_stage(self.ctx, 'dbt', evidence['status'], dbt_evidence=evidence)
        if evidence['status'] != 'SUCCEEDED' or not evidence['complete_graph']:
            raise RuntimeError('Monitoring artifact verification did not confirm a complete successful dbt build.')
        self.adapter.start_stage(self.ctx, 'warehouse', 'WAREHOUSE')
        self.stage = 'warehouse'

    def finish(self):
        self.adapter.finish_stage(self.ctx, 'warehouse', 'SUCCEEDED')
        self.adapter.finish_run(self.ctx, 'SUCCEEDED')

    def fail(self, error):
        from etl_monitoring import runtime
        # Close all active steps and preserve committed export metrics.
        runtime.fail(self.ctx, self.stage, error)
