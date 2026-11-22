/* Read-only. Select the correct demo database before executing. */
USE AmazonDeliveryBI_Demo;
GO

SELECT TOP (20)
    load_batch_id, batch_name, batch_type, status AS ingestion_status,
    source_file_name, rows_read, rows_inserted, rows_updated,
    rows_unchanged, rows_rejected, rows_loaded, started_at, finished_at, error_message
FROM audit.load_batch
ORDER BY started_at DESC;

/* audit.dbt_run is created by the final block, or by the standalone SQL script. */
SELECT TOP (20)
    b.load_batch_id, b.source_file_name, b.status AS ingestion_status,
    d.dbt_attempt_id, d.status AS dbt_status,
    CASE
        WHEN b.status = 'FAILED' OR d.status = 'FAILED' THEN 'FAILED'
        WHEN b.status = 'SUCCEEDED' AND d.status = 'SUCCEEDED' THEN 'SUCCEEDED'
        WHEN d.status = 'STARTED' OR b.status = 'STARTED' THEN 'STARTED'
        ELSE 'NOT_RECORDED'
    END AS recorded_etl_status,
    d.exit_code, d.started_at AS dbt_started_at, d.finished_at AS dbt_finished_at,
    d.log_directory, d.error_message AS dbt_error, d.result_summary
FROM audit.load_batch b
OUTER APPLY (
    SELECT TOP (1) a.* FROM audit.dbt_run a
    WHERE a.load_batch_id = b.load_batch_id
    ORDER BY a.started_at DESC, a.dbt_attempt_id DESC
) d
ORDER BY b.started_at DESC;

SELECT
    (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery) AS staging_rows,
    (SELECT COUNT_BIG(*) FROM dw.fact_delivery) AS fact_rows,
    (SELECT COUNT_BIG(DISTINCT staging_row_id) FROM dw.delivery_rejections)
        AS dbt_rejected_distinct_rows;

SELECT Order_ID, Delivery_Time, load_batch_id, updated_load_batch_id, row_hash
FROM staging.raw_amazon_delivery
WHERE Order_ID IN ('seminar3_new_001', 'seminar3_new_002');
