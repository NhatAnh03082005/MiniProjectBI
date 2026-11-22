"""Transaction helpers for the existing Mage pipelines. No process launcher.

Only explicit function calls can write using a caller-supplied DB connection.
Pure functions can be unit tested with no SQL Server, Mage or dbt execution.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from typing import Callable
from uuid import UUID


@dataclass(frozen=True)
class ExecutionContext:
    run_id: str
    execution_key: str
    attempt_id: int
    export_step_attempt: int = 1

    def __post_init__(self):
        UUID(self.run_id)
        UUID(self.execution_key)
        if self.attempt_id < 1 or self.export_step_attempt < 1:
            raise ValueError('Attempts must be positive')

    def variables(self):
        return dict(monitoring_run_id=self.run_id,
                    monitoring_execution_key=self.execution_key,
                    monitoring_attempt_id=self.attempt_id)


@dataclass(frozen=True)
class Inputs:
    read: int
    valid: int
    rejected: int

    def __post_init__(self):
        if any(type(x) is not int or x < 0 for x in (self.read,self.valid,self.rejected)):
            raise ValueError('Successful validation requires measured nonnegative integers')
        if self.read != self.valid + self.rejected:
            raise ValueError('Technical validation must partition measured parsed records')


@dataclass(frozen=True)
class Actions:
    inserted: int
    updated: int
    unchanged: int

    def check(self, inputs):
        if any(type(x) is not int or x < 0 for x in (self.inserted,self.updated,self.unchanged)):
            raise ValueError('Actions must be measured nonnegative integers')
        if inputs.valid != self.inserted + self.updated + self.unchanged:
            raise ValueError('Committed input/action reconciliation failed')


class CommitOutcomeUnknown(RuntimeError):
    """Do not mark FAILED or retry DML until a separate connection reconciles it."""


def source_measurements(source_payload, validation_payload):
    """Keep unknown counts NULL instead of trusting legacy initialized zeroes."""
    if source_payload.get('read_error'):
        return {'records_read':None,'records_valid':None,'records_rejected':None}
    measured_read=len(source_payload['data'])
    if validation_payload.get('validation_error'):
        return {'records_read':measured_read,'records_valid':None,'records_rejected':None}
    measured_valid=len(validation_payload['data'])
    measured_rejected=int(validation_payload['rows_rejected'])
    Inputs(measured_read,measured_valid,measured_rejected)
    return {'records_read':measured_read,'records_valid':measured_valid,'records_rejected':measured_rejected}


def transactional_export(connection, context: ExecutionContext, inputs: Inputs,
                         apply_dml: Callable, publish: Callable):
    """Exclusive writer connection, autocommit=False; STARTED already persisted.

    apply_dml(cursor) must return Actions using actual DML row counts/OUTPUT,
    and observed unchanged under the same lock. It MUST NOT commit internally.
    publish(cursor,context,inputs,actions) MUST NOT open another connection.
    Neither callback can publish counters to Mage output before this returns.
    """
    if connection.autocommit:
        raise ValueError('An atomic export requires autocommit=False')
    try:
        cursor = connection.cursor()
        cursor.execute('SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000;')
        # Conservative lock: blocks other writers including uninstrumented ones.
        # Review contention on representative staging volume before rollout.
        cursor.execute('SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery WITH (TABLOCKX,HOLDLOCK);')
        cursor.fetchone()
        cursor.execute('SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery WHERE row_hash IS NULL;')
        if cursor.fetchone()[0]:
            raise ValueError('Hash baseline must be approved and verified before action measurements')
        actions = apply_dml(cursor)
        actions.check(inputs)
        publish(cursor, context, inputs, actions)
    except Exception:
        connection.rollback()
        raise
    try:
        connection.commit()
    except Exception as error:
        # A failed acknowledgement does not prove rollback. Caller closes this
        # connection, records IN_DOUBT separately, reconciles durable witnesses.
        raise CommitOutcomeUnknown('Reconcile export witness before retry') from error
    return actions


def prepare_export_audit(cursor, context, inputs, payload, load_batch_id):
    """Persist on a separate metadata transaction BEFORE transactional_export.

    Caller commits this metadata transaction and verifies acknowledgement first.
    Unknown action counters remain NULL. Existing legacy rows_loaded is NOT NULL;
    its placeholder 0 is never exposed as a measured action by reporting views.
    """
    cursor.execute('''
        UPDATE monitoring.etl_runs SET legacy_load_batch_id=?,source_file=?,source_checksum=?
        WHERE execution_key=? AND run_id=? AND attempt_id=? AND status='STARTED'
          AND legacy_load_batch_id IS NULL;
        IF @@ROWCOUNT<>1 THROW 51000,'Missing or already-bound export context',1;
    ''',load_batch_id,payload['source_file_name'],payload['source_file_checksum'],
         context.execution_key,context.run_id,context.attempt_id)
    cursor.execute('''
        INSERT audit.load_batch(load_batch_id,batch_name,batch_type,source_file_name,source_file_checksum,
          expected_date_from,expected_date_to,expected_row_count,status,rows_read,rows_valid,
          rows_loaded,rows_rejected,rows_inserted,rows_updated,rows_unchanged,metric_definition_version)
        VALUES(?,?,?,?,?,?,?,?,'STARTED',?,?,0,?,NULL,NULL,NULL,NULL);
    ''',load_batch_id,payload['batch_name'],payload['batch_type'],payload['source_file_name'],
         payload['source_file_checksum'],payload.get('date_from') or None,payload.get('date_to') or None,
         inputs.read,inputs.read,inputs.valid,inputs.rejected)


def publish_export(cursor, context, inputs, actions, load_batch_id):
    """Call inside the SAME transaction as staging DML, never as post-commit insert.

    Run + export STARTED + legacy STARTED must already be committed separately.
    Durable metric row + SUCCEEDED audit/step is the commit witness.
    """
    actions.check(inputs)
    cursor.execute('''
        UPDATE monitoring.etl_runs SET legacy_load_batch_id=?
        WHERE execution_key=? AND run_id=? AND attempt_id=? AND status='STARTED'
          AND (legacy_load_batch_id IS NULL OR legacy_load_batch_id=?);
        IF @@ROWCOUNT<>1 THROW 51000,'Execution context mismatch',1;
    ''', load_batch_id,context.execution_key,context.run_id,context.attempt_id,load_batch_id)
    cursor.execute('''
        INSERT INTO monitoring.etl_record_metrics
        (execution_key,step_key,step_attempt,metric_scope,entity_name,measurement_state,
         records_read,records_valid,records_inserted,records_updated,records_unchanged,
         records_rejected,records_written)
        VALUES (?,'export',?,'STAGING_UPSERT','staging.raw_amazon_delivery','COMMITTED',?,?,?,?,?,?,?);
    ''',context.execution_key,context.export_step_attempt,inputs.read,inputs.valid,
         actions.inserted,actions.updated,actions.unchanged,inputs.rejected,
         actions.inserted+actions.updated)
    cursor.execute('''
        UPDATE audit.load_batch SET status='SUCCEEDED',finished_at=SYSUTCDATETIME(),
          rows_read=?,rows_valid=?,rows_rejected=?,rows_loaded=?,
          rows_inserted=?,rows_updated=?,rows_unchanged=?,metric_definition_version='STAGING_UPSERT_V1'
        WHERE load_batch_id=? AND status='STARTED';
        IF @@ROWCOUNT<>1 THROW 51000,'Audit witness mismatch',1;
    ''',inputs.read,inputs.valid,inputs.rejected,actions.inserted+actions.updated,
         actions.inserted,actions.updated,actions.unchanged,load_batch_id)
    cursor.execute('''
        UPDATE monitoring.etl_step_runs SET status='SUCCEEDED',end_time=SYSUTCDATETIME()
        WHERE execution_key=? AND step_key='export' AND step_attempt=? AND status='STARTED';
        IF @@ROWCOUNT<>1 THROW 51000,'Export step mismatch',1;
    ''',context.execution_key,context.export_step_attempt)


def apply_existing_upsert(cursor, payload, load_batch_id, loaded_at):
    """Proposed adapter for existing business DML; only call under export lock.

    Actual INSERT/UPDATE counts come from executed statements, never target size.
    Existing repository functions are imported only on explicit invocation.
    """
    from mage_project import amazon_delivery_repository as repository
    cursor.execute('SET NOCOUNT OFF;')
    repository._create_incoming_table(cursor)
    repository._load_incoming(cursor,payload['data'])
    expected = repository._count_change_types(cursor)
    repository._apply_updates(cursor,load_batch_id,payload['source_file_name'])
    updated = cursor.rowcount
    repository._apply_inserts(cursor,load_batch_id,payload['source_file_name'],loaded_at)
    inserted = cursor.rowcount
    if inserted<0 or updated<0:
        raise ValueError('Driver did not provide measured DML rowcounts; do not infer counts')
    actions = Actions(inserted,updated,expected[2])
    if (inserted,updated,actions.unchanged) != expected:
        raise ValueError('Measured actions differ from locked preclassification')
    cursor.execute('''SELECT COUNT_BIG(*) FROM #incoming_amazon_delivery s
        JOIN staging.raw_amazon_delivery t
          ON LOWER(LTRIM(RTRIM(t.Order_ID)))=s.order_key AND t.row_hash=s.row_hash;''')
    if cursor.fetchone()[0] != len(payload['data']):
        raise ValueError('Post-DML hash reconciliation failed')
    return actions
