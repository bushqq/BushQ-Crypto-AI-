@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title BushQ Crypto AI - Install Dependencies

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

echo 正在安装/更新依赖...
"%PYTHON%" -m pip install -r requirements.txt
echo.
echo 安装结束，按任意键关闭。
pause >nul
endlocal
