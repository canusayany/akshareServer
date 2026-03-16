@echo off
setlocal
:: 启动 AKShare 本地 HTTP 服务器 (http://127.0.0.1:8888)
:: 用法: start_server.cmd [nossl]
::   nossl - 禁用 SSL 验证（企业代理环境）

cd /d "%~dp0"
set "ROOT=%~dp0"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"
set "DATA_DIR=%ROOT%\data"
set "DB_PATH=%DATA_DIR%\akshare_cache.sqlite"
set "PYTHON_PATH=%ROOT%\python"

if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

if not exist "%VENV_PY%" (
    echo Creating venv...
    py -m venv "%ROOT%\.venv"
    if errorlevel 1 (
        python -m venv "%ROOT%\.venv"
    )
)
if not exist "%VENV_PY%" (
    echo Error: venv Python not found. Install Python 3.11+
    pause
    exit /b 1
)

set "PYTHONPATH=%PYTHON_PATH%"
set "AKSHARE_NODE_DB_PATH=%DB_PATH%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if /i "%1"=="nossl" (
    set "AKSHARE_NO_SSL_VERIFY=1"
    echo SSL verification DISABLED
)

echo Starting AKShare server on http://127.0.0.1:8888
echo Database: %DB_PATH%

"%VENV_PY%" -m akshare_node_bridge.server
endlocal
