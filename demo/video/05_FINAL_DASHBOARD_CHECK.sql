/* Read-only. Clear Power BI run selection and slicers before comparing totals. */
USE AmazonDeliveryBI;
GO
SELECT COUNT_BIG(*) AS total_runs,
    COALESCE(SUM(CASE WHEN overall_status = 'SUCCEEDED' THEN 1 ELSE 0 END), 0) AS successful_runs,
    COALESCE(SUM(CASE WHEN overall_status = 'FAILED' THEN 1 ELSE 0 END), 0) AS failed_runs,
    COALESCE(SUM(CASE WHEN overall_status IN ('STARTED','WAITING_DBT','IN_DOUBT') THEN 1 ELSE 0 END), 0) AS unfinished_runs,
    100.0 * SUM(CASE WHEN overall_status = 'SUCCEEDED' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN overall_status IN ('SUCCEEDED','FAILED') THEN 1 ELSE 0 END), 0)
        AS success_rate_percent,
    AVG(CASE WHEN overall_status IN ('SUCCEEDED','FAILED') THEN processing_duration_seconds END)
        AS average_processing_seconds
FROM monitoring.vw_etl_run_summary;

SELECT SUM(records_inserted) AS inserted_rows,
       SUM(records_updated) AS updated_rows,
       SUM(records_rejected) AS mage_rejected_rows,
       SUM(records_unchanged) AS unchanged_rows
FROM monitoring.vw_etl_record_metrics WHERE is_chart_eligible = 1;

SELECT severity, COUNT_BIG(*) AS event_count
FROM monitoring.etl_errors GROUP BY severity;

SELECT source_file, overall_status, mage_status, dbt_status, warehouse_status,
       start_time, end_time, error_message, warning_message
FROM monitoring.vw_etl_run_summary ORDER BY start_time DESC;
