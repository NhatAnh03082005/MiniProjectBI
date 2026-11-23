/* MANUAL VIDEO PREPARATION ONLY — not called by any pipeline.
   Deletes ALL data/objects of AmazonDeliveryBI on the named local instance.
   Disable all Mage triggers, stop Mage/AI and close BI connections first.
   Then run sql/run_sql_skeleton.sql separately to rebuild the structure.
   Does not delete AmazonDeliveryBI_Demo or Mage's own trigger/run history. */
USE master;
GO
IF UPPER(CONVERT(nvarchar(128), SERVERPROPERTY('ServerName'))) <> N'NHAT-ANH\SQLEXPRESS'
    THROW 51000, 'Wrong server; database reset refused.', 1;

IF DB_ID(N'AmazonDeliveryBI') IS NOT NULL
BEGIN
    ALTER DATABASE [AmazonDeliveryBI] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE [AmazonDeliveryBI];
END;
PRINT N'AmazonDeliveryBI removed. Run sql/run_sql_skeleton.sql to create structure.';
