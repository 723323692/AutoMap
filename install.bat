@echo off
chcp 65001 >nul
echo ========================================
echo    BabyBus 依赖安装脚本
echo ========================================
echo.

:: 检查是否有conda
echo [1/5] 检查Python环境...
where conda >nul 2>&1
if %errorlevel% equ 0 (
    echo 检测到Conda
    
    :: 检查yolov8环境是否存在
    conda env list | findstr /C:"yolov8" >nul 2>&1
    if %errorlevel% equ 0 (
        echo 检测到yolov8环境，正在激活...
        call conda activate yolov8
        echo 已激活: yolov8
    ) else (
        echo 未找到yolov8环境，正在创建...
        conda create -n yolov8 python=3.10 -y
        if errorlevel 1 (
            echo [错误] 创建conda环境失败
            pause
            exit /b 1
        )
        call conda activate yolov8
        echo 已创建并激活: yolov8
    )
    goto :check_python
)

:: 没有conda，检查系统Python
echo 未检测到Conda，检查系统Python...
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 未找到Python环境！
    echo.
    echo 请安装以下任一环境:
    echo   1. Anaconda: https://www.anaconda.com/download
    echo   2. Miniconda: https://docs.conda.io/en/latest/miniconda.html
    echo   3. Python 3.10+: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: 检查系统Python版本
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set MAJOR=%%a
    set MINOR=%%b
)
if %MAJOR% LSS 3 goto :version_error
if %MAJOR% EQU 3 if %MINOR% LSS 10 goto :version_error
echo 使用系统Python %PY_VER%
goto :check_python

:version_error
echo.
echo [错误] Python版本过低: %PY_VER%
echo 需要 Python 3.10 或更高版本
echo.
echo 建议安装Anaconda并创建新环境
echo.
pause
exit /b 1

:check_python
:: 显示当前Python信息
echo.
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo 当前Python: %%i

:: 检查是否已有完整依赖
echo.
echo [2/5] 检查已安装的依赖...
python -c "import torch; import ultralytics; import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo 缺少核心依赖，需要安装...
    goto :check_gpu
)

:: 依赖完整，检查PyTorch是否支持CUDA
echo 核心依赖已安装，检查CUDA支持...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    :: 没有NVIDIA显卡，不需要GPU版本
    goto :show_success
)

:: 有NVIDIA显卡，检查PyTorch是否支持CUDA
python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    goto :show_success
)

:: 有显卡但PyTorch不支持CUDA
echo.
echo [警告] 检测到NVIDIA显卡，但当前PyTorch是CPU版本！
echo.
echo 是否要升级到GPU版本？(推荐，速度更快)
echo [1] 是，升级到GPU版本
echo [2] 否，继续使用CPU版本
echo.
set /p UPGRADE_CHOICE=请输入选项 (1/2): 

if "%UPGRADE_CHOICE%"=="2" goto :show_success

:: 卸载CPU版本，安装GPU版本
echo.
echo 正在卸载CPU版本PyTorch...
pip uninstall torch torchvision -y >nul 2>&1

echo.
echo 请选择CUDA版本:
echo [1] CUDA 11.8 (推荐)
echo [2] CUDA 12.1
echo.
set /p CUDA_CHOICE=请输入选项 (1/2): 

if "%CUDA_CHOICE%"=="1" set CUDA_VERSION=cu118
if "%CUDA_CHOICE%"=="2" set CUDA_VERSION=cu121

echo.
echo 正在安装GPU版本PyTorch (%CUDA_VERSION%)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/%CUDA_VERSION%
goto :show_success

:show_success
echo.
echo ========================================
echo [成功] 环境检查完成！
echo ========================================
echo.
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA可用: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"无\"}')"
echo.
echo 运行 start.gui.bat 启动程序
echo.
pause
exit /b 0

:check_gpu
:: 检测NVIDIA显卡
echo.
echo [3/5] 检测显卡...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo 未检测到NVIDIA显卡，将安装CPU版本PyTorch
    set CUDA_VERSION=cpu
    goto :install_torch
)

echo 检测到NVIDIA显卡
echo.
echo 请选择PyTorch CUDA版本:
echo [1] CUDA 11.8 (推荐)
echo [2] CUDA 12.1
echo [3] CPU版本
echo.
set /p CUDA_CHOICE=请输入选项 (1/2/3): 

if "%CUDA_CHOICE%"=="1" set CUDA_VERSION=cu118
if "%CUDA_CHOICE%"=="2" set CUDA_VERSION=cu121
if "%CUDA_CHOICE%"=="3" set CUDA_VERSION=cpu

:install_torch
echo.
echo [4/5] 安装PyTorch (%CUDA_VERSION%)...
if "%CUDA_VERSION%"=="cpu" (
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
) else (
    pip install torch torchvision --index-url https://download.pytorch.org/whl/%CUDA_VERSION%
)

if errorlevel 1 (
    echo [错误] PyTorch安装失败
    pause
    exit /b 1
)

echo.
echo [5/5] 安装其他依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

goto :show_success
