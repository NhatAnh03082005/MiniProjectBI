/* Run after every filmed trigger. Read-only. */
USE AmazonDeliveryBI;
GO
SELECT TOP (12)
    execution_key, source_file, overall_status, source_status, mage_status,
    dbt_status, warehouse_status, evidence_kind, execution_origin,
    mage_pipeline_run_id, start_time, end_time,
    processing_duration_seconds, legacy_load_batch_id, error_message
FROM monitoring.vw_etl_run_summary
ORDER BY start_time DESC;

SELECT TOP (12)
    b.load_batch_id, b.source_file_name, b.status AS ingestion_status,
    b.rows_read, b.rows_inserted, b.rows_updated, b.rows_unchanged,
    b.rows_rejected, b.rows_loaded,
    d.status AS dbt_status, d.exit_code, d.error_message AS dbt_error
FROM audit.load_batch b
OUTER APPLY (
    SELECT TOP (1) d.* FROM audit.dbt_run d
    WHERE d.load_batch_id = b.load_batch_id
    ORDER BY d.started_at DESC, d.dbt_attempt_id DESC
) d
ORDER BY b.started_at DESC;

/* All attempts are retained. This query selects the latest parent run only. */
DECLARE @execution_key uniqueidentifier = (
    SELECT TOP (1) execution_key FROM monitoring.etl_runs
    ORDER BY start_time DESC, execution_key DESC
);

SELECT step_key, status, native_status, resource_type, artifact_verified,
       start_time, end_time, duration_seconds
FROM monitoring.vw_etl_step_status
WHERE execution_key = @execution_key AND latest_attempt_rank = 1
ORDER BY CASE step_key WHEN 'source' THEN 1 WHEN 'validate' THEN 2
    WHEN 'export' THEN 3 WHEN 'verify' THEN 4 WHEN 'mage' THEN 5
    WHEN 'dbt' THEN 6 WHEN 'warehouse' THEN 7 ELSE 8 END, step_key;

SELECT metric_scope, measurement_state, records_read, records_valid,
       records_inserted, records_updated, records_unchanged,
       records_rejected, records_written, is_chart_eligible
FROM monitoring.vw_etl_record_metrics
WHERE execution_key = @execution_key;

SELECT error_id, severity, step_key, error_code, message
FROM monitoring.vw_etl_error_details
WHERE execution_key = @execution_key
ORDER BY occurred_at, error_id;
