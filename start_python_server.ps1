[CmdletBinding()]
param(
    # Disable SSL certificate verification for all outbound HTTPS requests.
    # Use this when a corporate TLS-inspection proxy causes "certificate verify
    # failed" errors from AKShare.  Sets AKSHARE_NO_SSL_VERIFY=1.
    [switch]$Nossl,

    # Skip pip install steps.  Use this for fast restarts when dependencies
    # are already installed in the virtual environment.
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $root ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$requirements = Join-Path $root "requirements.txt"
$dataDir = Join-Path $root "data"
$dbPath = Join-Path $dataDir "akshare_cache.sqlite"
$pythonPath = Join-Path $root "python"
$requiredModules = @("akshare", "pandas", "requests", "baostock", "certifi")

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

function Test-RequiredModules {
    param(
        [string]$PythonExe,
        [string[]]$Modules
    )

    $jsonModules = ($Modules | ConvertTo-Json -Compress)
    $code = "import importlib.util, json; mods = $jsonModules; print(json.dumps({m: bool(importlib.util.find_spec(m)) for m in mods}))"
    try {
        $output = & $PythonExe -c $code 2>$null
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($output)) {
            return $false
        }
        $state = $output | ConvertFrom-Json
        foreach ($module in $Modules) {
            if (-not $state.$module) {
                return $false
            }
        }
        return $true
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

if ($SkipInstall -and -not (Test-RequiredModules -PythonExe $venvPython -Modules $requiredModules)) {
    Write-Host "Detected missing Python packages in $venvDir, forcing dependency install." -ForegroundColor Yellow
    $SkipInstall = $false
}

if (-not $SkipInstall) {
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip in $venvDir"
    }

    & $venvPython -m pip install -r $requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install requirements from $requirements"
    }
} else {
    Write-Host "Skipping pip install (-SkipInstall)" -ForegroundColor Yellow
}

$env:PYTHONPATH = $pythonPath
$env:AKSHARE_NODE_DB_PATH = $dbPath
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

if ($Nossl) {
    $env:AKSHARE_NO_SSL_VERIFY = "1"
    Write-Host "SSL verification DISABLED (AKSHARE_NO_SSL_VERIFY=1)" -ForegroundColor Yellow
    Write-Host "Only use this behind a trusted corporate TLS-inspection proxy." -ForegroundColor Yellow
}

Write-Host "Starting AKShare local server on http://127.0.0.1:8888" -ForegroundColor Green
Write-Host "Database: $dbPath"
Write-Host "Python: $venvPython"

& $venvPython -m akshare_node_bridge.server

