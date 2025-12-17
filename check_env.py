# -*- coding: utf-8 -*-
"""
环境检查脚本 - 自动查找合适的Python环境并检查依赖
"""

import subprocess
import sys
import os
import re

MIN_VERSION = (3, 10)
REQUIRED_PACKAGES = [
    'torch', 'ultralytics', 'cv2', 'numpy', 'scipy',
    'PyQt5', 'keyboard', 'pynput', 'pyautogui',
    'win32gui', 'loguru', 'dxcam'
]


def get_version_tuple(version_str):
    """解析版本字符串为元组"""
    match = re.match(r'(\d+)\.(\d+)', version_str)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (0, 0)


def run_command(cmd, shell=True):
    """运行命令并返回输出"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=30)
        return result.stdout.strip(), result.returncode
    except Exception:
        return "", 1


def get_conda_envs():
    """获取所有conda环境"""
    envs = []
    output, code = run_command("conda env list")
    if code == 0:
        for line in output.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split()
                if parts:
                    env_name = parts[0]
                    if env_name != '*':
                        envs.append(('conda', env_name))
    return envs


def get_system_python():
    """获取系统Python"""
    envs = []
    output, code = run_command("python --version")
    if code == 0:
        envs.append(('system', 'python'))
    
    output, code = run_command("py -3 --version")
    if code == 0:
        envs.append(('py', 'py -3'))
    
    return envs


def check_python_version(env_type, env_name):
    """检查Python版本"""
    if env_type == 'conda':
        cmd = f'conda run -n {env_name} python --version'
    elif env_type == 'system':
        cmd = 'python --version'
    else:
        cmd = 'py -3 --version'
    
    output, code = run_command(cmd)
    if code == 0:
        match = re.search(r'Python (\d+\.\d+)', output)
        if match:
            version = get_version_tuple(match.group(1))
            return version
    return (0, 0)


def check_package(env_type, env_name, package):
    """检查包是否安装"""
    # cv2 对应 opencv-python
    import_name = package
    if package == 'cv2':
        import_name = 'cv2'
    elif package == 'win32gui':
        import_name = 'win32gui'
    
    if env_type == 'conda':
        cmd = f'conda run -n {env_name} python -c "import {import_name}"'
    elif env_type == 'system':
        cmd = f'python -c "import {import_name}"'
    else:
        cmd = f'py -3 -c "import {import_name}"'
    
    _, code = run_command(cmd)
    return code == 0


def check_cuda(env_type, env_name):
    """检查CUDA是否可用"""
    check_code = "import torch; print('yes' if torch.cuda.is_available() else 'no')"
    if env_type == 'conda':
        cmd = f'conda run -n {env_name} python -c "{check_code}"'
    elif env_type == 'system':
        cmd = f'python -c "{check_code}"'
    else:
        cmd = f'py -3 -c "{check_code}"'
    
    output, code = run_command(cmd)
    return output.strip() == 'yes' if code == 0 else False


def main():
    print("=" * 50)
    print("  BabyBus 环境检查工具")
    print("=" * 50)
    print()
    
    # 收集所有环境
    print("[1/4] 扫描Python环境...")
    all_envs = []
    
    conda_envs = get_conda_envs()
    system_envs = get_system_python()
    all_envs.extend(conda_envs)
    all_envs.extend(system_envs)
    
    if not all_envs:
        print("\n错误: 未找到任何Python环境!")
        print("请安装Python 3.10+或Anaconda")
        return None
    
    print(f"找到 {len(all_envs)} 个环境")
    
    # 检查每个环境
    print("\n[2/4] 检查Python版本...")
    valid_envs = []
    for env_type, env_name in all_envs:
        version = check_python_version(env_type, env_name)
        version_str = f"{version[0]}.{version[1]}"
        
        if version >= MIN_VERSION:
            valid_envs.append((env_type, env_name, version))
            status = "✓"
        else:
            status = "✗"
        
        display_name = f"{env_name} ({env_type})" if env_type == 'conda' else env_name
        print(f"  {status} {display_name}: Python {version_str}")
    
    if not valid_envs:
        print(f"\n错误: 没有找到Python >= {MIN_VERSION[0]}.{MIN_VERSION[1]} 的环境!")
        return None
    
    # 检查依赖
    print("\n[3/4] 检查依赖包...")
    best_env = None
    best_score = -1
    
    for env_type, env_name, version in valid_envs:
        display_name = f"{env_name} ({env_type})" if env_type == 'conda' else env_name
        print(f"\n  检查环境: {display_name}")
        
        missing = []
        installed = []
        for pkg in REQUIRED_PACKAGES:
            if check_package(env_type, env_name, pkg):
                installed.append(pkg)
            else:
                missing.append(pkg)
        
        # 检查CUDA
        has_cuda = check_cuda(env_type, env_name)
        cuda_status = "✓ CUDA可用" if has_cuda else "✗ 仅CPU"
        
        score = len(installed) + (10 if has_cuda else 0)
        
        print(f"    已安装: {len(installed)}/{len(REQUIRED_PACKAGES)}")
        print(f"    {cuda_status}")
        if missing:
            print(f"    缺失: {', '.join(missing)}")
        
        if score > best_score:
            best_score = score
            best_env = (env_type, env_name, version, missing, has_cuda)
    
    # 输出结果
    print("\n" + "=" * 50)
    print("[4/4] 推荐环境")
    print("=" * 50)
    
    if best_env:
        env_type, env_name, version, missing, has_cuda = best_env
        display_name = f"{env_name} ({env_type})" if env_type == 'conda' else env_name
        
        print(f"\n推荐使用: {display_name}")
        print(f"Python版本: {version[0]}.{version[1]}")
        print(f"CUDA支持: {'是' if has_cuda else '否'}")
        
        if missing:
            print(f"\n需要安装以下依赖:")
            for pkg in missing:
                print(f"  - {pkg}")
            print(f"\n安装命令:")
            if env_type == 'conda':
                print(f"  conda activate {env_name}")
                print(f"  pip install {' '.join(missing)}")
            else:
                print(f"  pip install {' '.join(missing)}")
        else:
            print("\n所有依赖已安装，可以直接运行!")
        
        return best_env
    
    return None


if __name__ == "__main__":
    result = main()
    print()
    input("按回车键退出...")
