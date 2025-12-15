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

:: 检测Python环境并启动GUI（无窗口模式）

:: 方式1: 尝试conda环境
call conda activate yolov8 2>nul
if %errorlevel% equ 0 (
    start "" /B pythonw "%BASE_DIR%gui_app.py"
    goto :end
)

:: 方式2: 获取python路径，替换为pythonw
for /f "delims=" %%i in ('where python 2^>nul') do (
    set "PYTHON_PATH=%%i"
    goto :found_python
)
goto :try_py

:found_python
:: 将python.exe替换为pythonw.exe
set "PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%"
if exist "%PYTHONW_PATH%" (
    start "" /B "%PYTHONW_PATH%" "%BASE_DIR%gui_app.py"
    goto :end
)
:: pythonw不存在，用python但隐藏窗口
start "" /B /MIN python "%BASE_DIR%gui_app.py"
goto :end

:try_py
:: 方式3: 尝试py启动器
py --version >nul 2>&1
if %errorlevel% equ 0 (
    start "" /B /MIN py "%BASE_DIR%gui_app.py"
    goto :end
)

:: 都不可用，提示错误
echo 错误: 未找到Python环境
echo 请确保已安装Python并添加到系统PATH环境变量
pause

:end
endlocal
