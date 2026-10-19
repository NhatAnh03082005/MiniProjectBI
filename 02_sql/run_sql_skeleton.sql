/*
Purpose:
    Triển khai và kiểm tra toàn bộ SQL skeleton bằng một lần Execute trong SSMS.

Usage:
    Mở file này trong SQL Server Management Studio, kết nối đúng instance,
    sau đó chọn Execute. Không cần bật SQLCMD Mode.

Maintenance:
    File này tổng hợp năm SQL script thành phần theo đúng thứ tự phụ thuộc.
    Khi một script thành phần thay đổi, phải đồng bộ lại file tổng này.
*/

/* ========================================================================== */
/* 1. database/01_create_database.sql                                         */
/* ========================================================================== */

USE master;
GO

IF DB_ID(N'AmazonDeliveryBI') IS NULL
BEGIN
    CREATE DATABASE AmazonDeliveryBI;
    PRINT N'Đã tạo database AmazonDeliveryBI.';
END
ELSE
BEGIN
    PRINT N'Database AmazonDeliveryBI đã tồn tại, không tạo lại!!!';
END;
GO

/* ========================================================================== */
/* 2. database/02_create_schemas.sql                                          */
/* ========================================================================== */

USE AmazonDeliveryBI;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = N'staging'
)
BEGIN
    EXEC(N'CREATE SCHEMA staging');
    PRINT N'Đã tạo schema staging.';
END
ELSE
BEGIN
    PRINT N'Schema staging đã tồn tại.';
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = N'dw'
)
BEGIN
    EXEC(N'CREATE SCHEMA dw');
    PRINT N'Đã tạo schema dw.';
END
ELSE
BEGIN
    PRINT N'Schema dw đã tồn tại.';
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = N'audit'
)
BEGIN
    EXEC(N'CREATE SCHEMA audit');
    PRINT N'Đã tạo schema audit.';
END
ELSE
BEGIN
    PRINT N'Schema audit đã tồn tại.';
END;
GO

/* ========================================================================== */
/* 3. audit/01_create_load_batch.sql                                          */
/* ========================================================================== */

USE AmazonDeliveryBI;
GO

IF OBJECT_ID(
    N'audit.load_batch',
    N'U'
) IS NULL
BEGIN
    CREATE TABLE audit.load_batch
    (
        load_batch_id VARCHAR(64) NOT NULL,
        batch_type VARCHAR(20) NOT NULL,
        source_file_name NVARCHAR(260) NOT NULL,
        source_file_checksum CHAR(64) NOT NULL,

        expected_date_from DATE NULL,
        expected_date_to DATE NULL,
        expected_row_count INT NULL,

        started_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_load_batch_started_at
            DEFAULT (SYSUTCDATETIME()),
        finished_at DATETIME2(3) NULL,

        status VARCHAR(20) NOT NULL,
        rows_read INT NOT NULL
            CONSTRAINT DF_load_batch_rows_read DEFAULT (0),
        rows_loaded INT NOT NULL
            CONSTRAINT DF_load_batch_rows_loaded DEFAULT (0),
        rows_rejected INT NOT NULL
            CONSTRAINT DF_load_batch_rows_rejected DEFAULT (0),

        error_message NVARCHAR(MAX) NULL,

        CONSTRAINT PK_load_batch
            PRIMARY KEY (load_batch_id),

        CONSTRAINT CK_load_batch_batch_type
            CHECK (batch_type IN ('FULL_LOAD', 'INCREMENTAL')),
        CONSTRAINT CK_load_batch_status
            CHECK (status IN ('STARTED', 'SUCCEEDED', 'FAILED')),
        CONSTRAINT CK_load_batch_checksum
            CHECK (
                source_file_checksum COLLATE Latin1_General_100_BIN2
                    NOT LIKE '%[^0-9A-Fa-f]%'
            ),
        CONSTRAINT CK_load_batch_expected_dates
            CHECK (
                (expected_date_from IS NULL AND expected_date_to IS NULL)
                OR
                (
                    expected_date_from IS NOT NULL
                    AND expected_date_to IS NOT NULL
                    AND expected_date_from <= expected_date_to
                )
            ),
        CONSTRAINT CK_load_batch_expected_row_count
            CHECK (expected_row_count IS NULL OR expected_row_count >= 0),
        CONSTRAINT CK_load_batch_row_counts
            CHECK (
                rows_read >= 0
                AND rows_loaded >= 0
                AND rows_rejected >= 0
            ),
        CONSTRAINT CK_load_batch_finished_at
            CHECK (finished_at IS NULL OR finished_at >= started_at)
    );

    PRINT N'Đã tạo audit.load_batch.';
END
ELSE
BEGIN
    PRINT N'Bảng audit.load_batch đã tồn tại.';
END;
GO

/* ========================================================================== */
/* 4. staging/01_create_raw_amazon_delivery.sql                               */
/* ========================================================================== */

USE AmazonDeliveryBI;
GO

IF OBJECT_ID(
    N'staging.raw_amazon_delivery',
    N'U'
) IS NULL
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

        CONSTRAINT PK_raw_amazon_delivery
            PRIMARY KEY (staging_row_id),
        CONSTRAINT FK_raw_amazon_delivery_load_batch
            FOREIGN KEY (load_batch_id)
            REFERENCES audit.load_batch (load_batch_id)
    );

    PRINT N'Đã tạo staging.raw_amazon_delivery.';
END
ELSE
BEGIN
    PRINT N'Bảng staging.raw_amazon_delivery đã tồn tại.';
END;
GO

/* ========================================================================== */
/* 5. validation/01_validate_sql_skeleton.sql                                 */
/* ========================================================================== */

USE AmazonDeliveryBI;
GO

SELECT
    name AS schema_name
FROM sys.schemas
WHERE name IN (N'staging', N'dw', N'audit')
ORDER BY name;
GO

SELECT
    SCHEMA_NAME(schema_id) AS schema_name,
    name AS table_name
FROM sys.tables
WHERE
    (
        SCHEMA_NAME(schema_id) = N'staging'
        AND name = N'raw_amazon_delivery'
    )
    OR
    (
        SCHEMA_NAME(schema_id) = N'audit'
        AND name = N'load_batch'
    )
ORDER BY schema_name, table_name;
GO

SELECT
    c.column_id,
    c.name AS column_name,
    TYPE_NAME(c.user_type_id) AS data_type,
    c.max_length,
    c.is_nullable
FROM sys.columns AS c
WHERE c.object_id =
    OBJECT_ID(N'staging.raw_amazon_delivery')
ORDER BY c.column_id;
GO

SELECT
    COUNT_BIG(*) AS staging_row_count
FROM staging.raw_amazon_delivery;
GO

SELECT
    COUNT_BIG(*) AS audit_batch_count
FROM audit.load_batch;
GO
