/*
Purpose:
    Tạo hoặc nâng cấp audit batch cho dynamic batch và current-state upsert.

Compatibility:
    Script idempotent; dữ liệu audit hiện có được giữ nguyên.
*/

USE AmazonDeliveryBI;
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

        -- Tên cột legacy được giữ để tương thích; giá trị được suy ra động
        -- từ file hiện tại, không còn là mốc/số dòng gán cứng.
        expected_date_from DATE NULL,
        expected_date_to DATE NULL,
        expected_row_count INT NULL,

        started_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_load_batch_started_at DEFAULT (SYSUTCDATETIME()),
        finished_at DATETIME2(3) NULL,

        status VARCHAR(20) NOT NULL,
        rows_read INT NOT NULL
            CONSTRAINT DF_load_batch_rows_read DEFAULT (0),
        rows_loaded INT NOT NULL
            CONSTRAINT DF_load_batch_rows_loaded DEFAULT (0),
        rows_rejected INT NOT NULL
            CONSTRAINT DF_load_batch_rows_rejected DEFAULT (0),
        rows_inserted INT NOT NULL
            CONSTRAINT DF_load_batch_rows_inserted DEFAULT (0),
        rows_updated INT NOT NULL
            CONSTRAINT DF_load_batch_rows_updated DEFAULT (0),
        rows_unchanged INT NOT NULL
            CONSTRAINT DF_load_batch_rows_unchanged DEFAULT (0),

        error_message NVARCHAR(MAX) NULL,

        CONSTRAINT PK_load_batch PRIMARY KEY (load_batch_id),
        CONSTRAINT CK_load_batch_batch_type
            CHECK (batch_type IN ('FULL_LOAD', 'INCREMENTAL')),
        CONSTRAINT CK_load_batch_batch_name
            CHECK (LEN(LTRIM(RTRIM(batch_name))) > 0),
        CONSTRAINT CK_load_batch_status
            CHECK (status IN ('STARTED', 'SUCCEEDED', 'FAILED', 'SKIPPED')),
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
                rows_read >= 0 AND rows_loaded >= 0 AND rows_rejected >= 0
                AND rows_inserted >= 0 AND rows_updated >= 0
                AND rows_unchanged >= 0
            ),
        CONSTRAINT CK_load_batch_finished_at
            CHECK (finished_at IS NULL OR finished_at >= started_at)
    );
END;
GO

IF COL_LENGTH(N'audit.load_batch', N'rows_inserted') IS NULL
    ALTER TABLE audit.load_batch
    ADD rows_inserted INT NOT NULL
        CONSTRAINT DF_load_batch_rows_inserted DEFAULT (0) WITH VALUES;
GO

IF COL_LENGTH(N'audit.load_batch', N'rows_updated') IS NULL
    ALTER TABLE audit.load_batch
    ADD rows_updated INT NOT NULL
        CONSTRAINT DF_load_batch_rows_updated DEFAULT (0) WITH VALUES;
GO

IF COL_LENGTH(N'audit.load_batch', N'rows_unchanged') IS NULL
    ALTER TABLE audit.load_batch
    ADD rows_unchanged INT NOT NULL
        CONSTRAINT DF_load_batch_rows_unchanged DEFAULT (0) WITH VALUES;
GO

IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'audit.load_batch')
      AND name = N'CK_load_batch_batch_name'
)
    ALTER TABLE audit.load_batch DROP CONSTRAINT CK_load_batch_batch_name;
GO

IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'audit.load_batch')
      AND name = N'CK_load_batch_name_type'
)
    ALTER TABLE audit.load_batch DROP CONSTRAINT CK_load_batch_name_type;
GO

ALTER TABLE audit.load_batch WITH CHECK
ADD CONSTRAINT CK_load_batch_batch_name
    CHECK (LEN(LTRIM(RTRIM(batch_name))) > 0);
GO

IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'audit.load_batch')
      AND name = N'CK_load_batch_row_counts'
)
    ALTER TABLE audit.load_batch DROP CONSTRAINT CK_load_batch_row_counts;
GO

ALTER TABLE audit.load_batch WITH CHECK
ADD CONSTRAINT CK_load_batch_row_counts
    CHECK (
        rows_read >= 0 AND rows_loaded >= 0 AND rows_rejected >= 0
        AND rows_inserted >= 0 AND rows_updated >= 0
        AND rows_unchanged >= 0
    );
GO

IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'audit.load_batch')
      AND name = N'IX_load_batch_batch_name_status'
)
    DROP INDEX IX_load_batch_batch_name_status ON audit.load_batch;
GO

CREATE INDEX IX_load_batch_batch_name_status
    ON audit.load_batch (batch_name, status)
    INCLUDE (
        source_file_checksum,
        expected_date_from,
        expected_date_to,
        expected_row_count,
        rows_read,
        rows_loaded,
        rows_inserted,
        rows_updated,
        rows_unchanged,
        finished_at
    );
GO

PRINT N'audit.load_batch sẵn sàng cho dynamic batch và upsert.';
GO
