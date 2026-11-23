/* Run AFTER bootstrap, BEFORE any pipeline trigger. Read-only. */
USE AmazonDeliveryBI;
GO
SELECT CONVERT(nvarchar(128), SERVERPROPERTY('ServerName')) AS server_name,
       DB_NAME() AS database_name,
       SYSUTCDATETIME() AS now_utc,
       DATEADD(hour, 7, SYSUTCDATETIME()) AS now_bangkok;

SELECT (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery) AS staging_rows,
       (SELECT COUNT_BIG(*) FROM audit.load_batch) AS ingestion_batches,
       (SELECT COUNT_BIG(*) FROM audit.dbt_run) AS dbt_attempts,
       (SELECT COUNT_BIG(*) FROM monitoring.etl_runs) AS monitoring_runs;

SELECT name, CONVERT(nvarchar(128), value) AS environment
FROM sys.extended_properties
WHERE class = 0 AND name = 'ETLMonitoring.Environment';

SELECT s.name AS schema_name, o.name AS object_name, o.type_desc
FROM sys.objects o JOIN sys.schemas s ON s.schema_id = o.schema_id
WHERE s.name IN ('staging', 'audit', 'monitoring') AND o.is_ms_shipped = 0
ORDER BY s.name, o.type_desc, o.name;
/* Fact/Dimension are not expected before the first dbt build after reset. */
