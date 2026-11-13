/*
Purpose:
    Xác nhận schema hỗ trợ dynamic batch, raw row hash và action counters.
*/

USE AmazonDeliveryBI;
GO

IF OBJECT_ID(N'audit.load_batch', N'U') IS NULL
    THROW 51000, 'Thiếu audit.load_batch.', 1;
IF OBJECT_ID(N'staging.raw_amazon_delivery', N'U') IS NULL
    THROW 51000, 'Thiếu staging.raw_amazon_delivery.', 1;
GO

IF EXISTS (
    SELECT required.name
    FROM (VALUES
        (N'rows_inserted'), (N'rows_updated'), (N'rows_unchanged')
    ) AS required(name)
    WHERE COL_LENGTH(N'audit.load_batch', required.name) IS NULL
)
    THROW 51000, 'audit.load_batch thiếu action counter.', 1;
GO

IF EXISTS (
    SELECT required.name
    FROM (VALUES
        (N'row_hash'), (N'updated_load_batch_id'), (N'updated_at'),
        (N'updated_source_file_name'), (N'updated_source_row_number')
    ) AS required(name)
    WHERE COL_LENGTH(N'staging.raw_amazon_delivery', required.name) IS NULL
)
    THROW 51000, 'staging.raw_amazon_delivery thiếu upsert metadata.', 1;
GO

IF EXISTS (
    SELECT 1
    FROM audit.load_batch
    WHERE status = 'SUCCEEDED'
      AND rows_read <> rows_inserted + rows_updated + rows_unchanged + rows_rejected
      AND batch_name LIKE 'amazon_delivery_%'
)
    THROW 51000, 'Có dynamic batch không đối soát được action counter.', 1;
GO

IF EXISTS (
    SELECT LOWER(LTRIM(RTRIM(Order_ID)))
    FROM staging.raw_amazon_delivery
    WHERE Order_ID IS NOT NULL
    GROUP BY LOWER(LTRIM(RTRIM(Order_ID)))
    HAVING COUNT_BIG(*) > 1
)
    THROW 51000, 'Staging có Order_ID trùng sau trim/case-fold.', 1;
GO

SELECT
    (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery) AS staging_rows,
    (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery
     WHERE row_hash IS NOT NULL) AS rows_with_hash,
    (SELECT COUNT_BIG(*) FROM audit.load_batch) AS audit_batches,
    (SELECT COUNT_BIG(*) FROM audit.load_batch
     WHERE batch_name LIKE 'amazon_delivery_%') AS dynamic_batches;
GO

PRINT N'Validation SQL skeleton thành công.';
GO
