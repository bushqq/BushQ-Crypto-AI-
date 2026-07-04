@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title BushQ Crypto AI - Build Desktop EXE

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

echo 正在安装打包工具...
"%PYTHON%" -m pip install pyinstaller PySide6-Essentials
if errorlevel 1 goto failed

echo.
echo 正在清理旧桌面软件包...
if exist build rmdir /s /q build
if exist dist\BushQCryptoAI rmdir /s /q dist\BushQCryptoAI

echo.
echo 正在打包桌面软件...
"%PYTHON%" -m PyInstaller --noconfirm --windowed --onedir --name BushQCryptoAI --icon "assets\bushq_crypto_ai.ico" app.py
if errorlevel 1 goto failed

echo.
echo 正在复制配置和模板...
xcopy "config" "dist\BushQCryptoAI\config\" /E /I /Y >nul
xcopy "templates" "dist\BushQCryptoAI\templates\" /E /I /Y >nul
xcopy "assets" "dist\BushQCryptoAI\assets\" /E /I /Y >nul
copy ".env" "dist\BushQCryptoAI\.env" >nul
if not exist "dist\BushQCryptoAI\_internal" mkdir "dist\BushQCryptoAI\_internal"
xcopy "config" "dist\BushQCryptoAI\_internal\config\" /E /I /Y >nul
xcopy "templates" "dist\BushQCryptoAI\_internal\templates\" /E /I /Y >nul
xcopy "assets" "dist\BushQCryptoAI\_internal\assets\" /E /I /Y >nul
copy ".env" "dist\BushQCryptoAI\_internal\.env" >nul
if not exist "dist\BushQCryptoAI\data" mkdir "dist\BushQCryptoAI\data"
if not exist "dist\BushQCryptoAI\logs" mkdir "dist\BushQCryptoAI\logs"

echo.
echo 打包完成：
echo %CD%\dist\BushQCryptoAI\BushQCryptoAI.exe
echo.
pause
goto end

:failed
echo.
echo 打包失败，请查看上方错误信息。
pause

:end
endlocal
