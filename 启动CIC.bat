@echo off
chcp 65001 >nul
setlocal

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"
title BushQ Crypto AI

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

:menu
cls
echo ========================================
echo      BushQ Crypto AI
echo ========================================
echo.
echo  1. 启动自动推送软件
echo  2. 立即生成并推送一次报告
echo  3. 检查数据源健康状态
echo  4. 打开报告目录
echo  5. 编辑 AI Prompt
echo  6. 安装/更新依赖
echo  7. 打开桌面软件
echo  0. 退出
echo.
set /p choice=请选择操作：

if "%choice%"=="1" goto start_scheduler
if "%choice%"=="2" goto run_once
if "%choice%"=="3" goto health
if "%choice%"=="4" goto reports
if "%choice%"=="5" goto prompt
if "%choice%"=="6" goto install
if "%choice%"=="7" goto desktop
if "%choice%"=="0" goto end
goto menu

:start_scheduler
cls
echo 正在启动自动推送软件...
echo 关闭此窗口或按 Ctrl+C 可停止。
echo.
"%PYTHON%" main.py
pause
goto menu

:run_once
cls
echo 正在立即生成并推送一次报告...
echo.
"%PYTHON%" main.py --once
pause
goto menu

:health
cls
echo 正在检查数据源健康状态...
echo.
"%PYTHON%" main.py --health
pause
goto menu

:reports
if not exist "data\reports" mkdir "data\reports"
start "" "data\reports"
goto menu

:prompt
if not exist "templates\prompts" mkdir "templates\prompts"
start "" notepad "templates\prompts\daily_analysis.md"
goto menu

:install
cls
echo 正在安装/更新依赖...
echo.
"%PYTHON%" -m pip install -r requirements.txt
pause
goto menu

:desktop
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" gui_app.py
) else (
  python gui_app.py
)
goto menu

:end
endlocal
