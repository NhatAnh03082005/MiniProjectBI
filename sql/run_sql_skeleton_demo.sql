/*
All-in-one deployment for AmazonDeliveryBI_Demo.
Chạy trực tiếp bằng SSMS hoặc sqlcmd; không dùng :r, không cần SQLCMD Mode.
Script idempotent và không xóa dữ liệu hiện có.
*/
USE master;
GO

IF DB_ID(N'AmazonDeliveryBI_Demo') IS NULL
BEGIN
    CREATE DATABASE AmazonDeliveryBI_Demo;
    PRINT N'Đã tạo database AmazonDeliveryBI_Demo.';
END
ELSE PRINT N'Database AmazonDeliveryBI_Demo đã tồn tại; chuyển sang migration.';
GO

USE AmazonDeliveryBI_Demo;
GO
IF SCHEMA_ID(N'staging') IS NULL EXEC(N'CREATE SCHEMA staging');
IF SCHEMA_ID(N'dw') IS NULL EXEC(N'CREATE SCHEMA dw');
IF SCHEMA_ID(N'audit') IS NULL EXEC(N'CREATE SCHEMA audit');
GO

IF OBJECT_ID(N'audit.load_batch', N'U') IS NULL
BEGIN
    CREATE TABLE audit.load_batch
    (
        load_batch_id VARCHAR(64) NOT NULL,
        batch_name VARCHAR(50) NOT NULL,
        batch_type VARCHAR(20) NOT NULL,
        source_file_name NVARCHAR(260) NOT NULL,
        source_file_checksum CHAR(64) NOT NULL,
        expected_date_from DATE NULL,
        expected_date_to DATE NULL,
        expected_row_count INT NULL,
        started_at DATETIME2(3) NOT NULL CONSTRAINT DF_load_batch_started_at DEFAULT (SYSUTCDATETIME()),
        finished_at DATETIME2(3) NULL,
        status VARCHAR(20) NOT NULL,
        rows_read INT NOT NULL CONSTRAINT DF_load_batch_rows_read DEFAULT (0),
        rows_loaded INT NOT NULL CONSTRAINT DF_load_batch_rows_loaded DEFAULT (0),
        rows_rejected INT NOT NULL CONSTRAINT DF_load_batch_rows_rejected DEFAULT (0),
        rows_inserted INT NOT NULL CONSTRAINT DF_load_batch_rows_inserted DEFAULT (0),
        rows_updated INT NOT NULL CONSTRAINT DF_load_batch_rows_updated DEFAULT (0),
        rows_unchanged INT NOT NULL CONSTRAINT DF_load_batch_rows_unchanged DEFAULT (0),
        error_message NVARCHAR(MAX) NULL,
        CONSTRAINT PK_load_batch PRIMARY KEY (load_batch_id),
        CONSTRAINT CK_load_batch_batch_type CHECK (batch_type IN ('FULL_LOAD', 'INCREMENTAL')),
        CONSTRAINT CK_load_batch_batch_name CHECK (LEN(LTRIM(RTRIM(batch_name))) > 0),
        CONSTRAINT CK_load_batch_status CHECK (status IN ('STARTED', 'SUCCEEDED', 'FAILED', 'SKIPPED')),
        CONSTRAINT CK_load_batch_checksum CHECK (source_file_checksum COLLATE Latin1_General_100_BIN2 NOT LIKE '%[^0-9A-Fa-f]%'),
        CONSTRAINT CK_load_batch_expected_dates CHECK (
            (expected_date_from IS NULL AND expected_date_to IS NULL)
            OR (expected_date_from IS NOT NULL AND expected_date_to IS NOT NULL AND expected_date_from <= expected_date_to)
        ),
        CONSTRAINT CK_load_batch_expected_row_count CHECK (expected_row_count IS NULL OR expected_row_count >= 0),
        CONSTRAINT CK_load_batch_row_counts CHECK (
            rows_read >= 0 AND rows_loaded >= 0 AND rows_rejected >= 0
            AND rows_inserted >= 0 AND rows_updated >= 0 AND rows_unchanged >= 0
        ),
        CONSTRAINT CK_load_batch_finished_at CHECK (finished_at IS NULL OR finished_at >= started_at)
    );
END;
GO

IF COL_LENGTH(N'audit.load_batch', N'rows_inserted') IS NULL
    ALTER TABLE audit.load_batch ADD rows_inserted INT NOT NULL CONSTRAINT DF_load_batch_rows_inserted DEFAULT (0) WITH VALUES;
GO
IF COL_LENGTH(N'audit.load_batch', N'rows_updated') IS NULL
    ALTER TABLE audit.load_batch ADD rows_updated INT NOT NULL CONSTRAINT DF_load_batch_rows_updated DEFAULT (0) WITH VALUES;
GO
IF COL_LENGTH(N'audit.load_batch', N'rows_unchanged') IS NULL
    ALTER TABLE audit.load_batch ADD rows_unchanged INT NOT NULL CONSTRAINT DF_load_batch_rows_unchanged DEFAULT (0) WITH VALUES;
GO

IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE parent_object_id = OBJECT_ID(N'audit.load_batch') AND name = N'CK_load_batch_batch_name')
    ALTER TABLE audit.load_batch DROP CONSTRAINT CK_load_batch_batch_name;
GO
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE parent_object_id = OBJECT_ID(N'audit.load_batch') AND name = N'CK_load_batch_name_type')
    ALTER TABLE audit.load_batch DROP CONSTRAINT CK_load_batch_name_type;
GO
ALTER TABLE audit.load_batch WITH CHECK ADD CONSTRAINT CK_load_batch_batch_name CHECK (LEN(LTRIM(RTRIM(batch_name))) > 0);
GO
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE parent_object_id = OBJECT_ID(N'audit.load_batch') AND name = N'CK_load_batch_row_counts')
    ALTER TABLE audit.load_batch DROP CONSTRAINT CK_load_batch_row_counts;
GO
ALTER TABLE audit.load_batch WITH CHECK ADD CONSTRAINT CK_load_batch_row_counts CHECK (
    rows_read >= 0 AND rows_loaded >= 0 AND rows_rejected >= 0
    AND rows_inserted >= 0 AND rows_updated >= 0 AND rows_unchanged >= 0
);
GO

IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'audit.load_batch') AND name = N'IX_load_batch_batch_name_status')
    DROP INDEX IX_load_batch_batch_name_status ON audit.load_batch;
GO
CREATE INDEX IX_load_batch_batch_name_status ON audit.load_batch (batch_name, status)
INCLUDE (source_file_checksum, expected_date_from, expected_date_to, expected_row_count,
         rows_read, rows_loaded, rows_inserted, rows_updated, rows_unchanged, finished_at);
GO

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF;
GO

IF OBJECT_ID(N'staging.raw_amazon_delivery', N'U') IS NULL
BEGIN
    CREATE TABLE staging.raw_amazon_delivery
    (
        staging_row_id BIGINT IDENTITY(1,1) NOT NULL,
        Order_ID VARCHAR(32) NULL,
        Agent_Age VARCHAR(16) NULL,
        Agent_Rating VARCHAR(16) NULL,
        Store_Latitude VARCHAR(32) NULL,
        Store_Longitude VARCHAR(32) NULL,
        Drop_Latitude VARCHAR(32) NULL,
        Drop_Longitude VARCHAR(32) NULL,
        Order_Date VARCHAR(16) NULL,
        Order_Time VARCHAR(16) NULL,
        Pickup_Time VARCHAR(16) NULL,
        Weather VARCHAR(32) NULL,
        Traffic VARCHAR(32) NULL,
        Vehicle VARCHAR(32) NULL,
        Area VARCHAR(64) NULL,
        Delivery_Time VARCHAR(16) NULL,
        Category VARCHAR(64) NULL,
        source_file_name NVARCHAR(260) NOT NULL,
        source_row_number BIGINT NOT NULL,
        load_batch_id VARCHAR(64) NOT NULL,
        loaded_at DATETIME2(3) NOT NULL,
        row_hash CHAR(64) NULL,
        updated_load_batch_id VARCHAR(64) NULL,
        updated_at DATETIME2(3) NULL,
        updated_source_file_name NVARCHAR(260) NULL,
        updated_source_row_number BIGINT NULL,
        CONSTRAINT PK_raw_amazon_delivery PRIMARY KEY (staging_row_id),
        CONSTRAINT FK_raw_amazon_delivery_load_batch FOREIGN KEY (load_batch_id) REFERENCES audit.load_batch (load_batch_id),
        CONSTRAINT FK_raw_amazon_delivery_updated_load_batch FOREIGN KEY (updated_load_batch_id) REFERENCES audit.load_batch (load_batch_id)
    );
END;
GO

IF COL_LENGTH(N'staging.raw_amazon_delivery', N'row_hash') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD row_hash CHAR(64) NULL;
GO
IF COL_LENGTH(N'staging.raw_amazon_delivery', N'updated_load_batch_id') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD updated_load_batch_id VARCHAR(64) NULL;
GO
IF COL_LENGTH(N'staging.raw_amazon_delivery', N'updated_at') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD updated_at DATETIME2(3) NULL;
GO
IF COL_LENGTH(N'staging.raw_amazon_delivery', N'updated_source_file_name') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD updated_source_file_name NVARCHAR(260) NULL;
GO
IF COL_LENGTH(N'staging.raw_amazon_delivery', N'updated_source_row_number') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD updated_source_row_number BIGINT NULL;
GO

UPDATE staging.raw_amazon_delivery
SET updated_load_batch_id = COALESCE(updated_load_batch_id, load_batch_id),
    updated_at = COALESCE(updated_at, loaded_at),
    updated_source_file_name = COALESCE(updated_source_file_name, source_file_name),
    updated_source_row_number = COALESCE(updated_source_row_number, source_row_number)
WHERE updated_load_batch_id IS NULL OR updated_at IS NULL
   OR updated_source_file_name IS NULL OR updated_source_row_number IS NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE parent_object_id = OBJECT_ID(N'staging.raw_amazon_delivery') AND name = N'FK_raw_amazon_delivery_updated_load_batch')
    ALTER TABLE staging.raw_amazon_delivery WITH CHECK ADD CONSTRAINT FK_raw_amazon_delivery_updated_load_batch
        FOREIGN KEY (updated_load_batch_id) REFERENCES audit.load_batch (load_batch_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'staging.raw_amazon_delivery') AND name = N'IX_raw_amazon_delivery_load_batch_id')
    CREATE INDEX IX_raw_amazon_delivery_load_batch_id ON staging.raw_amazon_delivery (load_batch_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'staging.raw_amazon_delivery') AND name = N'IX_raw_amazon_delivery_updated_load_batch_id')
    CREATE INDEX IX_raw_amazon_delivery_updated_load_batch_id ON staging.raw_amazon_delivery (updated_load_batch_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'staging.raw_amazon_delivery') AND name = N'UX_raw_amazon_delivery_batch_source_row')
    CREATE UNIQUE INDEX UX_raw_amazon_delivery_batch_source_row ON staging.raw_amazon_delivery (load_batch_id, source_row_number);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'staging.raw_amazon_delivery') AND name = N'UX_raw_amazon_delivery_order_id')
    CREATE UNIQUE INDEX UX_raw_amazon_delivery_order_id ON staging.raw_amazon_delivery (Order_ID) WHERE Order_ID IS NOT NULL;
GO

IF OBJECT_ID(N'audit.load_batch', N'U') IS NULL THROW 51000, 'Thiếu audit.load_batch.', 1;
IF OBJECT_ID(N'staging.raw_amazon_delivery', N'U') IS NULL THROW 51000, 'Thiếu staging.raw_amazon_delivery.', 1;
GO
IF EXISTS (
    SELECT required.name FROM (VALUES (N'rows_inserted'), (N'rows_updated'), (N'rows_unchanged')) required(name)
    WHERE COL_LENGTH(N'audit.load_batch', required.name) IS NULL
) THROW 51000, 'audit.load_batch thiếu action counter.', 1;
GO
IF EXISTS (
    SELECT required.name FROM (VALUES (N'row_hash'), (N'updated_load_batch_id'), (N'updated_at'),
        (N'updated_source_file_name'), (N'updated_source_row_number')) required(name)
    WHERE COL_LENGTH(N'staging.raw_amazon_delivery', required.name) IS NULL
) THROW 51000, 'staging.raw_amazon_delivery thiếu upsert metadata.', 1;
GO
IF EXISTS (
    SELECT 1 FROM audit.load_batch
    WHERE status = 'SUCCEEDED'
      AND rows_read <> rows_inserted + rows_updated + rows_unchanged + rows_rejected
      AND batch_name LIKE 'amazon_delivery_%'
) THROW 51000, 'Có dynamic batch không đối soát được action counter.', 1;
GO
IF EXISTS (
    SELECT LOWER(LTRIM(RTRIM(Order_ID))) FROM staging.raw_amazon_delivery
    WHERE Order_ID IS NOT NULL
    GROUP BY LOWER(LTRIM(RTRIM(Order_ID))) HAVING COUNT_BIG(*) > 1
) THROW 51000, 'Staging có Order_ID trùng sau trim/case-fold.', 1;
GO

SELECT DB_NAME() AS database_name,
    (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery) AS staging_rows,
    (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery WHERE row_hash IS NOT NULL) AS rows_with_hash,
    (SELECT COUNT_BIG(*) FROM audit.load_batch) AS audit_batches,
    (SELECT COUNT_BIG(*) FROM audit.load_batch WHERE batch_name LIKE 'amazon_delivery_%') AS dynamic_batches;
GO
PRINT N'AmazonDeliveryBI_Demo deployment và validation thành công.';
GO

/* BEGIN INTEGRATED DBT AUDIT AND ETL MONITORING */

USE [AmazonDeliveryBI_Demo];
GO

-- dbt attempt audit (linked to ingestion batch).

/* Run in the SAME database as Mage. No USE/GO: also executed by the runner.
   One row per dbt attempt, not per ingestion batch. Existing audit is preserved. */
IF OBJECT_ID(N'audit.dbt_run', N'U') IS NULL
BEGIN
    CREATE TABLE audit.dbt_run (
        dbt_attempt_id VARCHAR(64) NOT NULL PRIMARY KEY,
        load_batch_id VARCHAR(64) NOT NULL,
        status VARCHAR(20) NOT NULL,
        started_at DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        finished_at DATETIME2(3) NULL,
        exit_code INT NULL,
        log_directory NVARCHAR(1024) NOT NULL,
        result_summary NVARCHAR(MAX) NULL,
        error_message NVARCHAR(2000) NULL,
        CONSTRAINT FK_dbt_run_load_batch FOREIGN KEY (load_batch_id)
            REFERENCES audit.load_batch(load_batch_id),
        CONSTRAINT CK_dbt_run_status CHECK (status IN ('STARTED', 'SUCCEEDED', 'FAILED'))
    );
    CREATE INDEX IX_dbt_run_batch ON audit.dbt_run(load_batch_id, started_at);
END;

GO

-- Integrated source: sql/monitoring/demo/01_monitoring_schema.sql

/* DEMO only. Run in SSMS. Creates monitoring objects; no business data reset. */
USE AmazonDeliveryBI_Demo;
GO
IF DB_NAME() <> 'AmazonDeliveryBI_Demo' THROW 51000,'DEMO target required',1;
SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS ON; SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON; SET ARITHABORT ON; SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF; SET XACT_ABORT ON;
GO
IF SCHEMA_ID('monitoring') IS NULL EXEC('CREATE SCHEMA monitoring AUTHORIZATION dbo');
BEGIN TRY
 BEGIN TRAN;
IF OBJECT_ID('monitoring.etl_runs') IS NOT NULL AND OBJECT_ID('monitoring.etl_runs','U') IS NULL THROW 51000,'Unexpected object type',1;
IF OBJECT_ID('monitoring.etl_runs','U') IS NULL
BEGIN
CREATE TABLE monitoring.etl_runs (
    execution_key uniqueidentifier NOT NULL DEFAULT NEWID() PRIMARY KEY,
    run_id uniqueidentifier NOT NULL,
    attempt_id int NOT NULL CHECK (attempt_id > 0),
    pipeline_name nvarchar(128) NOT NULL,
    batch_type varchar(20) NOT NULL CHECK (batch_type IN ('FULL_LOAD','INCREMENTAL','DBT_ONLY')),
    execution_kind varchar(16) NOT NULL DEFAULT 'MAGE_DBT' CHECK(execution_kind IN ('MAGE_DBT','DBT_ONLY')),
    source_file nvarchar(260) NULL,
    source_checksum char(64) NULL,
    legacy_load_batch_id varchar(64) NULL,
    mage_pipeline_run_id nvarchar(128) NULL,
    evidence_kind varchar(8) NOT NULL CHECK(evidence_kind IN ('REAL','TEST')),
    status varchar(20) NOT NULL CHECK (status IN
       ('STARTED','WAITING_DBT','IN_DOUBT','SUCCEEDED','FAILED','CANCELLED','SKIPPED','ABANDONED')),
    start_time datetime2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    end_time datetime2(3) NULL,
    heartbeat_at datetime2(3) NULL,
    metric_definition_version varchar(32) NOT NULL,
    CONSTRAINT UQ_etl_runs_attempt UNIQUE(run_id,attempt_id),
    CHECK ((status IN ('STARTED','WAITING_DBT','IN_DOUBT') AND end_time IS NULL) OR
           (status NOT IN ('STARTED','WAITING_DBT','IN_DOUBT') AND end_time IS NOT NULL)),
    CHECK (end_time IS NULL OR end_time>=start_time)
);
END;
IF OBJECT_ID('monitoring.etl_step_runs') IS NOT NULL AND OBJECT_ID('monitoring.etl_step_runs','U') IS NULL THROW 51000,'Unexpected object type',1;
IF OBJECT_ID('monitoring.etl_step_runs','U') IS NULL
BEGIN
CREATE TABLE monitoring.etl_step_runs (
    execution_key uniqueidentifier NOT NULL REFERENCES monitoring.etl_runs(execution_key),
    step_key varchar(128) NOT NULL,
    step_attempt int NOT NULL CHECK (step_attempt>0),
    component varchar(20) NOT NULL CHECK(component IN ('SOURCE','MAGE','DBT','WAREHOUSE')),
    external_execution_id nvarchar(512) NULL,
    dbt_invocation_id uniqueidentifier NULL,
    native_duration_seconds decimal(20,6) NULL,
    native_failures bigint NULL,
    native_status varchar(32) NULL,
    resource_type varchar(32) NULL,
    artifact_sha256 char(64) NULL,
    dbt_command varchar(32) NULL,
    process_exit_code int NULL,
    artifact_verified bit NOT NULL DEFAULT (0),
    artifact_path nvarchar(1024) NULL,
    status varchar(20) NOT NULL CHECK(status IN
       ('NOT_STARTED','STARTED','IN_DOUBT','SUCCEEDED','FAILED','CANCELLED','SKIPPED','ABANDONED')),
    start_time datetime2(3) NULL,
    end_time datetime2(3) NULL,
    PRIMARY KEY(execution_key,step_key,step_attempt),
    CHECK (end_time IS NULL OR (start_time IS NOT NULL AND end_time>=start_time)),
    CHECK (status NOT IN ('STARTED','WAITING_DBT','IN_DOUBT') OR (start_time IS NOT NULL AND end_time IS NULL)),
    CHECK (status<>'NOT_STARTED' OR (start_time IS NULL AND end_time IS NULL)),
    CHECK (status NOT IN ('CANCELLED','SKIPPED') OR
       (start_time IS NULL AND end_time IS NULL) OR
       (start_time IS NOT NULL AND end_time IS NOT NULL)),
    CHECK (status NOT IN ('SUCCEEDED','FAILED','ABANDONED') OR
           (start_time IS NOT NULL AND end_time IS NOT NULL) OR
           (status='FAILED' AND start_time IS NULL AND end_time IS NULL)),
    CHECK (step_key NOT IN ('source','mage','dbt','warehouse') OR
       (step_key='source' AND component='SOURCE') OR
       (step_key='mage' AND component='MAGE') OR
       (step_key='dbt' AND component='DBT') OR
       (step_key='warehouse' AND component='WAREHOUSE')),
    CHECK (artifact_verified=0 OR
       (component='DBT' AND dbt_invocation_id IS NOT NULL AND artifact_path IS NOT NULL))
);
END;
IF OBJECT_ID('monitoring.etl_record_metrics') IS NOT NULL AND OBJECT_ID('monitoring.etl_record_metrics','U') IS NULL THROW 51000,'Unexpected object type',1;
IF OBJECT_ID('monitoring.etl_record_metrics','U') IS NULL
BEGIN
CREATE TABLE monitoring.etl_record_metrics (
    execution_key uniqueidentifier NOT NULL,
    step_key varchar(128) NOT NULL,
    step_attempt int NOT NULL,
    metric_scope varchar(64) NOT NULL,
    entity_name nvarchar(128) NOT NULL,
    measurement_state varchar(16) NOT NULL CHECK(measurement_state IN ('OBSERVED','COMMITTED')),
    records_read bigint NULL CHECK(records_read>=0),
    records_valid bigint NULL CHECK(records_valid>=0),
    records_inserted bigint NULL CHECK(records_inserted>=0),
    records_updated bigint NULL CHECK(records_updated>=0),
    records_unchanged bigint NULL CHECK(records_unchanged>=0),
    records_rejected bigint NULL CHECK(records_rejected>=0),
    records_written bigint NULL CHECK(records_written>=0),
    captured_at datetime2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    PRIMARY KEY(execution_key,step_key,step_attempt,metric_scope,entity_name),
    FOREIGN KEY(execution_key,step_key,step_attempt)
       REFERENCES monitoring.etl_step_runs(execution_key,step_key,step_attempt),
    CHECK (measurement_state='COMMITTED' OR
       (records_inserted IS NULL AND records_updated IS NULL
        AND records_unchanged IS NULL AND records_written IS NULL))
);
END;
IF OBJECT_ID('monitoring.etl_errors') IS NOT NULL AND OBJECT_ID('monitoring.etl_errors','U') IS NULL THROW 51000,'Unexpected object type',1;
IF OBJECT_ID('monitoring.etl_errors','U') IS NULL
BEGIN
CREATE TABLE monitoring.etl_errors (
    error_id bigint IDENTITY PRIMARY KEY,
    execution_key uniqueidentifier NOT NULL REFERENCES monitoring.etl_runs(execution_key),
    step_key varchar(128) NULL,
    step_attempt int NULL,
    severity varchar(10) NOT NULL CHECK(severity IN ('ERROR','WARNING','INFO')),
    error_code nvarchar(128) NULL,
    message nvarchar(max) NOT NULL,
    occurred_at datetime2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    CHECK ((step_key IS NULL AND step_attempt IS NULL) OR
           (step_key IS NOT NULL AND step_attempt IS NOT NULL)),
    FOREIGN KEY(execution_key,step_key,step_attempt)
       REFERENCES monitoring.etl_step_runs(execution_key,step_key,step_attempt)
);
END;
IF COL_LENGTH('monitoring.etl_errors','event_key') IS NULL
 ALTER TABLE monitoring.etl_errors ADD event_key uniqueidentifier NULL;
IF EXISTS(SELECT 1 FROM (VALUES
('etl_errors','error_id','bigint',8,19,0,0,1),
('etl_errors','execution_key','uniqueidentifier',16,0,0,0,0),
('etl_errors','step_key','varchar',128,0,0,1,0),
('etl_errors','step_attempt','int',4,10,0,1,0),
('etl_errors','severity','varchar',10,0,0,0,0),
('etl_errors','error_code','nvarchar',256,0,0,1,0),
('etl_errors','message','nvarchar',-1,0,0,0,0),
('etl_errors','occurred_at','datetime2',7,23,3,0,0),
('etl_record_metrics','execution_key','uniqueidentifier',16,0,0,0,0),
('etl_record_metrics','step_key','varchar',128,0,0,0,0),
('etl_record_metrics','step_attempt','int',4,10,0,0,0),
('etl_record_metrics','metric_scope','varchar',64,0,0,0,0),
('etl_record_metrics','entity_name','nvarchar',256,0,0,0,0),
('etl_record_metrics','measurement_state','varchar',16,0,0,0,0),
('etl_record_metrics','records_read','bigint',8,19,0,1,0),
('etl_record_metrics','records_valid','bigint',8,19,0,1,0),
('etl_record_metrics','records_inserted','bigint',8,19,0,1,0),
('etl_record_metrics','records_updated','bigint',8,19,0,1,0),
('etl_record_metrics','records_unchanged','bigint',8,19,0,1,0),
('etl_record_metrics','records_rejected','bigint',8,19,0,1,0),
('etl_record_metrics','records_written','bigint',8,19,0,1,0),
('etl_record_metrics','captured_at','datetime2',7,23,3,0,0),
('etl_runs','execution_key','uniqueidentifier',16,0,0,0,0),
('etl_runs','run_id','uniqueidentifier',16,0,0,0,0),
('etl_runs','attempt_id','int',4,10,0,0,0),
('etl_runs','pipeline_name','nvarchar',256,0,0,0,0),
('etl_runs','batch_type','varchar',20,0,0,0,0),
('etl_runs','execution_kind','varchar',16,0,0,0,0),
('etl_runs','source_file','nvarchar',520,0,0,1,0),
('etl_runs','source_checksum','char',64,0,0,1,0),
('etl_runs','legacy_load_batch_id','varchar',64,0,0,1,0),
('etl_runs','mage_pipeline_run_id','nvarchar',256,0,0,1,0),
('etl_runs','evidence_kind','varchar',8,0,0,0,0),
('etl_runs','status','varchar',20,0,0,0,0),
('etl_runs','start_time','datetime2',7,23,3,0,0),
('etl_runs','end_time','datetime2',7,23,3,1,0),
('etl_runs','heartbeat_at','datetime2',7,23,3,1,0),
('etl_runs','metric_definition_version','varchar',32,0,0,0,0),
('etl_step_runs','execution_key','uniqueidentifier',16,0,0,0,0),
('etl_step_runs','step_key','varchar',128,0,0,0,0),
('etl_step_runs','step_attempt','int',4,10,0,0,0),
('etl_step_runs','component','varchar',20,0,0,0,0),
('etl_step_runs','external_execution_id','nvarchar',1024,0,0,1,0),
('etl_step_runs','dbt_invocation_id','uniqueidentifier',16,0,0,1,0),
('etl_step_runs','native_status','varchar',32,0,0,1,0),
('etl_step_runs','resource_type','varchar',32,0,0,1,0),
('etl_step_runs','artifact_sha256','char',64,0,0,1,0),
('etl_step_runs','dbt_command','varchar',32,0,0,1,0),
('etl_step_runs','process_exit_code','int',4,10,0,1,0),
('etl_step_runs','artifact_verified','bit',1,1,0,0,0),
('etl_step_runs','artifact_path','nvarchar',2048,0,0,1,0),
('etl_step_runs','status','varchar',20,0,0,0,0),
('etl_step_runs','start_time','datetime2',7,23,3,1,0),
('etl_step_runs','end_time','datetime2',7,23,3,1,0),
('etl_step_runs','native_duration_seconds','decimal',13,20,6,1,0),
('etl_step_runs','native_failures','bigint',8,19,0,1,0),
('etl_errors','event_key','uniqueidentifier',16,0,0,1,0)
) expected(tbl,col,typ,len,prec,scale,nullable,identity_col)
 LEFT JOIN sys.columns c ON c.object_id=OBJECT_ID('monitoring.'+expected.tbl) AND c.name=expected.col
 WHERE c.column_id IS NULL OR TYPE_NAME(c.user_type_id)<>expected.typ
 OR c.max_length<>expected.len OR c.precision<>expected.prec OR c.scale<>expected.scale
 OR c.is_nullable<>expected.nullable OR c.is_identity<>expected.identity_col)
 THROW 51000,'Existing monitoring column contract mismatch; no automatic repair',1;
IF ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.key_constraints k JOIN sys.index_columns ic ON ic.object_id=k.parent_object_id AND ic.index_id=k.unique_index_id
 JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE k.parent_object_id=OBJECT_ID('monitoring.etl_runs') AND k.type='PK'),'')<>'execution_key'
 THROW 51000,'Monitoring PK grain mismatch: etl_runs',1;
IF ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.key_constraints k JOIN sys.index_columns ic ON ic.object_id=k.parent_object_id AND ic.index_id=k.unique_index_id
 JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE k.parent_object_id=OBJECT_ID('monitoring.etl_step_runs') AND k.type='PK'),'')<>'execution_key,step_key,step_attempt'
 THROW 51000,'Monitoring PK grain mismatch: etl_step_runs',1;
IF ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.key_constraints k JOIN sys.index_columns ic ON ic.object_id=k.parent_object_id AND ic.index_id=k.unique_index_id
 JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE k.parent_object_id=OBJECT_ID('monitoring.etl_record_metrics') AND k.type='PK'),'')<>'execution_key,step_key,step_attempt,metric_scope,entity_name'
 THROW 51000,'Monitoring PK grain mismatch: etl_record_metrics',1;
IF ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.key_constraints k JOIN sys.index_columns ic ON ic.object_id=k.parent_object_id AND ic.index_id=k.unique_index_id
 JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE k.parent_object_id=OBJECT_ID('monitoring.etl_errors') AND k.type='PK'),'')<>'error_id'
 THROW 51000,'Monitoring PK grain mismatch: etl_errors',1;
IF EXISTS(SELECT * FROM (VALUES
('etl_errors','execution_key','monitoring','etl_runs','execution_key',1),
('etl_errors','execution_key','monitoring','etl_step_runs','execution_key',1),
('etl_errors','step_key','monitoring','etl_step_runs','step_key',2),
('etl_errors','step_attempt','monitoring','etl_step_runs','step_attempt',3),
('etl_record_metrics','execution_key','monitoring','etl_step_runs','execution_key',1),
('etl_record_metrics','step_key','monitoring','etl_step_runs','step_key',2),
('etl_record_metrics','step_attempt','monitoring','etl_step_runs','step_attempt',3),
('etl_step_runs','execution_key','monitoring','etl_runs','execution_key',1)
) e(tbl,col,ref_schema,ref_tbl,ref_col,ordinal)
 EXCEPT SELECT t.name,c.name,rs.name,rt.name,rc.name,fc.constraint_column_id
 FROM sys.foreign_keys f JOIN sys.tables t ON t.object_id=f.parent_object_id
 JOIN sys.foreign_key_columns fc ON fc.constraint_object_id=f.object_id
 JOIN sys.columns c ON c.object_id=fc.parent_object_id AND c.column_id=fc.parent_column_id
 JOIN sys.tables rt ON rt.object_id=fc.referenced_object_id JOIN sys.schemas rs ON rs.schema_id=rt.schema_id
 JOIN sys.columns rc ON rc.object_id=fc.referenced_object_id AND rc.column_id=fc.referenced_column_id
 WHERE t.schema_id=SCHEMA_ID('monitoring')) THROW 51000,'Monitoring FK endpoint mismatch',1;
IF EXISTS(SELECT * FROM (VALUES
('etl_errors','(severity=''info''orseverity=''warning''orseverity=''error'')'),
('etl_errors','(step_keyisnullandstep_attemptisnullorstep_keyisnotnullandstep_attemptisnotnull)'),
('etl_record_metrics','(measurement_state=''committed''ormeasurement_state=''observed'')'),
('etl_record_metrics','(records_read>=(0))'),
('etl_record_metrics','(records_valid>=(0))'),
('etl_record_metrics','(records_inserted>=(0))'),
('etl_record_metrics','(records_updated>=(0))'),
('etl_record_metrics','(records_unchanged>=(0))'),
('etl_record_metrics','(records_rejected>=(0))'),
('etl_record_metrics','(records_written>=(0))'),
('etl_record_metrics','(measurement_state=''committed''orrecords_insertedisnullandrecords_updatedisnullandrecords_unchangedisnullandrecords_writtenisnull)'),
('etl_runs','((status=''in_doubt''orstatus=''waiting_dbt''orstatus=''started'')andend_timeisnullornot(status=''in_doubt''orstatus=''waiting_dbt''orstatus=''started'')andend_timeisnotnull)'),
('etl_runs','(end_timeisnullorend_time>=start_time)'),
('etl_runs','(attempt_id>(0))'),
('etl_runs','(batch_type=''dbt_only''orbatch_type=''incremental''orbatch_type=''full_load'')'),
('etl_runs','(evidence_kind=''test''orevidence_kind=''real'')'),
('etl_runs','(execution_kind=''dbt_only''orexecution_kind=''mage_dbt'')'),
('etl_runs','(status=''abandoned''orstatus=''skipped''orstatus=''cancelled''orstatus=''failed''orstatus=''succeeded''orstatus=''in_doubt''orstatus=''waiting_dbt''orstatus=''started'')'),
('etl_step_runs','(component=''warehouse''orcomponent=''dbt''orcomponent=''mage''orcomponent=''source'')'),
('etl_step_runs','(status=''abandoned''orstatus=''skipped''orstatus=''cancelled''orstatus=''failed''orstatus=''succeeded''orstatus=''in_doubt''orstatus=''started''orstatus=''not_started'')'),
('etl_step_runs','(step_attempt>(0))'),
('etl_step_runs','(end_timeisnullorstart_timeisnotnullandend_time>=start_time)'),
('etl_step_runs','(not(status=''in_doubt''orstatus=''waiting_dbt''orstatus=''started'')orstart_timeisnotnullandend_timeisnull)'),
('etl_step_runs','(status<>''not_started''orstart_timeisnullandend_timeisnull)'),
('etl_step_runs','(not(status=''skipped''orstatus=''cancelled'')orstart_timeisnullandend_timeisnullorstart_timeisnotnullandend_timeisnotnull)'),
('etl_step_runs','(not(step_key=''warehouse''orstep_key=''dbt''orstep_key=''mage''orstep_key=''source'')orstep_key=''source''andcomponent=''source''orstep_key=''mage''andcomponent=''mage''orstep_key=''dbt''andcomponent=''dbt''orstep_key=''warehouse''andcomponent=''warehouse'')'),
('etl_step_runs','(artifact_verified=(0)orcomponent=''dbt''anddbt_invocation_idisnotnullandartifact_pathisnotnull)'),
('etl_step_runs','(not(status=''abandoned''orstatus=''failed''orstatus=''succeeded'')orstart_timeisnotnullandend_timeisnotnullorstatus=''failed''andstart_timeisnullandend_timeisnull)')
) e(tbl,definition)
 EXCEPT SELECT t.name,LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(cc.definition,'[',''),']',''),' ',''),CHAR(13),''),CHAR(10),''),CHAR(9),''))
 FROM sys.check_constraints cc JOIN sys.tables t ON t.object_id=cc.parent_object_id
 WHERE t.schema_id=SCHEMA_ID('monitoring')) THROW 51000,'Monitoring CHECK contract mismatch',1;
IF EXISTS(SELECT * FROM (VALUES
('etl_errors','error_id',''),
('etl_errors','execution_key',''),
('etl_errors','step_key',''),
('etl_errors','step_attempt',''),
('etl_errors','severity',''),
('etl_errors','error_code',''),
('etl_errors','message',''),
('etl_errors','occurred_at','(sysutcdatetime())'),
('etl_record_metrics','execution_key',''),
('etl_record_metrics','step_key',''),
('etl_record_metrics','step_attempt',''),
('etl_record_metrics','metric_scope',''),
('etl_record_metrics','entity_name',''),
('etl_record_metrics','measurement_state',''),
('etl_record_metrics','records_read',''),
('etl_record_metrics','records_valid',''),
('etl_record_metrics','records_inserted',''),
('etl_record_metrics','records_updated',''),
('etl_record_metrics','records_unchanged',''),
('etl_record_metrics','records_rejected',''),
('etl_record_metrics','records_written',''),
('etl_record_metrics','captured_at','(sysutcdatetime())'),
('etl_runs','execution_key','(newid())'),
('etl_runs','run_id',''),
('etl_runs','attempt_id',''),
('etl_runs','pipeline_name',''),
('etl_runs','batch_type',''),
('etl_runs','execution_kind','(''mage_dbt'')'),
('etl_runs','source_file',''),
('etl_runs','source_checksum',''),
('etl_runs','legacy_load_batch_id',''),
('etl_runs','mage_pipeline_run_id',''),
('etl_runs','evidence_kind',''),
('etl_runs','status',''),
('etl_runs','start_time','(sysutcdatetime())'),
('etl_runs','end_time',''),
('etl_runs','heartbeat_at',''),
('etl_runs','metric_definition_version',''),
('etl_step_runs','execution_key',''),
('etl_step_runs','step_key',''),
('etl_step_runs','step_attempt',''),
('etl_step_runs','component',''),
('etl_step_runs','external_execution_id',''),
('etl_step_runs','dbt_invocation_id',''),
('etl_step_runs','native_status',''),
('etl_step_runs','resource_type',''),
('etl_step_runs','artifact_sha256',''),
('etl_step_runs','dbt_command',''),
('etl_step_runs','process_exit_code',''),
('etl_step_runs','artifact_verified','((0))'),
('etl_step_runs','artifact_path',''),
('etl_step_runs','status',''),
('etl_step_runs','start_time',''),
('etl_step_runs','end_time',''),
('etl_step_runs','native_duration_seconds',''),
('etl_step_runs','native_failures','')
) e(tbl,col,default_definition)
 EXCEPT SELECT t.name,c.name,LOWER(REPLACE(REPLACE(REPLACE(ISNULL(d.definition,''),'[',''),']',''),' ',''))
 FROM sys.tables t JOIN sys.columns c ON c.object_id=t.object_id
 LEFT JOIN sys.default_constraints d ON d.object_id=c.default_object_id
 WHERE t.schema_id=SCHEMA_ID('monitoring')) THROW 51000,'Monitoring default/UTC contract mismatch',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('monitoring.etl_runs') AND name='UX_etl_runs_legacy_batch')
CREATE UNIQUE INDEX UX_etl_runs_legacy_batch ON monitoring.etl_runs(legacy_load_batch_id)
    WHERE legacy_load_batch_id IS NOT NULL;
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('monitoring.etl_step_runs') AND name='UX_dbt_invocation')
CREATE UNIQUE INDEX UX_dbt_invocation ON monitoring.etl_step_runs(dbt_invocation_id)
    WHERE step_key='dbt' AND dbt_invocation_id IS NOT NULL;
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('monitoring.etl_errors') AND name='IX_etl_errors_execution')
CREATE INDEX IX_etl_errors_execution ON monitoring.etl_errors(execution_key,occurred_at,error_id);
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('monitoring.etl_runs') AND name='IX_etl_runs_start')
CREATE INDEX IX_etl_runs_start ON monitoring.etl_runs(start_time) INCLUDE(status,batch_type,evidence_kind);
IF NOT EXISTS(SELECT 1 FROM sys.indexes i WHERE i.object_id=OBJECT_ID('monitoring.etl_errors') AND i.name='IX_etl_errors_execution'
 AND i.is_unique=0 AND i.is_disabled=0
 AND LOWER(REPLACE(REPLACE(REPLACE(ISNULL(i.filter_definition,''),'[',''),']',''),' ',''))=''
 AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=0)='execution_key,occurred_at,error_id'
 AND ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY c.name)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=1),'')='')
 THROW 51000,'Monitoring index contract mismatch: IX_etl_errors_execution',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes i WHERE i.object_id=OBJECT_ID('monitoring.etl_runs') AND i.name='IX_etl_runs_start'
 AND i.is_unique=0 AND i.is_disabled=0
 AND LOWER(REPLACE(REPLACE(REPLACE(ISNULL(i.filter_definition,''),'[',''),']',''),' ',''))=''
 AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=0)='start_time'
 AND ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY c.name)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=1),'')='batch_type,evidence_kind,status')
 THROW 51000,'Monitoring index contract mismatch: IX_etl_runs_start',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes i WHERE i.object_id=OBJECT_ID('monitoring.etl_runs') AND i.name='UQ_etl_runs_attempt'
 AND i.is_unique=1 AND i.is_disabled=0
 AND LOWER(REPLACE(REPLACE(REPLACE(ISNULL(i.filter_definition,''),'[',''),']',''),' ',''))=''
 AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=0)='run_id,attempt_id'
 AND ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY c.name)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=1),'')='')
 THROW 51000,'Monitoring index contract mismatch: UQ_etl_runs_attempt',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes i WHERE i.object_id=OBJECT_ID('monitoring.etl_runs') AND i.name='UX_etl_runs_legacy_batch'
 AND i.is_unique=1 AND i.is_disabled=0
 AND LOWER(REPLACE(REPLACE(REPLACE(ISNULL(i.filter_definition,''),'[',''),']',''),' ',''))='(legacy_load_batch_idisnotnull)'
 AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=0)='legacy_load_batch_id'
 AND ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY c.name)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=1),'')='')
 THROW 51000,'Monitoring index contract mismatch: UX_etl_runs_legacy_batch',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes i WHERE i.object_id=OBJECT_ID('monitoring.etl_step_runs') AND i.name='UX_dbt_invocation'
 AND i.is_unique=1 AND i.is_disabled=0
 AND LOWER(REPLACE(REPLACE(REPLACE(ISNULL(i.filter_definition,''),'[',''),']',''),' ',''))='(step_key=''dbt''anddbt_invocation_idisnotnull)'
 AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=0)='dbt_invocation_id'
 AND ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY c.name)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=1),'')='')
 THROW 51000,'Monitoring index contract mismatch: UX_dbt_invocation',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('monitoring.etl_errors') AND name='UX_etl_errors_event')
 EXEC(N'CREATE UNIQUE INDEX UX_etl_errors_event ON monitoring.etl_errors(execution_key,event_key) WHERE event_key IS NOT NULL;');
IF EXISTS(SELECT 1 FROM sys.foreign_keys WHERE parent_object_id IN
 (OBJECT_ID('monitoring.etl_runs'),OBJECT_ID('monitoring.etl_step_runs'),OBJECT_ID('monitoring.etl_record_metrics'),OBJECT_ID('monitoring.etl_errors'))
 AND (is_disabled=1 OR is_not_trusted=1)) THROW 51000,'Untrusted monitoring FK',1;
IF EXISTS(SELECT 1 FROM sys.check_constraints WHERE schema_id=SCHEMA_ID('monitoring') AND (is_disabled=1 OR is_not_trusted=1))
 THROW 51000,'Untrusted monitoring CHECK',1;
IF EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=0 AND name='ETLMonitoring.Environment'
 AND CONVERT(nvarchar(128),value)<>N'APPROVED_DEMO')
 THROW 51000,'Environment marker conflict; no automatic repair',1;
IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=0 AND name='ETLMonitoring.Environment')
 EXEC sys.sp_addextendedproperty @name=N'ETLMonitoring.Environment',@value=N'APPROVED_DEMO';
 COMMIT;
END TRY BEGIN CATCH IF @@TRANCOUNT>0 ROLLBACK; THROW; END CATCH;
GO

-- Integrated source: sql/monitoring/demo/02_logging_procedures.sql

/* DEMO only. Run in SSMS. Creates monitoring objects; no business data reset. */
USE AmazonDeliveryBI_Demo;
GO
IF DB_NAME() <> 'AmazonDeliveryBI_Demo' THROW 51000,'DEMO target required',1;
SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS ON; SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON; SET ARITHABORT ON; SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF; SET XACT_ABORT ON;
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

-- Integrated source: sql/monitoring/demo/03_reporting_views.sql

/* DEMO only. Run in SSMS. Creates monitoring objects; no business data reset. */
USE AmazonDeliveryBI_Demo;
GO
IF DB_NAME() <> 'AmazonDeliveryBI_Demo' THROW 51000,'DEMO target required',1;
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

PRINT N'AmazonDeliveryBI_Demo: staging, audit, dbt attempt audit and ETL Monitoring deployment completed.';

GO

/* END INTEGRATED DBT AUDIT AND ETL MONITORING */
