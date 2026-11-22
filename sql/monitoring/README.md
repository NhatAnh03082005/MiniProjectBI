# ETL Monitoring operations

The deployable scripts are in `primary/`; they support the approved PRIMARY or TEST targets where indicated. The runtime does not launch Mage or dbt. Keep orchestration in its existing owner branch.

## Dependencies

Use Python 3.11, SQL Server and Microsoft ODBC Driver 18. From the project root:

```powershell
python -m venv .mage_venv
./.mage_venv/Scripts/python.exe -m pip install -e ".[mage]"
python -m venv dbt_project/.venv
./dbt_project/.venv/Scripts/python.exe -m pip install -r dbt_project/requirements.txt
```

The optional local `.venv/python.exe` is a portable Python 3.11 interpreter, not a virtual environment. It can replace `python` above on this workstation; it is not committed.

## Deployment

Review and approve the target before executing DDL. Run with `sqlcmd -b` in this order: `00_additive_alignment.sql`, `01_monitoring_schema.sql`, `02_logging_procedures.sql`, `03_reporting_views.sql`, `04_monitoring_role.sql`; then `05_validate_readonly.sql`. Use `06_monitoring_runtime_principal.sql` only for the approved monitoring-only identity setup.

```powershell
sqlcmd -S 'localhost\SQLEXPRESS' -E -C -d AmazonDeliveryBI -b `
  -v MonitoringDatabase=AmazonDeliveryBI DeploymentEnvironment=PRIMARY DeploymentApproval=APPROVED_PRIMARY `
  -i sql/monitoring/primary/00_additive_alignment.sql
```

The approval token is an interlock, not authorization. Do not substitute reset/bootstrap scripts for migration. No script copies TEST history. Added historical action counters remain NULL.

`primary/hash_baseline.py --environment PRIMARY` is check-only. Applying missing row hashes needs separate approval with `--apply --approval APPROVED_PRIMARY_HASH_BASELINE`; it does not update business fields or fill action counters. A non-NULL mismatch stops the operation.

## Logging interface

Import `MonitoringAdapter` and `Settings` from `etl_monitoring.adapter`. Configure explicit environment/server/database; no target fallback is allowed. Operations: `start_run`, `start_stage`, `finish_stage`, `finish_run`, `log_counters`, `log_error`.

Persist run_id/execution_key before start_run. Logical retry keeps run_id and creates a new execution_key; SQL allocates attempt_id. Retry after a lost logging acknowledgement reuses the exact key/payload. Pass `ctx.variables()` through the existing Mage blocks so runtime hooks reuse the same execution.

Source/Mage/Validation/Export/Verification belong to existing Mage hooks; dbt/Warehouse belong to the orchestration caller. Avoid double recording. Use `prepare_dbt_ticket` and `verify_dbt_artifacts` for unique per-execution artifacts and explicit IDs. These functions do not run dbt. The legacy manual artifact recorder remains TEST-only.

COMMITTED action metrics must share the business DML transaction. Canonical counts are latest successful `export` / `STAGING_UPSERT` / `staging.raw_amazon_delivery` observations. Do not add Source/Validation/dbt node counts to them. Read = valid + technical rejected; valid = inserted + updated + unchanged; written = inserted + updated. Unknown stays NULL. Commit acknowledgement loss is IN_DOUBT until the durable witness is reconciled; do not automatically repeat DML.

## Connections and Power BI

`config/amazon_primary/Enter-Monitoring.ps1` enables a process-local PRIMARY logging profile. Its disabled SQL principal is impersonated without revert and has monitoring permissions only, not business upsert permissions. Use a clean shell; do not reuse a TEST-guarded process. Actual export/Verification requires a separately reviewed non-sysadmin business connection with staging/audit and monitoring permissions.

TEST templates and the process guard remain in `config/amazon_test/`. Credentials must never be committed. The current PBIP imports four PRIMARY views: `monitoring.vw_etl_run_summary`, `vw_etl_record_metrics`, `vw_etl_step_status`, `vw_etl_error_details`. Relationships use execution_key, single-direction from run summary. The ETL page filters REAL native executions. Empty history means no measured rate/duration/action counts, not a successful pipeline.
