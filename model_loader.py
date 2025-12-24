# -*- coding: utf-8 -*-
"""
运行时模型解密加载器
打包后自动解密加载模型，开发环境直接加载原始文件
"""
import os
import sys
import tempfile
import hashlib
import atexit
from pathlib import Path

# 加密密钥（必须与打包时一致！）
_KEY = b"YourSecretKey123_ChangeThis!!"

# 缓存已解密的模型路径，避免重复解密
_decrypted_cache = {}
# 临时文件列表，程序退出时清理
_temp_files = []

def _get_key():
    return hashlib.sha256(_KEY).digest()

def _cleanup_temp_files():
    """程序退出时清理临时文件"""
    for f in _temp_files:
        try:
            if os.path.exists(f):
                os.unlink(f)
        except:
            pass

atexit.register(_cleanup_temp_files)

def load_encrypted_model(encrypted_path):
    """解密模型文件"""
    # 检查缓存
    cache_key = str(encrypted_path)
    if cache_key in _decrypted_cache:
        cached_path = _decrypted_cache[cache_key]
        if os.path.exists(cached_path):
            return cached_path
    
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    
    with open(encrypted_path, "rb") as f:
        data = f.read()
    
    iv = data[:16]
    encrypted_data = data[16:]
    
    cipher = AES.new(_get_key(), AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
    
    # 写入临时文件供 YOLO 加载
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pt")
    temp_file.write(decrypted_data)
    temp_file.close()
    
    # 缓存并记录临时文件
    _decrypted_cache[cache_key] = temp_file.name
    _temp_files.append(temp_file.name)
    
    return temp_file.name

def get_model_path(model_name):
    """
    获取模型路径（自动处理加密/未加密）
    
    Args:
        model_name: 模型文件名，如 "stronger.pt", "abyss.pt", "obstacle.pt"
    
    Returns:
        模型文件路径（打包后为解密的临时文件路径）
    """
    # 判断是否为打包环境
    if getattr(sys, "frozen", False):
        # Nuitka 打包后
        if hasattr(sys, "_MEIPASS"):
            base_dir = Path(sys._MEIPASS)
        else:
            base_dir = Path(sys.executable).parent
        
        # 尝试加载加密模型
        encrypted_path = base_dir / "weights_encrypted" / f"{model_name}.enc"
        if encrypted_path.exists():
            return load_encrypted_model(encrypted_path)
        
        # 回退到未加密模型（兼容）
        plain_path = base_dir / "weights" / model_name
        if plain_path.exists():
            return str(plain_path)
    
    # 开发环境：查找项目根目录
    # 支持从子目录运行
    current = Path(__file__).parent
    for _ in range(5):  # 最多向上查找5层
        weights_path = current / "weights" / model_name
        if weights_path.exists():
            return str(weights_path)
        current = current.parent
    
    # 默认返回相对路径
    return f"weights/{model_name}"

def get_stronger_model_path():
    """获取 stronger 模型路径"""
    return get_model_path("stronger.pt")

def get_abyss_model_path():
    """获取 abyss 模型路径"""
    return get_model_path("abyss.pt")

def get_obstacle_model_path():
    """获取 obstacle 模型路径"""
    return get_model_path("obstacle.pt")
