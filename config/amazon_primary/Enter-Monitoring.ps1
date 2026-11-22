# PRIMARY monitoring only; process-local settings. Does not launch ETL/dbt or DDL.
# Deliberately does not configure business-writing connections.
if ($env:AMAZON_TEST_CONNECTIONS -eq '1') { throw 'Use a clean PRIMARY shell; do not reuse a TEST-guarded process.' }
$env:ETL_MONITORING_ENV='PRIMARY'
$env:ETL_MONITORING_SERVER='localhost\SQLEXPRESS'
$env:ETL_MONITORING_DATABASE='AmazonDeliveryBI'
$env:ETL_MONITORING_PRIMARY_WRITES='APPROVED_PRIMARY'
$env:ETL_MONITORING_PRINCIPAL='AmazonDeliveryBI_Monitoring_Runtime'
