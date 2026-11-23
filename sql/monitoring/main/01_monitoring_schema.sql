/* Main database, explicitly selected by the project owner. Run in SSMS. Creates monitoring objects; no business data reset. */
USE AmazonDeliveryBI;
GO
IF DB_NAME() <> 'AmazonDeliveryBI' THROW 51000,'Main database target required',1;
SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS ON; SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON; SET ARITHABORT ON; SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF; SET XACT_ABORT ON;
GO
IF SCHEMA_ID('monitoring') IS NULL EXEC('CREATE SCHEMA monitoring AUTHORIZATION dbo');
BEGIN TRY
 BEGIN TRAN;
IF OBJECT_ID('monitoring.etl_runs') IS NOT NULL AND OBJECT_ID('monitoring.etl_runs','U') IS NULL THROW 51000,'Unexpected object type',1;
IF OBJECT_ID('monitoring.etl_runs','U') IS NULL
BEGIN
CREATE TABLE monitoring.etl_runs (
    execution_key uniqueidentifier NOT NULL DEFAULT NEWID() PRIMARY KEY,
    run_id uniqueidentifier NOT NULL,
    attempt_id int NOT NULL CHECK (attempt_id > 0),
    pipeline_name nvarchar(128) NOT NULL,
    batch_type varchar(20) NOT NULL CHECK (batch_type IN ('FULL_LOAD','INCREMENTAL','DBT_ONLY')),
    execution_kind varchar(16) NOT NULL DEFAULT 'MAGE_DBT' CHECK(execution_kind IN ('MAGE_DBT','DBT_ONLY')),
    source_file nvarchar(260) NULL,
    source_checksum char(64) NULL,
    legacy_load_batch_id varchar(64) NULL,
    mage_pipeline_run_id nvarchar(128) NULL,
    evidence_kind varchar(8) NOT NULL CHECK(evidence_kind IN ('REAL','TEST')),
    status varchar(20) NOT NULL CHECK (status IN
       ('STARTED','WAITING_DBT','IN_DOUBT','SUCCEEDED','FAILED','CANCELLED','SKIPPED','ABANDONED')),
    start_time datetime2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    end_time datetime2(3) NULL,
    heartbeat_at datetime2(3) NULL,
    metric_definition_version varchar(32) NOT NULL,
    CONSTRAINT UQ_etl_runs_attempt UNIQUE(run_id,attempt_id),
    CHECK ((status IN ('STARTED','WAITING_DBT','IN_DOUBT') AND end_time IS NULL) OR
           (status NOT IN ('STARTED','WAITING_DBT','IN_DOUBT') AND end_time IS NOT NULL)),
    CHECK (end_time IS NULL OR end_time>=start_time)
);
END;
IF OBJECT_ID('monitoring.etl_step_runs') IS NOT NULL AND OBJECT_ID('monitoring.etl_step_runs','U') IS NULL THROW 51000,'Unexpected object type',1;
IF OBJECT_ID('monitoring.etl_step_runs','U') IS NULL
BEGIN
CREATE TABLE monitoring.etl_step_runs (
    execution_key uniqueidentifier NOT NULL REFERENCES monitoring.etl_runs(execution_key),
    step_key varchar(128) NOT NULL,
    step_attempt int NOT NULL CHECK (step_attempt>0),
    component varchar(20) NOT NULL CHECK(component IN ('SOURCE','MAGE','DBT','WAREHOUSE')),
    external_execution_id nvarchar(512) NULL,
    dbt_invocation_id uniqueidentifier NULL,
    native_duration_seconds decimal(20,6) NULL,
    native_failures bigint NULL,
    native_status varchar(32) NULL,
    resource_type varchar(32) NULL,
    artifact_sha256 char(64) NULL,
    dbt_command varchar(32) NULL,
    process_exit_code int NULL,
    artifact_verified bit NOT NULL DEFAULT (0),
    artifact_path nvarchar(1024) NULL,
    status varchar(20) NOT NULL CHECK(status IN
       ('NOT_STARTED','STARTED','IN_DOUBT','SUCCEEDED','FAILED','CANCELLED','SKIPPED','ABANDONED')),
    start_time datetime2(3) NULL,
    end_time datetime2(3) NULL,
    PRIMARY KEY(execution_key,step_key,step_attempt),
    CHECK (end_time IS NULL OR (start_time IS NOT NULL AND end_time>=start_time)),
    CHECK (status NOT IN ('STARTED','WAITING_DBT','IN_DOUBT') OR (start_time IS NOT NULL AND end_time IS NULL)),
    CHECK (status<>'NOT_STARTED' OR (start_time IS NULL AND end_time IS NULL)),
    CHECK (status NOT IN ('CANCELLED','SKIPPED') OR
       (start_time IS NULL AND end_time IS NULL) OR
       (start_time IS NOT NULL AND end_time IS NOT NULL)),
    CHECK (status NOT IN ('SUCCEEDED','FAILED','ABANDONED') OR
           (start_time IS NOT NULL AND end_time IS NOT NULL) OR
           (status='FAILED' AND start_time IS NULL AND end_time IS NULL)),
    CHECK (step_key NOT IN ('source','mage','dbt','warehouse') OR
       (step_key='source' AND component='SOURCE') OR
       (step_key='mage' AND component='MAGE') OR
       (step_key='dbt' AND component='DBT') OR
       (step_key='warehouse' AND component='WAREHOUSE')),
    CHECK (artifact_verified=0 OR
       (component='DBT' AND dbt_invocation_id IS NOT NULL AND artifact_path IS NOT NULL))
);
END;
IF OBJECT_ID('monitoring.etl_record_metrics') IS NOT NULL AND OBJECT_ID('monitoring.etl_record_metrics','U') IS NULL THROW 51000,'Unexpected object type',1;
IF OBJECT_ID('monitoring.etl_record_metrics','U') IS NULL
BEGIN
CREATE TABLE monitoring.etl_record_metrics (
    execution_key uniqueidentifier NOT NULL,
    step_key varchar(128) NOT NULL,
    step_attempt int NOT NULL,
    metric_scope varchar(64) NOT NULL,
    entity_name nvarchar(128) NOT NULL,
    measurement_state varchar(16) NOT NULL CHECK(measurement_state IN ('OBSERVED','COMMITTED')),
    records_read bigint NULL CHECK(records_read>=0),
    records_valid bigint NULL CHECK(records_valid>=0),
    records_inserted bigint NULL CHECK(records_inserted>=0),
    records_updated bigint NULL CHECK(records_updated>=0),
    records_unchanged bigint NULL CHECK(records_unchanged>=0),
    records_rejected bigint NULL CHECK(records_rejected>=0),
    records_written bigint NULL CHECK(records_written>=0),
    captured_at datetime2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    PRIMARY KEY(execution_key,step_key,step_attempt,metric_scope,entity_name),
    FOREIGN KEY(execution_key,step_key,step_attempt)
       REFERENCES monitoring.etl_step_runs(execution_key,step_key,step_attempt),
    CHECK (measurement_state='COMMITTED' OR
       (records_inserted IS NULL AND records_updated IS NULL
        AND records_unchanged IS NULL AND records_written IS NULL))
);
END;
IF OBJECT_ID('monitoring.etl_errors') IS NOT NULL AND OBJECT_ID('monitoring.etl_errors','U') IS NULL THROW 51000,'Unexpected object type',1;
IF OBJECT_ID('monitoring.etl_errors','U') IS NULL
BEGIN
CREATE TABLE monitoring.etl_errors (
    error_id bigint IDENTITY PRIMARY KEY,
    execution_key uniqueidentifier NOT NULL REFERENCES monitoring.etl_runs(execution_key),
    step_key varchar(128) NULL,
    step_attempt int NULL,
    severity varchar(10) NOT NULL CHECK(severity IN ('ERROR','WARNING','INFO')),
    error_code nvarchar(128) NULL,
    message nvarchar(max) NOT NULL,
    occurred_at datetime2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    CHECK ((step_key IS NULL AND step_attempt IS NULL) OR
           (step_key IS NOT NULL AND step_attempt IS NOT NULL)),
    FOREIGN KEY(execution_key,step_key,step_attempt)
       REFERENCES monitoring.etl_step_runs(execution_key,step_key,step_attempt)
);
END;
IF COL_LENGTH('monitoring.etl_errors','event_key') IS NULL
 ALTER TABLE monitoring.etl_errors ADD event_key uniqueidentifier NULL;
IF EXISTS(SELECT 1 FROM (VALUES
('etl_errors','error_id','bigint',8,19,0,0,1),
('etl_errors','execution_key','uniqueidentifier',16,0,0,0,0),
('etl_errors','step_key','varchar',128,0,0,1,0),
('etl_errors','step_attempt','int',4,10,0,1,0),
('etl_errors','severity','varchar',10,0,0,0,0),
('etl_errors','error_code','nvarchar',256,0,0,1,0),
('etl_errors','message','nvarchar',-1,0,0,0,0),
('etl_errors','occurred_at','datetime2',7,23,3,0,0),
('etl_record_metrics','execution_key','uniqueidentifier',16,0,0,0,0),
('etl_record_metrics','step_key','varchar',128,0,0,0,0),
('etl_record_metrics','step_attempt','int',4,10,0,0,0),
('etl_record_metrics','metric_scope','varchar',64,0,0,0,0),
('etl_record_metrics','entity_name','nvarchar',256,0,0,0,0),
('etl_record_metrics','measurement_state','varchar',16,0,0,0,0),
('etl_record_metrics','records_read','bigint',8,19,0,1,0),
('etl_record_metrics','records_valid','bigint',8,19,0,1,0),
('etl_record_metrics','records_inserted','bigint',8,19,0,1,0),
('etl_record_metrics','records_updated','bigint',8,19,0,1,0),
('etl_record_metrics','records_unchanged','bigint',8,19,0,1,0),
('etl_record_metrics','records_rejected','bigint',8,19,0,1,0),
('etl_record_metrics','records_written','bigint',8,19,0,1,0),
('etl_record_metrics','captured_at','datetime2',7,23,3,0,0),
('etl_runs','execution_key','uniqueidentifier',16,0,0,0,0),
('etl_runs','run_id','uniqueidentifier',16,0,0,0,0),
('etl_runs','attempt_id','int',4,10,0,0,0),
('etl_runs','pipeline_name','nvarchar',256,0,0,0,0),
('etl_runs','batch_type','varchar',20,0,0,0,0),
('etl_runs','execution_kind','varchar',16,0,0,0,0),
('etl_runs','source_file','nvarchar',520,0,0,1,0),
('etl_runs','source_checksum','char',64,0,0,1,0),
('etl_runs','legacy_load_batch_id','varchar',64,0,0,1,0),
('etl_runs','mage_pipeline_run_id','nvarchar',256,0,0,1,0),
('etl_runs','evidence_kind','varchar',8,0,0,0,0),
('etl_runs','status','varchar',20,0,0,0,0),
('etl_runs','start_time','datetime2',7,23,3,0,0),
('etl_runs','end_time','datetime2',7,23,3,1,0),
('etl_runs','heartbeat_at','datetime2',7,23,3,1,0),
('etl_runs','metric_definition_version','varchar',32,0,0,0,0),
('etl_step_runs','execution_key','uniqueidentifier',16,0,0,0,0),
('etl_step_runs','step_key','varchar',128,0,0,0,0),
('etl_step_runs','step_attempt','int',4,10,0,0,0),
('etl_step_runs','component','varchar',20,0,0,0,0),
('etl_step_runs','external_execution_id','nvarchar',1024,0,0,1,0),
('etl_step_runs','dbt_invocation_id','uniqueidentifier',16,0,0,1,0),
('etl_step_runs','native_status','varchar',32,0,0,1,0),
('etl_step_runs','resource_type','varchar',32,0,0,1,0),
('etl_step_runs','artifact_sha256','char',64,0,0,1,0),
('etl_step_runs','dbt_command','varchar',32,0,0,1,0),
('etl_step_runs','process_exit_code','int',4,10,0,1,0),
('etl_step_runs','artifact_verified','bit',1,1,0,0,0),
('etl_step_runs','artifact_path','nvarchar',2048,0,0,1,0),
('etl_step_runs','status','varchar',20,0,0,0,0),
('etl_step_runs','start_time','datetime2',7,23,3,1,0),
('etl_step_runs','end_time','datetime2',7,23,3,1,0),
('etl_step_runs','native_duration_seconds','decimal',13,20,6,1,0),
('etl_step_runs','native_failures','bigint',8,19,0,1,0),
('etl_errors','event_key','uniqueidentifier',16,0,0,1,0)
) expected(tbl,col,typ,len,prec,scale,nullable,identity_col)
 LEFT JOIN sys.columns c ON c.object_id=OBJECT_ID('monitoring.'+expected.tbl) AND c.name=expected.col
 WHERE c.column_id IS NULL OR TYPE_NAME(c.user_type_id)<>expected.typ
 OR c.max_length<>expected.len OR c.precision<>expected.prec OR c.scale<>expected.scale
 OR c.is_nullable<>expected.nullable OR c.is_identity<>expected.identity_col)
 THROW 51000,'Existing monitoring column contract mismatch; no automatic repair',1;
IF ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.key_constraints k JOIN sys.index_columns ic ON ic.object_id=k.parent_object_id AND ic.index_id=k.unique_index_id
 JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE k.parent_object_id=OBJECT_ID('monitoring.etl_runs') AND k.type='PK'),'')<>'execution_key'
 THROW 51000,'Monitoring PK grain mismatch: etl_runs',1;
IF ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.key_constraints k JOIN sys.index_columns ic ON ic.object_id=k.parent_object_id AND ic.index_id=k.unique_index_id
 JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE k.parent_object_id=OBJECT_ID('monitoring.etl_step_runs') AND k.type='PK'),'')<>'execution_key,step_key,step_attempt'
 THROW 51000,'Monitoring PK grain mismatch: etl_step_runs',1;
IF ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.key_constraints k JOIN sys.index_columns ic ON ic.object_id=k.parent_object_id AND ic.index_id=k.unique_index_id
 JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE k.parent_object_id=OBJECT_ID('monitoring.etl_record_metrics') AND k.type='PK'),'')<>'execution_key,step_key,step_attempt,metric_scope,entity_name'
 THROW 51000,'Monitoring PK grain mismatch: etl_record_metrics',1;
IF ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.key_constraints k JOIN sys.index_columns ic ON ic.object_id=k.parent_object_id AND ic.index_id=k.unique_index_id
 JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE k.parent_object_id=OBJECT_ID('monitoring.etl_errors') AND k.type='PK'),'')<>'error_id'
 THROW 51000,'Monitoring PK grain mismatch: etl_errors',1;
IF EXISTS(SELECT * FROM (VALUES
('etl_errors','execution_key','monitoring','etl_runs','execution_key',1),
('etl_errors','execution_key','monitoring','etl_step_runs','execution_key',1),
('etl_errors','step_key','monitoring','etl_step_runs','step_key',2),
('etl_errors','step_attempt','monitoring','etl_step_runs','step_attempt',3),
('etl_record_metrics','execution_key','monitoring','etl_step_runs','execution_key',1),
('etl_record_metrics','step_key','monitoring','etl_step_runs','step_key',2),
('etl_record_metrics','step_attempt','monitoring','etl_step_runs','step_attempt',3),
('etl_step_runs','execution_key','monitoring','etl_runs','execution_key',1)
) e(tbl,col,ref_schema,ref_tbl,ref_col,ordinal)
 EXCEPT SELECT t.name,c.name,rs.name,rt.name,rc.name,fc.constraint_column_id
 FROM sys.foreign_keys f JOIN sys.tables t ON t.object_id=f.parent_object_id
 JOIN sys.foreign_key_columns fc ON fc.constraint_object_id=f.object_id
 JOIN sys.columns c ON c.object_id=fc.parent_object_id AND c.column_id=fc.parent_column_id
 JOIN sys.tables rt ON rt.object_id=fc.referenced_object_id JOIN sys.schemas rs ON rs.schema_id=rt.schema_id
 JOIN sys.columns rc ON rc.object_id=fc.referenced_object_id AND rc.column_id=fc.referenced_column_id
 WHERE t.schema_id=SCHEMA_ID('monitoring')) THROW 51000,'Monitoring FK endpoint mismatch',1;
IF EXISTS(SELECT * FROM (VALUES
('etl_errors','(severity=''info''orseverity=''warning''orseverity=''error'')'),
('etl_errors','(step_keyisnullandstep_attemptisnullorstep_keyisnotnullandstep_attemptisnotnull)'),
('etl_record_metrics','(measurement_state=''committed''ormeasurement_state=''observed'')'),
('etl_record_metrics','(records_read>=(0))'),
('etl_record_metrics','(records_valid>=(0))'),
('etl_record_metrics','(records_inserted>=(0))'),
('etl_record_metrics','(records_updated>=(0))'),
('etl_record_metrics','(records_unchanged>=(0))'),
('etl_record_metrics','(records_rejected>=(0))'),
('etl_record_metrics','(records_written>=(0))'),
('etl_record_metrics','(measurement_state=''committed''orrecords_insertedisnullandrecords_updatedisnullandrecords_unchangedisnullandrecords_writtenisnull)'),
('etl_runs','((status=''in_doubt''orstatus=''waiting_dbt''orstatus=''started'')andend_timeisnullornot(status=''in_doubt''orstatus=''waiting_dbt''orstatus=''started'')andend_timeisnotnull)'),
('etl_runs','(end_timeisnullorend_time>=start_time)'),
('etl_runs','(attempt_id>(0))'),
('etl_runs','(batch_type=''dbt_only''orbatch_type=''incremental''orbatch_type=''full_load'')'),
('etl_runs','(evidence_kind=''test''orevidence_kind=''real'')'),
('etl_runs','(execution_kind=''dbt_only''orexecution_kind=''mage_dbt'')'),
('etl_runs','(status=''abandoned''orstatus=''skipped''orstatus=''cancelled''orstatus=''failed''orstatus=''succeeded''orstatus=''in_doubt''orstatus=''waiting_dbt''orstatus=''started'')'),
('etl_step_runs','(component=''warehouse''orcomponent=''dbt''orcomponent=''mage''orcomponent=''source'')'),
('etl_step_runs','(status=''abandoned''orstatus=''skipped''orstatus=''cancelled''orstatus=''failed''orstatus=''succeeded''orstatus=''in_doubt''orstatus=''started''orstatus=''not_started'')'),
('etl_step_runs','(step_attempt>(0))'),
('etl_step_runs','(end_timeisnullorstart_timeisnotnullandend_time>=start_time)'),
('etl_step_runs','(not(status=''in_doubt''orstatus=''waiting_dbt''orstatus=''started'')orstart_timeisnotnullandend_timeisnull)'),
('etl_step_runs','(status<>''not_started''orstart_timeisnullandend_timeisnull)'),
('etl_step_runs','(not(status=''skipped''orstatus=''cancelled'')orstart_timeisnullandend_timeisnullorstart_timeisnotnullandend_timeisnotnull)'),
('etl_step_runs','(not(step_key=''warehouse''orstep_key=''dbt''orstep_key=''mage''orstep_key=''source'')orstep_key=''source''andcomponent=''source''orstep_key=''mage''andcomponent=''mage''orstep_key=''dbt''andcomponent=''dbt''orstep_key=''warehouse''andcomponent=''warehouse'')'),
('etl_step_runs','(artifact_verified=(0)orcomponent=''dbt''anddbt_invocation_idisnotnullandartifact_pathisnotnull)'),
('etl_step_runs','(not(status=''abandoned''orstatus=''failed''orstatus=''succeeded'')orstart_timeisnotnullandend_timeisnotnullorstatus=''failed''andstart_timeisnullandend_timeisnull)')
) e(tbl,definition)
 EXCEPT SELECT t.name,LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(cc.definition,'[',''),']',''),' ',''),CHAR(13),''),CHAR(10),''),CHAR(9),''))
 FROM sys.check_constraints cc JOIN sys.tables t ON t.object_id=cc.parent_object_id
 WHERE t.schema_id=SCHEMA_ID('monitoring')) THROW 51000,'Monitoring CHECK contract mismatch',1;
IF EXISTS(SELECT * FROM (VALUES
('etl_errors','error_id',''),
('etl_errors','execution_key',''),
('etl_errors','step_key',''),
('etl_errors','step_attempt',''),
('etl_errors','severity',''),
('etl_errors','error_code',''),
('etl_errors','message',''),
('etl_errors','occurred_at','(sysutcdatetime())'),
('etl_record_metrics','execution_key',''),
('etl_record_metrics','step_key',''),
('etl_record_metrics','step_attempt',''),
('etl_record_metrics','metric_scope',''),
('etl_record_metrics','entity_name',''),
('etl_record_metrics','measurement_state',''),
('etl_record_metrics','records_read',''),
('etl_record_metrics','records_valid',''),
('etl_record_metrics','records_inserted',''),
('etl_record_metrics','records_updated',''),
('etl_record_metrics','records_unchanged',''),
('etl_record_metrics','records_rejected',''),
('etl_record_metrics','records_written',''),
('etl_record_metrics','captured_at','(sysutcdatetime())'),
('etl_runs','execution_key','(newid())'),
('etl_runs','run_id',''),
('etl_runs','attempt_id',''),
('etl_runs','pipeline_name',''),
('etl_runs','batch_type',''),
('etl_runs','execution_kind','(''mage_dbt'')'),
('etl_runs','source_file',''),
('etl_runs','source_checksum',''),
('etl_runs','legacy_load_batch_id',''),
('etl_runs','mage_pipeline_run_id',''),
('etl_runs','evidence_kind',''),
('etl_runs','status',''),
('etl_runs','start_time','(sysutcdatetime())'),
('etl_runs','end_time',''),
('etl_runs','heartbeat_at',''),
('etl_runs','metric_definition_version',''),
('etl_step_runs','execution_key',''),
('etl_step_runs','step_key',''),
('etl_step_runs','step_attempt',''),
('etl_step_runs','component',''),
('etl_step_runs','external_execution_id',''),
('etl_step_runs','dbt_invocation_id',''),
('etl_step_runs','native_status',''),
('etl_step_runs','resource_type',''),
('etl_step_runs','artifact_sha256',''),
('etl_step_runs','dbt_command',''),
('etl_step_runs','process_exit_code',''),
('etl_step_runs','artifact_verified','((0))'),
('etl_step_runs','artifact_path',''),
('etl_step_runs','status',''),
('etl_step_runs','start_time',''),
('etl_step_runs','end_time',''),
('etl_step_runs','native_duration_seconds',''),
('etl_step_runs','native_failures','')
) e(tbl,col,default_definition)
 EXCEPT SELECT t.name,c.name,LOWER(REPLACE(REPLACE(REPLACE(ISNULL(d.definition,''),'[',''),']',''),' ',''))
 FROM sys.tables t JOIN sys.columns c ON c.object_id=t.object_id
 LEFT JOIN sys.default_constraints d ON d.object_id=c.default_object_id
 WHERE t.schema_id=SCHEMA_ID('monitoring')) THROW 51000,'Monitoring default/UTC contract mismatch',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('monitoring.etl_runs') AND name='UX_etl_runs_legacy_batch')
CREATE UNIQUE INDEX UX_etl_runs_legacy_batch ON monitoring.etl_runs(legacy_load_batch_id)
    WHERE legacy_load_batch_id IS NOT NULL;
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('monitoring.etl_step_runs') AND name='UX_dbt_invocation')
CREATE UNIQUE INDEX UX_dbt_invocation ON monitoring.etl_step_runs(dbt_invocation_id)
    WHERE step_key='dbt' AND dbt_invocation_id IS NOT NULL;
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('monitoring.etl_errors') AND name='IX_etl_errors_execution')
CREATE INDEX IX_etl_errors_execution ON monitoring.etl_errors(execution_key,occurred_at,error_id);
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('monitoring.etl_runs') AND name='IX_etl_runs_start')
CREATE INDEX IX_etl_runs_start ON monitoring.etl_runs(start_time) INCLUDE(status,batch_type,evidence_kind);
IF NOT EXISTS(SELECT 1 FROM sys.indexes i WHERE i.object_id=OBJECT_ID('monitoring.etl_errors') AND i.name='IX_etl_errors_execution'
 AND i.is_unique=0 AND i.is_disabled=0
 AND LOWER(REPLACE(REPLACE(REPLACE(ISNULL(i.filter_definition,''),'[',''),']',''),' ',''))=''
 AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=0)='execution_key,occurred_at,error_id'
 AND ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY c.name)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=1),'')='')
 THROW 51000,'Monitoring index contract mismatch: IX_etl_errors_execution',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes i WHERE i.object_id=OBJECT_ID('monitoring.etl_runs') AND i.name='IX_etl_runs_start'
 AND i.is_unique=0 AND i.is_disabled=0
 AND LOWER(REPLACE(REPLACE(REPLACE(ISNULL(i.filter_definition,''),'[',''),']',''),' ',''))=''
 AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=0)='start_time'
 AND ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY c.name)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=1),'')='batch_type,evidence_kind,status')
 THROW 51000,'Monitoring index contract mismatch: IX_etl_runs_start',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes i WHERE i.object_id=OBJECT_ID('monitoring.etl_runs') AND i.name='UQ_etl_runs_attempt'
 AND i.is_unique=1 AND i.is_disabled=0
 AND LOWER(REPLACE(REPLACE(REPLACE(ISNULL(i.filter_definition,''),'[',''),']',''),' ',''))=''
 AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=0)='run_id,attempt_id'
 AND ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY c.name)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=1),'')='')
 THROW 51000,'Monitoring index contract mismatch: UQ_etl_runs_attempt',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes i WHERE i.object_id=OBJECT_ID('monitoring.etl_runs') AND i.name='UX_etl_runs_legacy_batch'
 AND i.is_unique=1 AND i.is_disabled=0
 AND LOWER(REPLACE(REPLACE(REPLACE(ISNULL(i.filter_definition,''),'[',''),']',''),' ',''))='(legacy_load_batch_idisnotnull)'
 AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=0)='legacy_load_batch_id'
 AND ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY c.name)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=1),'')='')
 THROW 51000,'Monitoring index contract mismatch: UX_etl_runs_legacy_batch',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes i WHERE i.object_id=OBJECT_ID('monitoring.etl_step_runs') AND i.name='UX_dbt_invocation'
 AND i.is_unique=1 AND i.is_disabled=0
 AND LOWER(REPLACE(REPLACE(REPLACE(ISNULL(i.filter_definition,''),'[',''),']',''),' ',''))='(step_key=''dbt''anddbt_invocation_idisnotnull)'
 AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY ic.key_ordinal)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=0)='dbt_invocation_id'
 AND ISNULL((SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP(ORDER BY c.name)
 FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.is_included_column=1),'')='')
 THROW 51000,'Monitoring index contract mismatch: UX_dbt_invocation',1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('monitoring.etl_errors') AND name='UX_etl_errors_event')
 EXEC(N'CREATE UNIQUE INDEX UX_etl_errors_event ON monitoring.etl_errors(execution_key,event_key) WHERE event_key IS NOT NULL;');
IF EXISTS(SELECT 1 FROM sys.foreign_keys WHERE parent_object_id IN
 (OBJECT_ID('monitoring.etl_runs'),OBJECT_ID('monitoring.etl_step_runs'),OBJECT_ID('monitoring.etl_record_metrics'),OBJECT_ID('monitoring.etl_errors'))
 AND (is_disabled=1 OR is_not_trusted=1)) THROW 51000,'Untrusted monitoring FK',1;
IF EXISTS(SELECT 1 FROM sys.check_constraints WHERE schema_id=SCHEMA_ID('monitoring') AND (is_disabled=1 OR is_not_trusted=1))
 THROW 51000,'Untrusted monitoring CHECK',1;
IF EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=0 AND name='ETLMonitoring.Environment'
 AND CONVERT(nvarchar(128),value)<>N'APPROVED_PRIMARY')
 THROW 51000,'Environment marker conflict; no automatic repair',1;
IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=0 AND name='ETLMonitoring.Environment')
 EXEC sys.sp_addextendedproperty @name=N'ETLMonitoring.Environment',@value=N'APPROVED_PRIMARY';
 COMMIT;
END TRY BEGIN CATCH IF @@TRANCOUNT>0 ROLLBACK; THROW; END CATCH;
GO
