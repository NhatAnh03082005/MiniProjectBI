:ON ERROR EXIT
/* READ ONLY. Supports PRIMARY or TEST. Does not create execution data. */
USE [$(MonitoringDatabase)];
IF DB_NAME() NOT IN ('AmazonDeliveryBI','AmazonDeliveryBI_TEST')
 OR CONVERT(nvarchar(128),SERVERPROPERTY('ServerName'))<>N'DESKTOP-OBDFK6B\SQLEXPRESS'
 THROW 51000,'Unexpected monitoring target',1;
IF (SELECT COUNT(*) FROM sys.objects WHERE schema_id=SCHEMA_ID('monitoring') AND type='U'
 AND name IN ('etl_runs','etl_step_runs','etl_record_metrics','etl_errors'))<>4
 OR (SELECT COUNT(*) FROM sys.objects WHERE schema_id=SCHEMA_ID('monitoring') AND type='V'
 AND name IN ('vw_etl_run_summary','vw_etl_record_metrics','vw_etl_step_status','vw_etl_error_details'))<>4
 OR (SELECT COUNT(*) FROM sys.objects WHERE schema_id=SCHEMA_ID('monitoring') AND type='P'
 AND name IN ('usp_begin_execution','usp_start_step','usp_finish_step','usp_finish_execution'))<>4
 THROW 51000,'Required monitoring objects missing; no READY conclusion',1;
IF COL_LENGTH('monitoring.etl_errors','event_key') IS NULL
 OR NOT EXISTS(SELECT 1 FROM sys.parameters WHERE object_id=OBJECT_ID('monitoring.usp_finish_step') AND name='@artifact_sha256')
 THROW 51000,'Adapter contract version incomplete',1;
GO
SELECT 'duplicate_attempts' check_name,COUNT_BIG(*) violations FROM
 (SELECT run_id,attempt_id FROM monitoring.etl_runs GROUP BY run_id,attempt_id HAVING COUNT(*)>1) d
UNION ALL SELECT 'negative_duration',COUNT_BIG(*) FROM monitoring.vw_etl_run_summary
 WHERE duration_seconds<0 OR processing_duration_seconds<0
UNION ALL SELECT 'invalid_chart_measurements',COUNT_BIG(*) FROM monitoring.vw_etl_record_metrics
 WHERE is_chart_eligible=1 AND (measurement_state<>'COMMITTED' OR step_status<>'SUCCEEDED'
  OR records_read IS NULL OR records_valid IS NULL OR records_rejected IS NULL
  OR records_inserted IS NULL OR records_updated IS NULL OR records_unchanged IS NULL
  OR records_written IS NULL OR records_read<>records_valid+records_rejected
  OR records_valid<>records_inserted+records_updated+records_unchanged
  OR records_written<>records_inserted+records_updated)
UNION ALL SELECT 'duplicate_eligible_exports',COUNT_BIG(*) FROM
 (SELECT execution_key FROM monitoring.vw_etl_record_metrics WHERE is_chart_eligible=1
 GROUP BY execution_key HAVING COUNT(*)>1) d
UNION ALL SELECT 'untrusted_constraints',
 (SELECT COUNT(*) FROM sys.check_constraints WHERE schema_id=SCHEMA_ID('monitoring') AND (is_disabled=1 OR is_not_trusted=1))+
 (SELECT COUNT(*) FROM sys.foreign_keys WHERE schema_id=SCHEMA_ID('monitoring') AND (is_disabled=1 OR is_not_trusted=1))
UNION ALL SELECT 'synthetic_native_executions',COUNT_BIG(*) FROM monitoring.vw_etl_run_summary
 WHERE pipeline_name LIKE 'monitoring[_]contract[_]%' AND execution_origin IN ('MAGE_ENGINE','DBT_CLI');
SELECT evidence_kind,execution_origin,status,COUNT_BIG(*) attempts FROM monitoring.vw_etl_run_summary
 GROUP BY evidence_kind,execution_origin,status;
SELECT COUNT(*) executions,COUNT(DISTINCT run_id) logical_runs,
 SUM(CASE WHEN overall_status='SUCCEEDED' THEN 1 ELSE 0 END) successes,
 SUM(CASE WHEN overall_status='FAILED' THEN 1 ELSE 0 END) failures,
 AVG(CASE WHEN overall_status IN ('SUCCEEDED','FAILED') THEN processing_duration_seconds END) average_seconds
FROM monitoring.vw_etl_run_summary WHERE execution_origin IN ('MAGE_ENGINE','DBT_CLI')
 AND evidence_kind=CASE DB_NAME() WHEN 'AmazonDeliveryBI' THEN 'REAL' ELSE 'TEST' END;
