:ON ERROR EXIT
/* REVIEW BEFORE DEPLOYMENT. sqlcmd -b required. PRIMARY needs separate approval.
   No business DML, DROP TABLE, TRUNCATE or history copy. Environment variables
   are an execution interlock, not authorization. Never run with backup/ETL jobs.
*/
USE [$(MonitoringDatabase)];
SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS ON; SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON; SET ARITHABORT ON; SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF; SET LOCK_TIMEOUT 5000; SET XACT_ABORT ON;
IF CONVERT(nvarchar(128),SERVERPROPERTY('ServerName'))<>N'DESKTOP-OBDFK6B\SQLEXPRESS'
 THROW 51000,'Server mismatch',1;
IF NOT ((N'$(DeploymentEnvironment)'='PRIMARY' AND DB_NAME()='AmazonDeliveryBI'
          AND N'$(DeploymentApproval)'='APPROVED_PRIMARY') OR
        (N'$(DeploymentEnvironment)'='TEST' AND DB_NAME()='AmazonDeliveryBI_TEST'
          AND N'$(DeploymentApproval)'='APPROVED_TEST'))
 THROW 51000,'Explicit approved environment/database pair required',1;
GO
CREATE OR ALTER PROCEDURE monitoring.usp_begin_execution
 @execution_key uniqueidentifier, @run_id uniqueidentifier,
 @pipeline_name nvarchar(128), @batch_type varchar(20),
 @evidence_kind varchar(8), @mage_pipeline_run_id nvarchar(128), @execution_kind varchar(16)='MAGE_DBT'
AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON;
 IF @@TRANCOUNT<>0 THROW 51000,'Lifecycle procedure requires its own connection/transaction',1;
 BEGIN TRY
  BEGIN TRANSACTION;
  DECLARE @lock_result int,@attempt int,@resource nvarchar(255)=N'etl-run:'+CONVERT(nvarchar(36),@run_id);
  EXEC @lock_result=sys.sp_getapplock @Resource=@resource,@LockMode='Exclusive',
       @LockOwner='Transaction',@LockTimeout=5000;
  IF @lock_result<0 THROW 51000,'Could not serialize logical run allocation',1;
  -- Idempotent request retry after lost acknowledgement: caller keeps execution_key.
  IF EXISTS(SELECT 1 FROM monitoring.etl_runs WHERE execution_key=@execution_key)
  BEGIN
   IF NOT EXISTS(SELECT 1 FROM monitoring.etl_runs WHERE execution_key=@execution_key
                 AND run_id=@run_id AND pipeline_name=@pipeline_name AND batch_type=@batch_type
                 AND evidence_kind=@evidence_kind AND execution_kind=@execution_kind
                 AND ISNULL(mage_pipeline_run_id,'')=ISNULL(@mage_pipeline_run_id,''))
     THROW 51000,'Execution key reused with a different context',1;
   COMMIT;
   SELECT execution_key,run_id,attempt_id,status FROM monitoring.etl_runs WHERE execution_key=@execution_key;
   RETURN;
  END;
  IF EXISTS(SELECT 1 FROM monitoring.etl_runs WHERE run_id=@run_id AND status IN ('STARTED','WAITING_DBT','IN_DOUBT'))
    THROW 51000,'Reconcile active attempt before starting a retry',1;
  IF EXISTS(SELECT 1 FROM monitoring.etl_runs WHERE run_id=@run_id
            AND (pipeline_name<>@pipeline_name OR batch_type<>@batch_type OR evidence_kind<>@evidence_kind
                 OR execution_kind<>@execution_kind))
    THROW 51000,'Logical run context cannot change between attempts',1;
  SELECT @attempt=COALESCE(MAX(attempt_id),0)+1 FROM monitoring.etl_runs WHERE run_id=@run_id;
  INSERT monitoring.etl_runs(execution_key,run_id,attempt_id,pipeline_name,batch_type,evidence_kind,
      mage_pipeline_run_id,execution_kind,status,metric_definition_version,heartbeat_at)
  VALUES(@execution_key,@run_id,@attempt,@pipeline_name,@batch_type,@evidence_kind,
      @mage_pipeline_run_id,@execution_kind,'STARTED','STAGING_UPSERT_V1',SYSUTCDATETIME());
  INSERT monitoring.etl_step_runs(execution_key,step_key,step_attempt,component,status)
  SELECT @execution_key,step_key,1,component,CASE WHEN @execution_kind='DBT_ONLY' AND step_key IN ('source','mage') THEN 'SKIPPED' ELSE 'NOT_STARTED' END
  FROM (VALUES('source','SOURCE'),('mage','MAGE'),('dbt','DBT'),('warehouse','WAREHOUSE')) stages(step_key,component);
  COMMIT;
  SELECT execution_key,run_id,attempt_id,status FROM monitoring.etl_runs WHERE execution_key=@execution_key;
 END TRY
 BEGIN CATCH
  IF @@TRANCOUNT>0 ROLLBACK;
  THROW;
 END CATCH;
END;
GO
CREATE OR ALTER PROCEDURE monitoring.usp_start_step
 @execution_key uniqueidentifier,@step_key varchar(128),@step_attempt int,
 @component varchar(20),@external_execution_id nvarchar(128)=NULL
AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON;
 IF @@TRANCOUNT<>0 THROW 51000,'Dedicated lifecycle connection required',1;
 BEGIN TRY
  BEGIN TRANSACTION;
  IF NOT EXISTS(SELECT 1 FROM monitoring.etl_runs WITH(UPDLOCK,HOLDLOCK)
                WHERE execution_key=@execution_key AND status IN ('STARTED','WAITING_DBT'))
    THROW 51000,'Execution must be STARTED',1;
  IF EXISTS(SELECT 1 FROM monitoring.etl_step_runs WHERE execution_key=@execution_key
             AND step_key=@step_key AND step_attempt=@step_attempt)
  BEGIN
   IF NOT EXISTS(SELECT 1 FROM monitoring.etl_step_runs WHERE execution_key=@execution_key
       AND step_key=@step_key AND step_attempt=@step_attempt AND component=@component
       AND (status='NOT_STARTED' OR ISNULL(external_execution_id,'')=ISNULL(@external_execution_id,'')))
      THROW 51000,'Step context mismatch',1;
   UPDATE monitoring.etl_step_runs SET status='STARTED',start_time=SYSUTCDATETIME(),
     external_execution_id=@external_execution_id
    WHERE execution_key=@execution_key AND step_key=@step_key AND step_attempt=@step_attempt
      AND status='NOT_STARTED';
   COMMIT;
   SELECT status FROM monitoring.etl_step_runs WHERE execution_key=@execution_key
     AND step_key=@step_key AND step_attempt=@step_attempt;
   RETURN;
  END;
  IF EXISTS(SELECT 1 FROM monitoring.etl_step_runs WHERE execution_key=@execution_key
             AND step_key=@step_key AND status IN ('STARTED','WAITING_DBT','IN_DOUBT'))
    THROW 51000,'Cannot overlap attempts of the same step',1;
  DECLARE @next int;
  SELECT @next=COALESCE(MAX(step_attempt),0)+1 FROM monitoring.etl_step_runs
   WHERE execution_key=@execution_key AND step_key=@step_key;
  IF @next<>@step_attempt THROW 51000,'Step attempts must be sequential',1;
  INSERT monitoring.etl_step_runs(execution_key,step_key,step_attempt,component,external_execution_id,status,start_time)
  VALUES(@execution_key,@step_key,@step_attempt,@component,@external_execution_id,'STARTED',SYSUTCDATETIME());
  UPDATE monitoring.etl_runs SET heartbeat_at=SYSUTCDATETIME() WHERE execution_key=@execution_key;
  COMMIT;
  SELECT status FROM monitoring.etl_step_runs WHERE execution_key=@execution_key
    AND step_key=@step_key AND step_attempt=@step_attempt;
 END TRY
 BEGIN CATCH
  IF @@TRANCOUNT>0 ROLLBACK;
  THROW;
 END CATCH;
END;
GO
CREATE OR ALTER PROCEDURE monitoring.usp_finish_step
 @execution_key uniqueidentifier,@step_key varchar(128),@step_attempt int,@status varchar(20),
 @message nvarchar(max)=NULL,@error_code nvarchar(128)=NULL,
 @dbt_invocation_id uniqueidentifier=NULL,@dbt_command varchar(32)=NULL,
 @process_exit_code int=NULL,@artifact_verified bit=0,@artifact_path nvarchar(1024)=NULL,
 @observed_start_time datetime2(3)=NULL,@observed_end_time datetime2(3)=NULL,@artifact_sha256 char(64)=NULL
AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON;
 IF @@TRANCOUNT<>0 THROW 51000,'Dedicated lifecycle connection required',1;
 IF @status NOT IN ('SUCCEEDED','FAILED','CANCELLED','SKIPPED','ABANDONED','IN_DOUBT')
    THROW 51000,'Invalid finish status',1;
 -- Export success is exclusively published with business DML; this API cannot assert it.
 IF @step_key='export' AND @status='SUCCEEDED'
    THROW 51000,'Export success must be atomic with committed DML metrics',1;
 IF @step_key='dbt' AND @status='SUCCEEDED' AND
    (@artifact_verified<>1 OR @dbt_invocation_id IS NULL OR @artifact_path IS NULL
     OR COALESCE(@dbt_command,'')<>'build' OR COALESCE(@process_exit_code,-1)<>0)
    THROW 51000,'dbt success requires verified build evidence',1;
 IF (@observed_start_time IS NULL AND @observed_end_time IS NOT NULL)
     OR (@observed_start_time IS NOT NULL AND @observed_end_time IS NULL)
     OR @observed_end_time<@observed_start_time
     OR @observed_end_time>DATEADD(second,1,SYSUTCDATETIME())
    THROW 51000,'Invalid observed UTC interval',1;
 BEGIN TRY
  BEGIN TRANSACTION;
  -- ACK-loss retry is a no-op, including after the parent execution is closed.
  IF EXISTS(SELECT 1 FROM monitoring.etl_step_runs WITH(UPDLOCK,HOLDLOCK)
       WHERE execution_key=@execution_key AND step_key=@step_key AND step_attempt=@step_attempt
       AND status=@status AND status IN ('SUCCEEDED','FAILED','CANCELLED','SKIPPED','ABANDONED')
       AND ISNULL(CONVERT(varchar(36),dbt_invocation_id),'')=ISNULL(CONVERT(varchar(36),@dbt_invocation_id),'')
       AND ISNULL(artifact_path,'')=ISNULL(@artifact_path,'')
       AND ISNULL(artifact_sha256,'')=ISNULL(@artifact_sha256,''))
  BEGIN COMMIT; RETURN; END;
  IF NOT EXISTS(SELECT 1 FROM monitoring.etl_runs WITH(UPDLOCK,HOLDLOCK)
       WHERE execution_key=@execution_key AND status IN ('STARTED','WAITING_DBT','IN_DOUBT'))
    THROW 51000,'Execution is already closed',1;
  UPDATE monitoring.etl_step_runs SET status=@status,
      start_time=COALESCE(@observed_start_time,start_time),
      end_time=CASE WHEN @status='IN_DOUBT' OR (start_time IS NULL AND @observed_start_time IS NULL) THEN NULL ELSE COALESCE(@observed_end_time,SYSUTCDATETIME()) END,
      dbt_invocation_id=@dbt_invocation_id,dbt_command=@dbt_command,
      process_exit_code=@process_exit_code,artifact_verified=@artifact_verified,artifact_path=@artifact_path,
      artifact_sha256=@artifact_sha256
   WHERE execution_key=@execution_key AND step_key=@step_key AND step_attempt=@step_attempt
     AND (status IN ('STARTED','IN_DOUBT') OR
          (status='NOT_STARTED' AND @status IN ('SKIPPED','CANCELLED')));
  IF @@ROWCOUNT<>1 THROW 51000,'Step missing or already terminal: read state before retry',1;
  IF @message IS NOT NULL
    INSERT monitoring.etl_errors(execution_key,step_key,step_attempt,severity,error_code,message)
    VALUES(@execution_key,@step_key,@step_attempt,
      CASE WHEN @status IN ('FAILED','CANCELLED','ABANDONED','IN_DOUBT') THEN 'ERROR' ELSE 'INFO' END,
      @error_code,@message);
  UPDATE monitoring.etl_runs SET heartbeat_at=SYSUTCDATETIME() WHERE execution_key=@execution_key;
  COMMIT;
 END TRY
 BEGIN CATCH
  IF @@TRANCOUNT>0 ROLLBACK;
  THROW;
 END CATCH;
END;
GO
CREATE OR ALTER PROCEDURE monitoring.usp_finish_execution
 @execution_key uniqueidentifier,@status varchar(20)
AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON;
 IF @@TRANCOUNT<>0 THROW 51000,'Dedicated lifecycle connection required',1;
 IF @status NOT IN ('SUCCEEDED','FAILED','CANCELLED','SKIPPED','ABANDONED','IN_DOUBT','WAITING_DBT')
    THROW 51000,'Invalid execution status',1;
 BEGIN TRY
  BEGIN TRANSACTION;
  IF NOT EXISTS(SELECT 1 FROM monitoring.etl_runs WITH(UPDLOCK,HOLDLOCK)
       WHERE execution_key=@execution_key AND status IN ('STARTED','WAITING_DBT','IN_DOUBT'))
    THROW 51000,'Execution missing or terminal: read state before retry',1;
  IF @status='WAITING_DBT' AND
     (NOT EXISTS(SELECT 1 FROM monitoring.etl_runs WHERE execution_key=@execution_key AND execution_kind='MAGE_DBT')
      OR ISNULL((SELECT TOP(1) status FROM monitoring.etl_step_runs WHERE execution_key=@execution_key
                 AND step_key='mage' ORDER BY step_attempt DESC),'MISSING')<>'SUCCEEDED'
      OR ISNULL((SELECT TOP(1) status FROM monitoring.etl_step_runs WHERE execution_key=@execution_key
                 AND step_key='dbt' ORDER BY step_attempt DESC),'MISSING') NOT IN ('NOT_STARTED','STARTED'))
    THROW 51000,'WAITING_DBT requires completed Mage and a pending dbt stage',1;
  IF @status='SUCCEEDED'
  BEGIN
   IF EXISTS(SELECT required.step_key FROM (VALUES('source'),('mage'),('dbt'),('warehouse')) required(step_key)
     OUTER APPLY(SELECT TOP(1) status FROM monitoring.etl_step_runs s
       WHERE s.execution_key=@execution_key AND s.step_key=required.step_key ORDER BY step_attempt DESC) actual
     WHERE COALESCE(actual.status,'MISSING')<>'SUCCEEDED'
       AND (required.step_key IN ('dbt','warehouse') OR EXISTS(SELECT 1 FROM monitoring.etl_runs WHERE execution_key=@execution_key AND execution_kind='MAGE_DBT')))
      THROW 51000,'Required stages have not all succeeded',1;
   IF EXISTS(SELECT 1 FROM monitoring.etl_runs WHERE execution_key=@execution_key AND execution_kind='MAGE_DBT'
        AND pipeline_name IN ('amazon_delivery_full_load','amazon_delivery_incremental_load'))
      AND NOT EXISTS(SELECT 1 FROM monitoring.etl_record_metrics m JOIN monitoring.etl_step_runs s
         ON s.execution_key=m.execution_key AND s.step_key=m.step_key AND s.step_attempt=m.step_attempt
         WHERE m.execution_key=@execution_key AND m.step_key='export' AND s.status='SUCCEEDED'
           AND m.measurement_state='COMMITTED' AND m.metric_scope='STAGING_UPSERT'
           AND m.entity_name='staging.raw_amazon_delivery'
           AND s.step_attempt=(SELECT MAX(step_attempt) FROM monitoring.etl_step_runs latest
               WHERE latest.execution_key=s.execution_key AND latest.step_key='export'))
      THROW 51000,'Amazon pipeline success requires a committed export witness',1;
   IF EXISTS(SELECT 1 FROM monitoring.etl_step_runs WHERE execution_key=@execution_key
              AND status IN ('STARTED','WAITING_DBT','IN_DOUBT'))
      THROW 51000,'Execution still has unresolved steps',1;
  END;
  IF @status NOT IN ('STARTED','WAITING_DBT','IN_DOUBT') AND EXISTS(
       SELECT 1 FROM monitoring.etl_step_runs WHERE execution_key=@execution_key
         AND status IN ('STARTED','WAITING_DBT','IN_DOUBT'))
    THROW 51000,'Close or reconcile all active steps before closing execution',1;
  UPDATE monitoring.etl_runs SET status=@status,
     end_time=CASE WHEN @status IN ('IN_DOUBT','WAITING_DBT') THEN NULL ELSE SYSUTCDATETIME() END,
     heartbeat_at=SYSUTCDATETIME() WHERE execution_key=@execution_key;
  COMMIT;
 END TRY
 BEGIN CATCH
  IF @@TRANCOUNT>0 ROLLBACK;
  THROW;
 END CATCH;
END;
GO
