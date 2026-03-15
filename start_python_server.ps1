$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $root ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$requirements = Join-Path $root "requirements.txt"
$dataDir = Join-Path $root "data"
$dbPath = Join-Path $dataDir "akshare_cache.sqlite"
$pythonPath = Join-Path $root "python"

function Get-PythonLauncher {
    foreach ($candidate in @("py", "python")) {
        try {
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
        }
    }
    throw "Python launcher not found. Install Python 3.11+ and ensure 'py' or 'python' is on PATH."
}

function Test-PortInUse {
    param([int]$Port)
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        return $null -ne $connection
    } catch {
        return $false
    }
}

if (Test-PortInUse -Port 8888) {
    throw "127.0.0.1:8888 is already in use. Stop the existing process before starting the local server."
}

if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

$pythonLauncher = Get-PythonLauncher

if (-not (Test-Path $venvPython)) {
    & $pythonLauncher -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment at $venvDir"
    }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip in $venvDir"
}

& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install requirements from $requirements"
}

$env:PYTHONPATH = $pythonPath
$env:AKSHARE_NODE_DB_PATH = $dbPath
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Write-Host "Starting AKShare local server on http://127.0.0.1:8888" -ForegroundColor Green
Write-Host "Database: $dbPath"
Write-Host "Python: $venvPython"

& $venvPython -m akshare_node_bridge.server

