/* Run in the SAME database as Mage. No USE/GO: also executed by the runner.
   One row per dbt attempt, not per ingestion batch. Existing audit is preserved. */
IF OBJECT_ID(N'audit.dbt_run', N'U') IS NULL
BEGIN
    CREATE TABLE audit.dbt_run (
        dbt_attempt_id VARCHAR(64) NOT NULL PRIMARY KEY,
        load_batch_id VARCHAR(64) NOT NULL,
        status VARCHAR(20) NOT NULL,
        started_at DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        finished_at DATETIME2(3) NULL,
        exit_code INT NULL,
        log_directory NVARCHAR(1024) NOT NULL,
        result_summary NVARCHAR(MAX) NULL,
        error_message NVARCHAR(2000) NULL,
        CONSTRAINT FK_dbt_run_load_batch FOREIGN KEY (load_batch_id)
            REFERENCES audit.load_batch(load_batch_id),
        CONSTRAINT CK_dbt_run_status CHECK (status IN ('STARTED', 'SUCCEEDED', 'FAILED'))
    );
    CREATE INDEX IX_dbt_run_batch ON audit.dbt_run(load_batch_id, started_at);
END;
