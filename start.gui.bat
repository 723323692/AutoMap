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

echo 正在启动 BabyBus...
echo.

:: 优先使用conda yolov8环境
where conda >nul 2>&1
if %errorlevel% equ 0 (
    call conda activate yolov8 2>nul
    if %errorlevel% equ 0 (
        echo 使用conda环境: yolov8
        start "" /B pythonw "%BASE_DIR%gui_app.py"
        goto :end
    )
)

:: 使用系统Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo 使用系统Python
    start "" /B pythonw "%BASE_DIR%gui_app.py"
    goto :end
)

:: 未找到环境，运行检查脚本
echo 未找到合适的Python环境，正在检查...
python "%BASE_DIR%check_env.py"
pause
exit /b 1

:end
echo 启动成功!
timeout /t 2 >nul
endlocal
