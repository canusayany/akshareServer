@echo off
:: 无 SSL 验证快速启动 AKShare 本地服务器
:: 使用: start_nossl.cmd          (跳过 pip 安装)
:: 使用: start_nossl.cmd -Install  (重新安装依赖)
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0start_nossl.ps1" %*
endlocal
