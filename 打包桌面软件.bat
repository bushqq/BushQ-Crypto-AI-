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

"%PYTHON%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
  echo 正在安装打包依赖...
  "%PYTHON%" -m pip install -r requirements-build.txt
  if errorlevel 1 goto failed
)

echo.
echo 正在清理旧桌面软件包...
if exist build rmdir /s /q build
if exist dist\BushQCryptoAI rmdir /s /q dist\BushQCryptoAI

echo.
echo 正在打包桌面软件...
"%PYTHON%" -m PyInstaller --noconfirm --clean BushQCryptoAI.spec
if errorlevel 1 goto failed

echo.
echo 正在准备本地数据目录...
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
