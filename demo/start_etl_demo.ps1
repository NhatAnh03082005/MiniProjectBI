param(
    [string]$Server = 'localhost\SQLEXPRESS',
    [ValidateSet('AmazonDeliveryBI_Demo', 'AmazonDeliveryBI')]
    [string]$Database = 'AmazonDeliveryBI_Demo',
    [string]$Driver = 'ODBC Driver 18 for SQL Server',
    [ValidateSet('sql', 'windows')]
    [string]$Authentication = 'sql',
    [string]$User = 'sa'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
$magePath = Join-Path $projectRoot '.venv/Scripts/mage.exe'
if (!(Test-Path -LiteralPath $pythonPath) -or !(Test-Path -LiteralPath $magePath)) {
    throw 'Can moi truong .venv co Mage. Xem MAGE_TEAM_SETUP.md.'
}
$env:BI_PROJECT_ROOT = $projectRoot
$env:MSSQL_SERVER = $Server
$env:MSSQL_DATABASE = $Database
$env:MSSQL_DRIVER = $Driver
$env:PYTHONUTF8 = '1'
$env:MSSQL_AUTHENTICATION = $Authentication
if ($Authentication -eq 'sql') {
    $env:MSSQL_USER = $User
    $securePassword = Read-Host "Nhap mat khau SQL Server cho $User" -AsSecureString
    $credential = [System.Management.Automation.PSCredential]::new($User, $securePassword)
    $env:MSSQL_PASSWORD = $credential.GetNetworkCredential().Password
}
if (!$env:DBT_PYTHON_EXECUTABLE) { $env:DBT_PYTHON_EXECUTABLE = $pythonPath }
if (!$env:DBT_BUILD_TIMEOUT_SECONDS) { $env:DBT_BUILD_TIMEOUT_SECONDS = '1800' }
# Make the shared project modules importable by Mage workers.
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = $projectRoot + [IO.Path]::PathSeparator + $env:PYTHONPATH
} else {
    $env:PYTHONPATH = $projectRoot
}
Write-Host "Mage -> dbt target: $Server / $Database"
Write-Host 'Script nay khong tao/reset database va khong tu chay ETL.'
Push-Location $projectRoot
try {
    & $magePath start mage_project
    if ($LASTEXITCODE -ne 0) { throw "Mage exited with code $LASTEXITCODE" }
} finally {
    if ($Authentication -eq 'sql') { Remove-Item Env:MSSQL_PASSWORD -ErrorAction SilentlyContinue }
    Pop-Location
}
