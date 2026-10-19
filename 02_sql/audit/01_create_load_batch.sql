/*
Purpose:
    Theo dõi mỗi lần Mage.ai chạy Full Load hoặc Incremental Load.

Note:
    Watermark, idempotency và rejected-record design chi tiết
    vẫn thuộc LOAD-01. Bảng này chỉ là skeleton tối thiểu.
*/

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
