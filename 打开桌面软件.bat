@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title BushQ Crypto AI

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

"%PYTHON%" gui_app.py
endlocal
