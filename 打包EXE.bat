@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title CIC - Build EXE

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

echo 正在安装 PyInstaller...
"%PYTHON%" -m pip install pyinstaller
if errorlevel 1 goto failed

echo.
echo 正在清理旧打包目录...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo 正在打包 CryptoIntelCenter.exe...
"%PYTHON%" -m PyInstaller --noconfirm --onedir --name CryptoIntelCenter app.py
if errorlevel 1 goto failed

echo.
echo 正在复制运行配置...
xcopy config "dist\CryptoIntelCenter\config\" /E /I /Y >nul
xcopy templates "dist\CryptoIntelCenter\templates\" /E /I /Y >nul
copy ".env" "dist\CryptoIntelCenter\.env" >nul
if not exist "dist\CryptoIntelCenter\data" mkdir "dist\CryptoIntelCenter\data"
if not exist "dist\CryptoIntelCenter\logs" mkdir "dist\CryptoIntelCenter\logs"

echo.
echo 打包完成：
echo %CD%\dist\CryptoIntelCenter\CryptoIntelCenter.exe
echo.
pause
goto end

:failed
echo.
echo 打包失败，请查看上方错误信息。
pause

:end
endlocal
