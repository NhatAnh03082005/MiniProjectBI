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
