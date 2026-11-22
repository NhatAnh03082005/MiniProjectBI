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
IF DATABASE_PRINCIPAL_ID('etl_monitoring_writer') IS NULL
 CREATE ROLE etl_monitoring_writer AUTHORIZATION dbo;
GRANT SELECT,INSERT,UPDATE ON SCHEMA::monitoring TO etl_monitoring_writer;
GRANT EXECUTE ON SCHEMA::monitoring TO etl_monitoring_writer;
-- Do not assign any login automatically. Review a non-sysadmin service identity
-- separately. No grants on dw.*, staging.* or audit.* are introduced here.
GO
