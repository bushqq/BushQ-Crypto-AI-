@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title BushQ Crypto AI - Auto Scheduler

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

echo BushQ Crypto AI 自动推送已启动。
echo 会在亚股、欧股、美股开盘前 1 小时运行分析并推送。
echo 关闭此窗口或按 Ctrl+C 可停止。
echo.
"%PYTHON%" main.py
endlocal
