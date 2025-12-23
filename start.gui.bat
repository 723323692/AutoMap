@echo off
chcp 65001 >nul

:: 自我提权为管理员
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

setlocal
set BASE_DIR=%~dp0
set PYTHONPATH=%BASE_DIR%
set PYTHON_CMD=
set ENV_NAME=

echo ========================================
echo        BabyBus 启动器
echo ========================================
echo.

:: 1. 优先conda yolov8
where conda >nul 2>&1
if %errorlevel% equ 0 (
    call conda activate yolov8 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=pythonw
        set ENV_NAME=conda yolov8
        goto :found
    )
)

:: 2. pythonw (静默运行，无黑窗口)
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('where pythonw') do set PYTHON_CMD=%%i& goto :pythonw_found
)
:pythonw_found
if defined PYTHON_CMD (
    set ENV_NAME=pythonw
    goto :found
)

:: 3. python
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('where python') do set PYTHON_CMD=%%i& goto :python_found
)
:python_found
if defined PYTHON_CMD (
    set ENV_NAME=python
    goto :found
)

:: 4. py启动器
where py >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3
    set ENV_NAME=py启动器
    goto :found
)

:: 未找到
echo [错误] 未找到Python环境!
echo 请安装Python 3.9+ 或 Anaconda
pause
exit /b 1

:found
echo [环境] %ENV_NAME%
echo [路径] %PYTHON_CMD%
echo.
echo 正在启动...
start "" /B %PYTHON_CMD% "%BASE_DIR%gui_app.py"
echo 启动成功!
timeout /t 2 >nul
endlocal
