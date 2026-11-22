# Dot-source this file in a NEW PowerShell for TEST. Does not start Mage or dbt.
$amazonRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$env:PYTHONPATH = "$PSScriptRoot;$amazonRoot"
$env:AMAZON_TEST_CONNECTIONS = '1'
$env:AMAZON_MONITORING_ENABLED = '1'
$env:MSSQL_SERVER = 'localhost\SQLEXPRESS'
$env:MSSQL_DATABASE = 'AmazonDeliveryBI_TEST'
$env:MSSQL_DRIVER = 'ODBC Driver 18 for SQL Server'
$env:BI_PROJECT_ROOT = $amazonRoot
$env:DBT_SQLSERVER_DATABASE = 'AmazonDeliveryBI_TEST'
$env:DBT_SQLSERVER_SERVER = 'localhost\SQLEXPRESS'
$env:DBT_SEND_ANONYMOUS_USAGE_STATS = 'false'
$env:MAGE_DATA_DIR = Join-Path $amazonRoot '.runtime_test\mage_data'
$env:MAGE_DATABASE_CONNECTION_URL = 'sqlite:///' + ((Join-Path $env:MAGE_DATA_DIR 'mage-ai.db') -replace '\\','/')
New-Item -ItemType Directory -Force -Path $env:MAGE_DATA_DIR | Out-Null
$env:AMAZON_EVIDENCE_KIND = 'TEST'
$env:DEBUG = '0'
# CLI target/profile/artifact paths are explicit in the manual instructions.
