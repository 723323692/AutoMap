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

:: 检测Python环境并启动GUI
echo 正在检测Python环境...

:: 方式1: 检查conda是否可用
where conda >nul 2>&1
if %errorlevel% equ 0 (
    echo 检测到Conda环境
    :: 尝试激活指定环境（可修改环境名）
    call conda activate yolov8 2>nul
    if %errorlevel% equ 0 (
        echo 已激活conda环境: yolov8
        start "" /B pythonw "%BASE_DIR%gui_app.py"
        goto :end
    )
    :: 尝试激活base环境
    call conda activate base 2>nul
    if %errorlevel% equ 0 (
        echo 已激活conda环境: base
        start "" /B pythonw "%BASE_DIR%gui_app.py"
        goto :end
    )
)

:: 方式2: 检查系统Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo 检测到系统Python
    for /f "delims=" %%i in ('where python 2^>nul') do (
        set "PYTHON_PATH=%%i"
        goto :found_python
    )
)
goto :try_py

:found_python
:: 将python.exe替换为pythonw.exe（无窗口模式）
set "PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%"
if exist "%PYTHONW_PATH%" (
    echo 使用: %PYTHONW_PATH%
    start "" /B "%PYTHONW_PATH%" "%BASE_DIR%gui_app.py"
    goto :end
)
:: pythonw不存在，用python
echo 使用: %PYTHON_PATH%
start "" /B python "%BASE_DIR%gui_app.py"
goto :end

:try_py
:: 方式3: 尝试py启动器（Windows Python Launcher）
where py >nul 2>&1
if %errorlevel% equ 0 (
    echo 检测到Python Launcher
    start "" /B py -3 "%BASE_DIR%gui_app.py"
    goto :end
)

:: 方式4: 检查常见安装路径
if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" (
    echo 使用: Python 3.11
    start "" /B "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" "%BASE_DIR%gui_app.py"
    goto :end
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe" (
    echo 使用: Python 3.10
    start "" /B "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe" "%BASE_DIR%gui_app.py"
    goto :end
)
if exist "%LOCALAPPDATA%\Programs\Python\Python39\pythonw.exe" (
    echo 使用: Python 3.9
    start "" /B "%LOCALAPPDATA%\Programs\Python\Python39\pythonw.exe" "%BASE_DIR%gui_app.py"
    goto :end
)
if exist "C:\Python311\pythonw.exe" (
    start "" /B "C:\Python311\pythonw.exe" "%BASE_DIR%gui_app.py"
    goto :end
)
if exist "C:\Python310\pythonw.exe" (
    start "" /B "C:\Python310\pythonw.exe" "%BASE_DIR%gui_app.py"
    goto :end
)

:: 都不可用，提示错误
echo.
echo ========================================
echo 错误: 未找到Python环境
echo ========================================
echo.
echo 请确保已安装以下任一环境:
echo   1. Anaconda/Miniconda (推荐)
echo   2. Python 3.9+ 并添加到系统PATH
echo.
echo 安装后请重新运行此脚本
echo.
pause
exit /b 1

:end
echo 启动成功!
timeout /t 2 >nul
endlocal
