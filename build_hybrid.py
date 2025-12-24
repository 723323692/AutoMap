# -*- coding: utf-8 -*-
"""
混合打包方案：
1. 复制项目到临时目录（避免目录名特殊字符问题）
2. Cython 编译核心代码为 .pyd
3. 模型文件 AES 加密
4. PyInstaller onedir 打包
"""

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
APP_NAME = "DNF_Assistant"
ENTRY_FILE = "gui_app.py"

# 需要用 Cython 编译保护的核心文件
CORE_FILES = [
    "gui_app.py",
    "dnf/stronger/main.py",
    "dnf/stronger/method.py",
    "dnf/stronger/player.py",
    "dnf/stronger/skill_util.py",
    "dnf/stronger/map_util.py",
    "dnf/stronger/object_detect.py",
    "dnf/stronger/path_finder.py",
    "dnf/abyss/main.py",
    "utils/auth.py",
    "utils/login_dialog.py",
    "utils/keyboard_utils.py",
    "utils/mouse_utils.py",
    "utils/window_utils.py",
    "utils/utilities.py",
    "config.py",
    "model_loader.py",
]

ENCRYPTION_KEY = b"YourSecretKey123_ChangeThis!!"


def install_deps():
    print("安装依赖...")
    subprocess.run([sys.executable, "-m", "pip", "install", "cython", "pyinstaller", "pycryptodome"], check=True)


def copy_project_to_temp():
    """复制项目到临时目录"""
    print("\n[0/4] 复制项目到临时目录...")
    temp_base = Path("C:/temp_build")
    temp_base.mkdir(exist_ok=True)
    temp_dir = temp_base / "dnf_project"
    
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    # 复制需要的文件
    dirs_to_copy = ["dnf", "utils", "assets", "weights", "weights_encrypted"]
    files_to_copy = ["gui_app.py", "config.py", "model_loader.py", "role_config.json", "gui_config.json"]
    
    temp_dir.mkdir(parents=True)
    
    for d in dirs_to_copy:
        src = PROJECT_ROOT / d
        if src.exists():
            shutil.copytree(src, temp_dir / d)
    
    for f in files_to_copy:
        src = PROJECT_ROOT / f
        if src.exists():
            shutil.copy2(src, temp_dir / f)
    
    print(f"  复制到: {temp_dir}")
    return temp_dir


def compile_single_file(work_dir, py_file):
    """编译单个文件"""
    src = work_dir / py_file
    if not src.exists():
        return False
    
    src_dir = src.parent
    src_name = src.name
    stem = src.stem
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(work_dir)
    
    setup_content = f'''# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"{work_dir}")
from setuptools import setup
from Cython.Build import cythonize
setup(
    ext_modules=cythonize("{src_name}", language_level="3", quiet=True),
    script_args=["build_ext", "--inplace"]
)
'''
    setup_file = src_dir / "_setup.py"
    setup_file.write_text(setup_content, encoding="utf-8")
    
    try:
        result = subprocess.run(
            [sys.executable, "_setup.py"],
            capture_output=True, text=True, 
            cwd=str(src_dir),
            env=env
        )
        
        # 检查 .pyd 是否生成（可能在深层 build 目录）
        pyd_found = False
        # 搜索所有可能的位置
        for pyd in src_dir.rglob(f"{stem}*.pyd"):
            # 移动到源文件目录（与原 .py 同级）
            dest = src_dir / pyd.name
            if pyd != dest:
                shutil.copy2(pyd, dest)
            pyd_found = True
            print(f"(found: {pyd.name})", end=" ")
            break
        
        # 如果没找到，再检查 build 目录的深层结构
        if not pyd_found:
            build_dir = src_dir / "build"
            if build_dir.exists():
                for pyd in build_dir.rglob(f"{stem}*.pyd"):
                    dest = src_dir / pyd.name
                    shutil.copy2(pyd, dest)
                    pyd_found = True
                    print(f"(found in build: {pyd.name})", end=" ")
                    break
        
        return pyd_found
    except:
        return False
    finally:
        setup_file.unlink(missing_ok=True)


def compile_with_cython(work_dir):
    """Cython 编译核心文件"""
    print("\n[1/4] Cython 编译核心代码...")
    
    compiled = []
    for py_file in CORE_FILES:
        print(f"  编译: {py_file}", end=" ")
        if compile_single_file(work_dir, py_file):
            print("✓")
            compiled.append(py_file)
            # 删除原始 .py 文件，只保留 .pyd
            (work_dir / py_file).unlink(missing_ok=True)
        else:
            print("✗")
    
    # 清理 .c 文件和 build 目录
    for f in work_dir.rglob("*.c"):
        f.unlink(missing_ok=True)
    shutil.rmtree(work_dir / "build", ignore_errors=True)
    
    print(f"  成功编译: {len(compiled)}/{len(CORE_FILES)}")
    return compiled


def encrypt_models(work_dir):
    """加密模型文件"""
    print("\n[2/4] 加密模型文件...")
    
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    import hashlib
    
    key = hashlib.sha256(ENCRYPTION_KEY).digest()
    model_files = ["weights/abyss.pt", "weights/obstacle.pt", "weights/stronger.pt"]
    encrypted_dir = work_dir / "weights_encrypted"
    encrypted_dir.mkdir(exist_ok=True)
    
    for model_path in model_files:
        src = work_dir / model_path
        if not src.exists():
            continue
        print(f"  加密: {model_path}")
        with open(src, "rb") as f:
            data = f.read()
        cipher = AES.new(key, AES.MODE_CBC)
        encrypted = cipher.iv + cipher.encrypt(pad(data, AES.block_size))
        dst = encrypted_dir / (src.name + ".enc")
        with open(dst, "wb") as f:
            f.write(encrypted)


def create_launcher(work_dir):
    """创建启动器"""
    launcher = work_dir / "launcher.py"
    launcher.write_text('''# -*- coding: utf-8 -*-
import sys, os
import traceback

# 获取exe所在目录用于写日志
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
    base = sys._MEIPASS
else:
    exe_dir = os.path.dirname(os.path.abspath(__file__))
    base = exe_dir

log_file = os.path.join(exe_dir, "error.log")

# 全局异常处理
def exception_hook(exc_type, exc_value, exc_tb):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(error_msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(error_msg + "\\n")

sys.excepthook = exception_hook

try:
    sys.path.insert(0, base)
    os.chdir(base)
    import gui_app
    gui_app.main()
except Exception as e:
    error_msg = f"启动错误: {type(e).__name__}: {e}\\n"
    error_msg += traceback.format_exc()
    print(error_msg)
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(error_msg)
    input("按回车键退出...")
''', encoding="utf-8")
    return "launcher.py"


def build_with_pyinstaller(work_dir, compiled_files):
    """PyInstaller 打包"""
    print("\n[3/4] PyInstaller 打包...")
    
    entry = create_launcher(work_dir)
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir", "--windowed",  # 正式发布模式，无控制台窗口
        "--name", APP_NAME,
        "--add-data", "assets;assets",
        "--add-data", "role_config.json;.",
        "--add-data", "gui_config.json;.",
        "--add-data", "weights_encrypted;weights_encrypted",
        "--hidden-import", "cv2",
        "--hidden-import", "torch",
        "--hidden-import", "ultralytics",
        "--hidden-import", "pynput",
        "--hidden-import", "pynput.keyboard",
        "--hidden-import", "pynput.mouse",
        "--hidden-import", "keyboard",
        "--hidden-import", "PyQt5",
        "--hidden-import", "PyQt5.QtWidgets",
        "--hidden-import", "PyQt5.QtCore",
        "--hidden-import", "PyQt5.QtGui",
        "--hidden-import", "skimage",
        "--hidden-import", "skimage.metrics",
        "--hidden-import", "skimage.metrics._structural_similarity",
        "--hidden-import", "pyautogui",
        "--hidden-import", "loguru",
        "--hidden-import", "dxcam",
        "--hidden-import", "comtypes",
        "--hidden-import", "winsound",
        "--hidden-import", "requests",
        "--hidden-import", "numpy",
        "--hidden-import", "scipy",
        "--hidden-import", "scipy.spatial",
        "--hidden-import", "scipy.spatial.distance",
        "--hidden-import", "win32gui",
        "--hidden-import", "win32ui",
        "--hidden-import", "win32con",
        "--hidden-import", "win32api",
        "--hidden-import", "ctypes",
        "--hidden-import", "configparser",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "schedule",
        "--hidden-import", "concurrent.futures",
        "--hidden-import", "queue",
        "--hidden-import", "threading",
        "--hidden-import", "itertools",
        "--hidden-import", "pathlib",
        "--hidden-import", "dataclasses",
        "--hidden-import", "json",
        "--hidden-import", "re",
        "--hidden-import", "math",
        "--hidden-import", "hashlib",
        "--hidden-import", "uuid",
        "--hidden-import", "platform",
        "--hidden-import", "base64",
        "--hidden-import", "tempfile",
        "--hidden-import", "atexit",
        "--hidden-import", "smtplib",
        "--hidden-import", "email",
        "--hidden-import", "email.mime.text",
        "--hidden-import", "email.mime.multipart",
        "--hidden-import", "email.mime.image",
        "--hidden-import", "email.header",
        "--hidden-import", "logging",
        "--hidden-import", "functools",
        "--hidden-import", "pprint",
        "--hidden-import", "Crypto",
        "--hidden-import", "Crypto.Cipher",
        "--hidden-import", "Crypto.Cipher.AES",
        "--hidden-import", "Crypto.Util.Padding",
        "--hidden-import", "collections",
        "--hidden-import", "enum",
        "--hidden-import", "typing",
        "--hidden-import", "traceback",
        "--collect-all", "ultralytics",
        "--noconfirm",
    ]
    
    # 添加 .pyd 文件
    for py_file in compiled_files:
        pyd_dir = (work_dir / py_file).parent
        for pyd in pyd_dir.glob("*.pyd"):
            rel_dir = pyd.parent.relative_to(work_dir)
            cmd.extend(["--add-binary", f"{pyd};{rel_dir}"])
    
    # 添加未编译的 dnf 和 utils 目录
    cmd.extend(["--add-data", "dnf;dnf", "--add-data", "utils;utils"])
    
    icon = work_dir / "assets/img/icon.ico"
    if icon.exists():
        cmd.extend(["--icon", str(icon)])
    
    cmd.append(entry)
    
    subprocess.run(cmd, check=True, cwd=str(work_dir))
    return work_dir / "dist" / APP_NAME


def copy_result_back(result_dir):
    """复制结果回原目录"""
    print("\n[4/4] 复制结果...")
    dest = PROJECT_ROOT / "dist" / APP_NAME
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(result_dir, dest)
    print(f"  输出: {dest}")
    return dest


def main():
    print("=" * 50)
    print("混合打包方案 (Cython + PyInstaller)")
    print("=" * 50)
    
    install_deps()
    work_dir = copy_project_to_temp()
    compiled = compile_with_cython(work_dir)
    encrypt_models(work_dir)
    result_dir = build_with_pyinstaller(work_dir, compiled)
    final_dir = copy_result_back(result_dir)
    
    print("\n" + "=" * 50)
    print(f"打包完成！")
    print(f"运行: {final_dir / (APP_NAME + '.exe')}")
    print("=" * 50)


if __name__ == "__main__":
    main()
