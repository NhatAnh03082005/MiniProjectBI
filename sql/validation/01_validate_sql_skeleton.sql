/*
Purpose:
    Kiểm tra database, schema và bảng skeleton.

Expected:
    - Có database AmazonDeliveryBI.
    - Có ba schema staging, dw, audit.
    - Có staging.raw_amazon_delivery.
    - Có audit.load_batch.
    - Raw table hiện có thể bằng 0 dòng vì chưa chạy Mage.
*/

USE AmazonDeliveryBI;
GO

-- 1. Kiểm tra schema
SELECT
    name AS schema_name
FROM sys.schemas
WHERE name IN (N'staging', N'dw', N'audit')
ORDER BY name;
GO

-- 2. Kiểm tra hai bảng skeleton
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

-- 3. Kiểm tra cấu trúc raw staging
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

-- 4. Đếm dòng hiện tại
SELECT
    COUNT_BIG(*) AS staging_row_count
FROM staging.raw_amazon_delivery;
GO

SELECT
    COUNT_BIG(*) AS audit_batch_count
FROM audit.load_batch;
GO