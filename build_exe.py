# -*- coding: utf-8 -*-
"""
PyInstaller 打包脚本
运行: python build_exe.py
"""

import os
import subprocess
import sys

def build():
    # 检查 PyInstaller 是否安装
    try:
        import PyInstaller
        print(f"PyInstaller 版本: {PyInstaller.__version__}")
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 打包命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=DNF脚本",
        "--onedir",            # 打包成目录（对大型库更稳定）
        "--windowed",          # 无控制台窗口
        "--noconfirm",         # 覆盖已有文件
        "--clean",             # 清理临时文件
        # 图标
        "--icon=assets/img/img_gui/favicon.ico",
        # 添加数据文件
        "--add-data=assets;assets",
        "--add-data=weights;weights",
        "--add-data=dnf;dnf",
        "--add-data=utils;utils",
        "--add-data=config.py;.",
        "--add-data=role_config.json;.",
        "--add-data=gui_config.json;.",
        # 隐藏导入
        "--hidden-import=pynput",
        "--hidden-import=pynput.keyboard",
        "--hidden-import=pynput.mouse",
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "--hidden-import=PIL",
        "--hidden-import=PyQt5",
        "--hidden-import=torch",
        "--hidden-import=torchvision",
        "--hidden-import=ultralytics",
        "--hidden-import=ultralytics.nn",
        "--hidden-import=ultralytics.nn.tasks",
        "--hidden-import=ultralytics.engine",
        "--hidden-import=ultralytics.engine.model",
        "--hidden-import=ultralytics.engine.predictor",
        "--hidden-import=ultralytics.engine.results",
        "--hidden-import=ultralytics.models",
        "--hidden-import=ultralytics.models.yolo",
        "--hidden-import=ultralytics.utils",
        "--hidden-import=ultralytics.data",
        "--hidden-import=skimage",
        "--hidden-import=loguru",
        "--hidden-import=keyboard",
        "--hidden-import=dxcam",
        "--hidden-import=win32gui",
        "--hidden-import=win32con",
        "--hidden-import=win32api",
        # 排除不需要的模块（减小体积）
        "--exclude-module=matplotlib",
        "--exclude-module=tkinter",
        "--exclude-module=scipy.spatial.cKDTree",
        # 管理员权限
        "--uac-admin",
        # 入口文件
        "gui_app.py"
    ]
    
    print("开始打包...")
    print(" ".join(cmd))
    print()
    
    subprocess.run(cmd)
    
    print()
    print("=" * 50)
    print("打包完成！")
    print("输出文件: dist/DNF脚本.exe")
    print("=" * 50)

if __name__ == "__main__":
    build()
