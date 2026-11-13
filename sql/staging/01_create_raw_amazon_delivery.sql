/*
Purpose:
    Tạo hoặc nâng cấp bảng current-state raw Amazon Delivery.

Contract:
    - Một dòng hiện hành cho một Order_ID.
    - 16 giá trị nguồn được giữ nguyên; dbt tiếp tục chuẩn hóa phía sau.
    - load_batch_id/loaded_at là lineage lần tạo đầu tiên.
    - updated_* là lineage lần thay đổi gần nhất.
    - File nguồn được giữ trong data/raw/archive để replay khi cần.
*/

USE AmazonDeliveryBI;
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
        CONSTRAINT FK_raw_amazon_delivery_load_batch
            FOREIGN KEY (load_batch_id)
            REFERENCES audit.load_batch (load_batch_id),
        CONSTRAINT FK_raw_amazon_delivery_updated_load_batch
            FOREIGN KEY (updated_load_batch_id)
            REFERENCES audit.load_batch (load_batch_id)
    );
END;
GO

IF COL_LENGTH(N'staging.raw_amazon_delivery', N'row_hash') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD row_hash CHAR(64) NULL;
GO

IF COL_LENGTH(N'staging.raw_amazon_delivery', N'updated_load_batch_id') IS NULL
    ALTER TABLE staging.raw_amazon_delivery
    ADD updated_load_batch_id VARCHAR(64) NULL;
GO

IF COL_LENGTH(N'staging.raw_amazon_delivery', N'updated_at') IS NULL
    ALTER TABLE staging.raw_amazon_delivery ADD updated_at DATETIME2(3) NULL;
GO

IF COL_LENGTH(N'staging.raw_amazon_delivery', N'updated_source_file_name') IS NULL
    ALTER TABLE staging.raw_amazon_delivery
    ADD updated_source_file_name NVARCHAR(260) NULL;
GO

IF COL_LENGTH(N'staging.raw_amazon_delivery', N'updated_source_row_number') IS NULL
    ALTER TABLE staging.raw_amazon_delivery
    ADD updated_source_row_number BIGINT NULL;
GO

UPDATE staging.raw_amazon_delivery
SET updated_load_batch_id = COALESCE(updated_load_batch_id, load_batch_id),
    updated_at = COALESCE(updated_at, loaded_at),
    updated_source_file_name = COALESCE(updated_source_file_name, source_file_name),
    updated_source_row_number = COALESCE(updated_source_row_number, source_row_number)
WHERE updated_load_batch_id IS NULL
   OR updated_at IS NULL
   OR updated_source_file_name IS NULL
   OR updated_source_row_number IS NULL;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.foreign_keys
    WHERE parent_object_id = OBJECT_ID(N'staging.raw_amazon_delivery')
      AND name = N'FK_raw_amazon_delivery_updated_load_batch'
)
    ALTER TABLE staging.raw_amazon_delivery WITH CHECK
    ADD CONSTRAINT FK_raw_amazon_delivery_updated_load_batch
        FOREIGN KEY (updated_load_batch_id)
        REFERENCES audit.load_batch (load_batch_id);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'staging.raw_amazon_delivery')
      AND name = N'IX_raw_amazon_delivery_load_batch_id'
)
    CREATE INDEX IX_raw_amazon_delivery_load_batch_id
        ON staging.raw_amazon_delivery (load_batch_id);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'staging.raw_amazon_delivery')
      AND name = N'IX_raw_amazon_delivery_updated_load_batch_id'
)
    CREATE INDEX IX_raw_amazon_delivery_updated_load_batch_id
        ON staging.raw_amazon_delivery (updated_load_batch_id);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'staging.raw_amazon_delivery')
      AND name = N'UX_raw_amazon_delivery_batch_source_row'
)
    CREATE UNIQUE INDEX UX_raw_amazon_delivery_batch_source_row
        ON staging.raw_amazon_delivery (load_batch_id, source_row_number);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'staging.raw_amazon_delivery')
      AND name = N'UX_raw_amazon_delivery_order_id'
)
    CREATE UNIQUE INDEX UX_raw_amazon_delivery_order_id
        ON staging.raw_amazon_delivery (Order_ID)
        WHERE Order_ID IS NOT NULL;
GO

PRINT N'staging.raw_amazon_delivery sẵn sàng cho current-state upsert.';
GO
