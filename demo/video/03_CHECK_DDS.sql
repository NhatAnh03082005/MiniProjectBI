/* Run after a SUCCEEDED build. Read-only. Counts reflect CURRENT DDS snapshot. */
USE AmazonDeliveryBI;
GO
WITH counts AS (
    SELECT
        (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery) AS staging_rows,
        (SELECT COUNT_BIG(*) FROM dw.fact_delivery) AS fact_rows,
        (SELECT COUNT_BIG(DISTINCT staging_row_id) FROM dw.delivery_rejections) AS dbt_rejected_rows
)
SELECT *, fact_rows + dbt_rejected_rows AS reconciled_rows,
    CASE WHEN staging_rows = fact_rows + dbt_rejected_rows THEN 'PASS' ELSE 'FAIL' END
        AS reconciliation_status
FROM counts;

SELECT 'dim_date' AS dimension_name, COUNT_BIG(*) AS rows FROM dw.dim_date
UNION ALL SELECT 'dim_delivery_condition', COUNT_BIG(*) FROM dw.dim_delivery_condition
UNION ALL SELECT 'dim_vehicle', COUNT_BIG(*) FROM dw.dim_vehicle
UNION ALL SELECT 'dim_area', COUNT_BIG(*) FROM dw.dim_area
UNION ALL SELECT 'dim_category', COUNT_BIG(*) FROM dw.dim_category;

SELECT SUM(CONVERT(bigint, delivery_count)) AS total_delivery_records,
    AVG(CONVERT(float, delivery_time_minutes)) AS average_delivery_minutes,
    COUNT(DISTINCT CASE WHEN date_key <> 0 THEN date_key END) AS active_days
FROM dw.fact_delivery;

SELECT DISTINCT
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delivery_time_minutes) OVER () AS median_minutes,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY delivery_time_minutes) OVER () AS p90_minutes,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY delivery_time_minutes) OVER () AS p95_minutes
FROM dw.fact_delivery WHERE delivery_time_minutes IS NOT NULL;
