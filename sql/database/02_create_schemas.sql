/*
Purpose:
    Tạo các schema chính của project.

Schemas:
    staging - dữ liệu nguồn và dữ liệu chuẩn hóa trung gian.
    dw      - Dimension và Fact do dbt tạo.
    audit   - lịch sử batch, trạng thái và lỗi.

Safety:
    Chỉ tạo schema khi chưa tồn tại.
*/

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