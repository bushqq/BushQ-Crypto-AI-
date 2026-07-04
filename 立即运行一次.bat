@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title BushQ Crypto AI - Run Once

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

echo 正在生成并推送一次 BushQ Crypto AI 报告...
echo.
"%PYTHON%" main.py --once
echo.
echo 执行结束，按任意键关闭。
pause >nul
endlocal
