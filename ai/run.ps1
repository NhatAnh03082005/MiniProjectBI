[CmdletBinding()]
param(
    [switch]$Install,
    [ValidateRange(1024,65535)][int]$Port=8501
)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$environmentPath=Join-Path $projectRoot '.ai_venv'
$aiPython=Join-Path $environmentPath 'Scripts\python.exe'
$versionProbe="import sys,sysconfig,struct; supported=(sys.implementation.name == 'cpython' and (3,11) <= sys.version_info[:2] < (3,14) and struct.calcsize('P') == 8 and not sysconfig.get_config_var('Py_GIL_DISABLED')); sys.exit(1) if not supported else print(sys.executable)"
function Get-AiBasePython {
    param([string]$Executable,[string[]]$LeadingArguments=@())
    try {
        # Windows PowerShell5.1 can turn native stderr into an exception.
        # Rejecting a candidate must still allow the next interpreter.
        $probeOutput=& $Executable @LeadingArguments -c $versionProbe 2>$null
        if ($LASTEXITCODE -eq 0) {return ([string]$probeOutput).Trim()}
    }
    catch {return $null}
    return $null
}
if (Test-Path -LiteralPath $environmentPath) {
    if (-not (Test-Path -LiteralPath $aiPython) -or -not (Get-AiBasePython -Executable $aiPython)) {
        throw 'Existing .ai_venv is incompatible or incomplete. Recreate it manually with standard 64-bit CPython 3.11-3.13, then run -Install. The launcher did not change it.'
    }
}
if (-not (Test-Path -LiteralPath $aiPython)) {
    $basePython=$null
    $projectPython=Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $projectPython) {
        $basePython=Get-AiBasePython -Executable $projectPython
    }
    # Prefer registered standard builds, then validate the default commands.
    # A default py -3 can resolve to a free-threaded or newer interpreter.
    if (-not $basePython -and (Get-Command py -ErrorAction SilentlyContinue)) {
        foreach ($pythonVersion in @('-3.11','-3.12','-3.13','-3')) {
            $basePython=Get-AiBasePython -Executable 'py' -LeadingArguments @($pythonVersion)
            if ($basePython) {break}
        }
    }
    if (-not $basePython -and (Get-Command python -ErrorAction SilentlyContinue)) {
        $basePython=Get-AiBasePython -Executable 'python'
    }
    if (-not $basePython -or -not (Test-Path -LiteralPath $basePython)) {
        throw 'Install standard 64-bit CPython 3.11 (or 3.12-3.13), then retry. Free-threaded, 32-bit, and Python 3.14+ builds are not supported by the pinned AI dependencies.'
    }
    & $basePython -m venv $environmentPath
    if ($LASTEXITCODE -ne 0) {throw 'Could not create the isolated AI environment.'}
    $Install=$true
}
if ($Install) {
    & $aiPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) {throw 'Dependency installation failed.'}
}
& $aiPython -c "import streamlit,pandas,pyodbc,httpx"
if ($LASTEXITCODE -ne 0) {throw 'Dependencies are missing. Run .\ai\run.ps1 -Install first.'}
Push-Location -LiteralPath $projectRoot
try {
    Write-Host "Open http://127.0.0.1:$Port in your browser. Press Ctrl+C to stop."
    & $aiPython -m streamlit run (Join-Path $PSScriptRoot 'app.py') --server.address 127.0.0.1 --server.port $Port --server.headless true --browser.gatherUsageStats false --theme.base light --theme.primaryColor '#FF9900' --theme.backgroundColor '#F4F6F8' --theme.secondaryBackgroundColor '#FFFFFF' --theme.textColor '#232F3E'
    if ($LASTEXITCODE -ne 0) {throw 'The AI application stopped with an error.'}
}
finally {Pop-Location}
