# -*- coding: utf-8 -*-
"""
路径管理模块 - 统一管理配置文件和日志的存储位置
支持开发环境和打包后的 exe 环境
"""

import os
import sys
from pathlib import Path


def get_app_dir():
    """
    获取应用程序目录
    - 开发环境：项目根目录
    - 打包后：exe 所在目录
    """
    if getattr(sys, 'frozen', False):
        # 打包后的 exe
        return Path(sys.executable).parent
    else:
        # 开发环境
        return Path(__file__).parent.parent


def get_data_dir():
    """
    获取数据存储目录（配置文件、日志等）
    - Windows: %APPDATA%/DNF_Assistant/
    - 开发环境：项目根目录
    
    这样即使 exe 在只读目录也能正常写入配置
    """
    if getattr(sys, 'frozen', False):
        # 打包后：使用用户数据目录
        if sys.platform == 'win32':
            base = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:
            base = os.path.expanduser('~/.config')
        
        data_dir = Path(base) / 'DNF_Assistant'
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    else:
        # 开发环境：项目根目录
        return get_app_dir()


def get_config_path(filename):
    """获取配置文件路径"""
    return get_data_dir() / filename


def get_log_dir():
    """获取日志目录"""
    log_dir = get_data_dir() / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_assets_dir():
    """
    获取资源目录（图片、音频等）
    打包后资源会被嵌入到 exe 中
    """
    if getattr(sys, 'frozen', False):
        # Nuitka 打包后
        return get_app_dir() / 'assets'
    else:
        return get_app_dir() / 'assets'


# 常用路径
APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
LOG_DIR = get_log_dir()
ASSETS_DIR = get_assets_dir()

# 配置文件路径
ROLE_CONFIG_FILE = get_config_path('role_config.json')
GUI_CONFIG_FILE = get_config_path('gui_config.json')
AUTH_LOCAL_FILE = get_config_path('.auth_local')


def init_data_dir():
    """
    初始化数据目录，复制默认配置文件
    首次运行时调用
    """
    if not getattr(sys, 'frozen', False):
        return  # 开发环境不需要
    
    # 检查并复制默认配置
    default_configs = ['role_config.json', 'gui_config.json']
    
    for config_name in default_configs:
        target = get_config_path(config_name)
        if not target.exists():
            # 从 exe 目录复制默认配置
            source = get_app_dir() / config_name
            if source.exists():
                import shutil
                shutil.copy(source, target)
                print(f"已复制默认配置: {config_name}")


if __name__ == '__main__':
    print(f"APP_DIR: {APP_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"LOG_DIR: {LOG_DIR}")
    print(f"ROLE_CONFIG_FILE: {ROLE_CONFIG_FILE}")
    print(f"GUI_CONFIG_FILE: {GUI_CONFIG_FILE}")
