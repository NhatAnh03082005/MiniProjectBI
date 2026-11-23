/* Main database, explicitly selected by the project owner. Run in SSMS. Creates monitoring objects; no business data reset. */
USE AmazonDeliveryBI;
GO
IF DB_NAME() <> 'AmazonDeliveryBI' THROW 51000,'Main database target required',1;
SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS ON; SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON; SET ARITHABORT ON; SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF; SET XACT_ABORT ON;
GO
CREATE OR ALTER VIEW monitoring.vw_etl_step_status
AS
SELECT s.*, r.run_id, r.attempt_id,
       CAST(DATEDIFF_BIG(millisecond,s.start_time,s.end_time)/1000.0
            AS decimal(20,3)) AS duration_seconds,
       ROW_NUMBER() OVER(PARTITION BY s.execution_key,s.step_key
                         ORDER BY s.step_attempt DESC) AS latest_attempt_rank
FROM monitoring.etl_step_runs s
JOIN monitoring.etl_runs r ON r.execution_key=s.execution_key;
GO
CREATE OR ALTER VIEW monitoring.vw_etl_run_summary
AS
SELECT r.*,r.status AS overall_status,
       CASE WHEN r.execution_kind='DBT_ONLY' THEN 'DBT_CLI'
            WHEN r.mage_pipeline_run_id IS NOT NULL THEN 'MAGE_ENGINE'
            ELSE 'BLOCK_TEST_OR_UNKNOWN_ENGINE' END AS execution_origin,
       CAST(DATEDIFF_BIG(millisecond,r.start_time,r.end_time)/1000.0
            AS decimal(20,3)) AS duration_seconds,
       CAST('WALL_CLOCK_WITH_MANUAL_WAIT' AS varchar(32)) AS duration_scope,
       s.source_status,s.mage_status,s.dbt_status,s.warehouse_status,
       s.mage_start_time,s.mage_end_time,s.dbt_start_time,s.dbt_end_time,
       s.mage_duration_seconds,s.dbt_duration_seconds,
       CASE WHEN r.status IN ('SUCCEEDED','FAILED','CANCELLED','ABANDONED')
              AND (s.mage_duration_seconds IS NOT NULL OR s.dbt_duration_seconds IS NOT NULL
                   OR s.warehouse_duration_seconds IS NOT NULL)
              AND NOT (s.mage_status='SUCCEEDED' AND s.mage_duration_seconds IS NULL)
              AND NOT (s.dbt_status='SUCCEEDED' AND s.dbt_duration_seconds IS NULL)
            THEN COALESCE(s.mage_duration_seconds,0)+COALESCE(s.dbt_duration_seconds,0)
               +COALESCE(s.warehouse_duration_seconds,0) END AS processing_duration_seconds,
       e.step_key AS failed_step,e.step_attempt AS failed_step_attempt,e.message AS error_message,
       w.message AS warning_message
FROM monitoring.etl_runs r
OUTER APPLY (
    SELECT MAX(CASE WHEN step_key='source' THEN status END) source_status,
           MAX(CASE WHEN step_key='mage' THEN status END) mage_status,
           MAX(CASE WHEN step_key='dbt' THEN status END) dbt_status,
           MAX(CASE WHEN step_key='warehouse' THEN status END) warehouse_status,
           MAX(CASE WHEN step_key='mage' THEN start_time END) mage_start_time,
           MAX(CASE WHEN step_key='mage' THEN end_time END) mage_end_time,
           MAX(CASE WHEN step_key='dbt' THEN start_time END) dbt_start_time,
           MAX(CASE WHEN step_key='dbt' THEN end_time END) dbt_end_time,
           MAX(CASE WHEN step_key='mage' THEN duration_seconds END) mage_duration_seconds,
           MAX(CASE WHEN step_key='dbt' THEN duration_seconds END) dbt_duration_seconds,
           MAX(CASE WHEN step_key='warehouse' THEN duration_seconds END) warehouse_duration_seconds
    FROM monitoring.vw_etl_step_status s
    WHERE s.execution_key=r.execution_key AND latest_attempt_rank=1
) s
OUTER APPLY (
    SELECT TOP(1) e.step_key,e.step_attempt,e.message FROM monitoring.etl_errors e
    LEFT JOIN monitoring.vw_etl_step_status es
      ON es.execution_key=e.execution_key AND es.step_key=e.step_key
     AND es.step_attempt=e.step_attempt
    WHERE e.execution_key=r.execution_key AND e.severity='ERROR'
      AND r.status IN ('FAILED','CANCELLED','ABANDONED','IN_DOUBT')
      AND (e.step_key IS NULL OR
           (es.latest_attempt_rank=1 AND es.status IN ('FAILED','CANCELLED','ABANDONED','IN_DOUBT')))
    ORDER BY e.occurred_at DESC,e.error_id DESC
) e
OUTER APPLY (
    SELECT TOP(1) message FROM monitoring.etl_errors e
    WHERE e.execution_key=r.execution_key AND severity='WARNING'
    ORDER BY occurred_at DESC,error_id DESC
) w;
GO
CREATE OR ALTER VIEW monitoring.vw_etl_record_metrics
AS
SELECT m.*,r.run_id,r.attempt_id,r.batch_type,r.metric_definition_version,
       s.latest_attempt_rank,s.status AS step_status,
       CASE WHEN m.measurement_state='COMMITTED' AND s.latest_attempt_rank=1
              AND s.status='SUCCEEDED' AND m.step_key='export'
              AND m.metric_scope='STAGING_UPSERT'
              AND m.entity_name='staging.raw_amazon_delivery'
              AND r.metric_definition_version='STAGING_UPSERT_V1'
            THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS is_chart_eligible
FROM monitoring.etl_record_metrics m
JOIN monitoring.etl_runs r ON r.execution_key=m.execution_key
JOIN monitoring.vw_etl_step_status s
  ON s.execution_key=m.execution_key AND s.step_key=m.step_key
 AND s.step_attempt=m.step_attempt;
GO
CREATE OR ALTER VIEW monitoring.vw_etl_error_details
AS
SELECT e.*,r.run_id,r.attempt_id,s.status AS step_attempt_status,
       s.latest_attempt_rank,
       CASE WHEN s.latest_attempt_rank=1 AND s.status IN
                ('FAILED','CANCELLED','ABANDONED','IN_DOUBT')
            THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS is_current_step_failure
FROM monitoring.etl_errors e
JOIN monitoring.etl_runs r ON r.execution_key=e.execution_key
LEFT JOIN monitoring.vw_etl_step_status s ON s.execution_key=e.execution_key
 AND s.step_key=e.step_key AND s.step_attempt=e.step_attempt;
GO
