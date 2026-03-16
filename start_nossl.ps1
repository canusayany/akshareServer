<#
.SYNOPSIS
    Fast startup wrapper with SSL verification disabled.

.DESCRIPTION
    This script forwards to start_python_server.ps1 and forces
    AKSHARE_NO_SSL_VERIFY mode by passing -Nossl.

    Default behavior skips pip install for quick restart.
    Use -Install if you want to reinstall dependencies first.

.PARAMETER Install
    Run pip install before starting the server.

.EXAMPLE
    .\start_nossl.ps1
    .\start_nossl.ps1 -Install
#>

param(
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainScript = Join-Path $scriptDir "start_python_server.ps1"

if (-not (Test-Path $mainScript)) {
    throw "Cannot find $mainScript. Run this script from the akshareServer folder."
}

if ($Install) {
    Write-Host "Starting with dependency install (AKSHARE_NO_SSL_VERIFY=1)" -ForegroundColor Cyan
    & $mainScript -Nossl
} else {
    Write-Host "Fast start with pip install skipped (AKSHARE_NO_SSL_VERIFY=1)" -ForegroundColor Cyan
    Write-Host "Use .\start_nossl.ps1 -Install to reinstall dependencies first." -ForegroundColor Gray
    & $mainScript -Nossl -SkipInstall
}
