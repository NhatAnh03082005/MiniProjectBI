/*
Purpose:
    Tạo database dùng chung cho project Amazon Delivery BI.

Owner:
    Trưởng nhóm - Technical Scaffold.

Safety:
    Chỉ tạo database khi chưa tồn tại.
    Không xóa hoặc ghi đè database hiện có.
*/

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