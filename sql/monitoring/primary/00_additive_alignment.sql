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
SET XACT_ABORT ON;
SET LOCK_TIMEOUT 5000;
BEGIN TRY
 BEGIN TRANSACTION;
 IF OBJECT_ID('audit.load_batch','U') IS NULL
    OR OBJECT_ID('staging.raw_amazon_delivery','U') IS NULL
    THROW 51000, 'Expected legacy tables are missing.', 1;
 IF EXISTS(SELECT 1 FROM staging.raw_amazon_delivery
           WHERE Order_ID IS NULL OR LTRIM(RTRIM(Order_ID))='')
    THROW 51000, 'Resolve invalid source keys with owner before rollout.', 1;
 IF EXISTS(SELECT LOWER(LTRIM(RTRIM(Order_ID))) FROM staging.raw_amazon_delivery
           GROUP BY LOWER(LTRIM(RTRIM(Order_ID))) HAVING COUNT_BIG(*)>1)
    THROW 51000, 'Normalized duplicate keys: no automatic repair allowed.', 1;

 IF COL_LENGTH('audit.load_batch','rows_valid') IS NULL
    ALTER TABLE audit.load_batch ADD rows_valid bigint NULL;
 IF COL_LENGTH('audit.load_batch','rows_inserted') IS NULL
    ALTER TABLE audit.load_batch ADD rows_inserted int NULL;
 IF COL_LENGTH('audit.load_batch','rows_updated') IS NULL
    ALTER TABLE audit.load_batch ADD rows_updated int NULL;
 IF COL_LENGTH('audit.load_batch','rows_unchanged') IS NULL
    ALTER TABLE audit.load_batch ADD rows_unchanged int NULL;
 IF COL_LENGTH('audit.load_batch','metric_definition_version') IS NULL
    ALTER TABLE audit.load_batch ADD metric_definition_version varchar(32) NULL;
 -- Existing non-null/default action columns require separate provenance review.
 IF EXISTS(SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('audit.load_batch')
           AND name IN ('rows_valid','rows_inserted','rows_updated','rows_unchanged',
                        'metric_definition_version')
           AND (is_nullable=0 OR default_object_id<>0))
    THROW 51000, 'Existing metrics have defaults or NOT NULL: review history provenance.', 1;

 IF COL_LENGTH('staging.raw_amazon_delivery','row_hash') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD row_hash char(64) NULL;
 IF COL_LENGTH('staging.raw_amazon_delivery','updated_load_batch_id') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD updated_load_batch_id varchar(64) NULL;
 IF COL_LENGTH('staging.raw_amazon_delivery','updated_at') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD updated_at datetime2(3) NULL;
 IF COL_LENGTH('staging.raw_amazon_delivery','updated_source_file_name') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD updated_source_file_name nvarchar(260) NULL;
 IF COL_LENGTH('staging.raw_amazon_delivery','updated_source_row_number') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD updated_source_row_number bigint NULL;
 IF EXISTS(SELECT 1 FROM (VALUES
       ('audit.load_batch','rows_valid','bigint',8),
       ('audit.load_batch','rows_inserted','int',4),
       ('audit.load_batch','rows_updated','int',4),
       ('audit.load_batch','rows_unchanged','int',4),
       ('audit.load_batch','metric_definition_version','varchar',32),
       ('staging.raw_amazon_delivery','row_hash','char',64),
       ('staging.raw_amazon_delivery','updated_load_batch_id','varchar',64),
       ('staging.raw_amazon_delivery','updated_at','datetime2',7),
       ('staging.raw_amazon_delivery','updated_source_file_name','nvarchar',520),
       ('staging.raw_amazon_delivery','updated_source_row_number','bigint',8)
      ) expected(object_name,column_name,type_name,max_length)
      LEFT JOIN sys.columns c ON c.object_id=OBJECT_ID(expected.object_name) AND c.name=expected.column_name
      WHERE c.column_id IS NULL OR TYPE_NAME(c.user_type_id)<>expected.type_name
        OR c.max_length<>expected.max_length OR c.is_nullable<>1 OR c.default_object_id<>0)
    THROW 51000, 'Unexpected existing column contract: no automatic type/default repair.', 1;

 -- No historical lineage is invented. Future updates alone populate updated_*.
 IF OBJECT_ID('audit.CK_load_batch_name_type','C') IS NOT NULL
    ALTER TABLE audit.load_batch DROP CONSTRAINT CK_load_batch_name_type;
 IF OBJECT_ID('audit.CK_load_batch_batch_name','C') IS NULL
 ALTER TABLE audit.load_batch WITH CHECK ADD CONSTRAINT CK_load_batch_batch_name
    CHECK(LEN(LTRIM(RTRIM(batch_name)))>0);
 IF OBJECT_ID('audit.CK_load_batch_monitoring_counts','C') IS NULL
    EXEC(N'ALTER TABLE audit.load_batch WITH CHECK ADD CONSTRAINT CK_load_batch_monitoring_counts
       CHECK((rows_valid IS NULL OR rows_valid>=0)
         AND (rows_inserted IS NULL OR rows_inserted>=0)
         AND (rows_updated IS NULL OR rows_updated>=0)
         AND (rows_unchanged IS NULL OR rows_unchanged>=0));');
 IF NOT EXISTS(SELECT 1 FROM sys.foreign_keys
               WHERE parent_object_id=OBJECT_ID('staging.raw_amazon_delivery')
                 AND name='FK_raw_amazon_delivery_updated_load_batch')
    EXEC(N'ALTER TABLE staging.raw_amazon_delivery WITH CHECK
       ADD CONSTRAINT FK_raw_amazon_delivery_updated_load_batch
       FOREIGN KEY(updated_load_batch_id) REFERENCES audit.load_batch(load_batch_id);');
 COMMIT;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK;
 THROW;
END CATCH;
