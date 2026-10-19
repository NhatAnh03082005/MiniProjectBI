/*
Purpose:
    Tạo bảng tiếp nhận nguyên trạng Amazon Delivery Dataset.

Important:
    - Không làm sạch tại bảng này.
    - Không trim.
    - Không sửa Metropolitian.
    - Không chuẩn hóa NaN thành NULL.
    - Không đổi dấu tọa độ.
    - Không loại outlier.
    - Phải tạo audit.load_batch trước bảng này.
    - Mage.ai chịu trách nhiệm ghi vào bảng này.
*/

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

        -- Metadata ingestion
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
