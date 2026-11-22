:ON ERROR EXIT
/* Monitoring-only identity. No credentials returned/persisted; SQL login remains
   DISABLED. Approved Windows bootstrap may explicitly impersonate per connection.
   Does not grant business data access, impersonation rights to other logins,
   change authentication mode, or enable password-based network logins. */
USE AmazonDeliveryBI;
IF CONVERT(nvarchar(128),SERVERPROPERTY('ServerName'))<>N'DESKTOP-OBDFK6B\SQLEXPRESS'
 OR N'$(DeploymentApproval)'<>N'APPROVED_PRIMARY'
 OR NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=0
    AND name='ETLMonitoring.Environment' AND CONVERT(nvarchar(128),value)='APPROVED_PRIMARY')
 THROW 51000,'Approved deployed PRIMARY required',1;
IF SUSER_ID('AmazonDeliveryBI_Monitoring_Runtime') IS NULL
BEGIN
 DECLARE @secret nvarchar(128)=N'Mon!7a'+CONVERT(nvarchar(64),CRYPT_GEN_RANDOM(32),2);
 DECLARE @ddl nvarchar(max)=N'CREATE LOGIN [AmazonDeliveryBI_Monitoring_Runtime] WITH PASSWORD='
  +QUOTENAME(@secret,'''')+N', CHECK_POLICY=ON, DEFAULT_DATABASE=[AmazonDeliveryBI];';
 EXEC sys.sp_executesql @ddl;
 ALTER LOGIN [AmazonDeliveryBI_Monitoring_Runtime] DISABLE;
END;
IF NOT EXISTS(SELECT 1 FROM sys.server_principals WHERE name='AmazonDeliveryBI_Monitoring_Runtime'
 AND type='S' AND is_disabled=1)
 THROW 51000,'Existing principal is not the expected disabled SQL identity; no automatic repair',1;
IF IS_SRVROLEMEMBER('sysadmin','AmazonDeliveryBI_Monitoring_Runtime')<>0
 THROW 51000,'Monitoring identity must not be sysadmin',1;
IF USER_ID('AmazonDeliveryBI_Monitoring_Runtime') IS NULL
 CREATE USER [AmazonDeliveryBI_Monitoring_Runtime] FOR LOGIN [AmazonDeliveryBI_Monitoring_Runtime];
IF EXISTS(SELECT 1 FROM sys.database_principals WHERE name='AmazonDeliveryBI_Monitoring_Runtime'
 AND sid<>SUSER_SID('AmazonDeliveryBI_Monitoring_Runtime'))
 THROW 51000,'Existing user SID mismatch',1;
IF NOT EXISTS(SELECT 1 FROM sys.database_role_members rm
 WHERE rm.role_principal_id=DATABASE_PRINCIPAL_ID('etl_monitoring_writer')
 AND rm.member_principal_id=USER_ID('AmazonDeliveryBI_Monitoring_Runtime'))
 ALTER ROLE etl_monitoring_writer ADD MEMBER [AmazonDeliveryBI_Monitoring_Runtime];
GO
