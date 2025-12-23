# -*- coding:utf-8 -*-
"""
卡密验证模块 - 网络验证 + 防破解 + 加密传输版本
"""

import os
import sys
import json
import hashlib
import uuid
import platform
import requests
import base64
import ctypes
import threading
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_AUTH_FILE = os.path.join(PROJECT_ROOT, '.auth_local')

# ========== 配置（混淆处理）==========
_S = lambda s: base64.b64decode(s).decode()
_SERVER = _S('aHR0cDovLzEyMy4yMDcuODMuMTUyOjUwMDA=')  # http://123.207.83.152:5000
_SECRET = _S('QmFieUJ1czIwMjRTZWNyZXRLZXk=')  # BabyBus2024SecretKey
_ENCRYPT_KEY = _S('QmFieUJ1c0VuY3J5cHQyMDI0')  # BabyBusEncrypt2024

AUTH_SERVER_URL = os.environ.get('AUTH_SERVER_URL', _SERVER)
API_SECRET = os.environ.get('AUTH_API_SECRET', _SECRET)
ENCRYPT_KEY = os.environ.get('AUTH_ENCRYPT_KEY', _ENCRYPT_KEY)
REQUEST_TIMEOUT = 10

# 全局验证状态
_auth_state = {
    'verified': False,
    'card_key': None,
    'check_count': 0,
    'last_check': 0
}
_auth_lock = threading.Lock()


def _xor_encrypt(data, key):
    """XOR加密/解密"""
    key_bytes = key.encode('utf-8')
    data_bytes = data.encode('utf-8')
    encrypted = bytes([data_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data_bytes))])
    return base64.b64encode(encrypted).decode('utf-8')


def _xor_decrypt(encrypted_data, key):
    """XOR解密"""
    try:
        key_bytes = key.encode('utf-8')
        data_bytes = base64.b64decode(encrypted_data)
        decrypted = bytes([data_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data_bytes))])
        return decrypted.decode('utf-8')
    except:
        return None


def _encrypt_request_data(data):
    """加密请求数据"""
    json_str = json.dumps(data, ensure_ascii=False)
    encrypted = _xor_encrypt(json_str, ENCRYPT_KEY)
    return {'encrypted': encrypted, 'v': '2'}  # v=2 表示加密版本


def _decrypt_response_data(response_json):
    """解密响应数据"""
    if 'encrypted' in response_json:
        decrypted = _xor_decrypt(response_json['encrypted'], ENCRYPT_KEY)
        if decrypted:
            return json.loads(decrypted)
    return response_json  # 兼容未加密响应


def _check_debugger():
    """检测调试器"""
    try:
        if sys.gettrace() is not None:
            return True
        if platform.system() == 'Windows':
            kernel32 = ctypes.windll.kernel32
            if kernel32.IsDebuggerPresent():
                return True
    except:
        pass
    return False


def _integrity_check():
    """完整性校验"""
    try:
        # 检查关键函数是否被篡改
        import inspect
        source = inspect.getsource(verify_card)
        if 'return True' in source and source.count('return True') > 2:
            return False
    except:
        pass
    return True


def get_machine_code():
    """获取机器码（基于硬件信息生成唯一标识）"""
    try:
        info_parts = []
        
        # MAC地址
        mac = uuid.getnode()
        info_parts.append(str(mac))
        
        # 计算机名
        info_parts.append(platform.node())
        
        # 处理器信息
        info_parts.append(platform.processor())
        
        # 系统信息
        info_parts.append(platform.system() + platform.release())
        
        # 磁盘序列号（Windows）- 隐藏命令窗口
        if platform.system() == 'Windows':
            try:
                import subprocess
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                result = subprocess.run(
                    ['wmic', 'diskdrive', 'get', 'serialnumber'],
                    capture_output=True, text=True, timeout=5,
                    startupinfo=startupinfo
                )
                serial = result.stdout.strip().split('\n')[-1].strip()
                if serial:
                    info_parts.append(serial)
            except:
                pass
        
        # 组合并哈希
        combined = '|'.join(info_parts)
        hash_obj = hashlib.sha256(combined.encode('utf-8'))
        machine_code = hash_obj.hexdigest()[:16].upper()
        
        # 格式化
        formatted = '-'.join([machine_code[i:i+4] for i in range(0, 16, 4)])
        return formatted
    except:
        return None


def _sign_request(data):
    """生成请求签名（内部使用）"""
    sorted_data = '&'.join(f"{k}={v}" for k, v in sorted(data.items()) if k != 'sign')
    return hashlib.md5(f"{sorted_data}&secret={API_SECRET}".encode()).hexdigest()


def _encrypt_local_data(data):
    """加密本地数据"""
    machine = get_machine_code() or 'default'
    key = hashlib.md5(machine.encode()).hexdigest()
    json_str = json.dumps(data)
    encrypted = base64.b64encode(json_str.encode()).decode()
    checksum = hashlib.md5(f"{encrypted}{key}".encode()).hexdigest()[:8]
    return f"{encrypted}.{checksum}"


def _decrypt_local_data(encrypted_str):
    """解密本地数据"""
    try:
        machine = get_machine_code() or 'default'
        key = hashlib.md5(machine.encode()).hexdigest()
        parts = encrypted_str.rsplit('.', 1)
        if len(parts) != 2:
            return None
        encrypted, checksum = parts
        expected_checksum = hashlib.md5(f"{encrypted}{key}".encode()).hexdigest()[:8]
        if checksum != expected_checksum:
            return None
        json_str = base64.b64decode(encrypted).decode()
        return json.loads(json_str)
    except:
        return None


def load_local_auth():
    """加载本地保存的登录信息"""
    if os.path.exists(LOCAL_AUTH_FILE):
        try:
            with open(LOCAL_AUTH_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return _decrypt_local_data(content)
        except:
            pass
    return None


def save_local_auth(card_key, expire_info=None):
    """保存登录信息到本地（加密）"""
    data = {
        'card_key': card_key,
        'machine_code': get_machine_code(),
        'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expire_info': expire_info,
        '_t': int(datetime.now().timestamp())
    }
    encrypted = _encrypt_local_data(data)
    with open(LOCAL_AUTH_FILE, 'w', encoding='utf-8') as f:
        f.write(encrypted)


def clear_local_auth():
    """清除本地登录信息"""
    if os.path.exists(LOCAL_AUTH_FILE):
        os.remove(LOCAL_AUTH_FILE)


def _calc_checksum(data, salt='BabyBusCard2024'):
    """计算校验码（4位）"""
    hash_str = hashlib.md5(f"{data}{salt}".encode()).hexdigest().upper()
    return hash_str[0] + hash_str[7] + hash_str[15] + hash_str[31]


def verify_card_format(card_key):
    """验证卡密格式是否正确（本地校验）"""
    if not card_key or len(card_key) != 34:
        return False
    
    prefix = card_key[:2]
    valid_prefixes = ['TK', 'ZK', 'YK', 'JK', 'NK', 'SK', 'YJ']
    if prefix not in valid_prefixes:
        return False
    
    main_part = card_key[:30]
    checksum = card_key[30:]
    expected = _calc_checksum(main_part)
    
    return checksum == expected


def verify_card(card_key):
    """
    验证卡密（网络验证 + 加密传输）
    返回: (success, message, expire_info)
    """
    global _auth_state
    
    # 调试器检测
    if _check_debugger():
        return False, "检测到调试环境", None
    
    # 完整性校验
    if not _integrity_check():
        return False, "程序完整性校验失败", None
    
    if not card_key or len(card_key.strip()) == 0:
        return False, "请输入卡密", None
    
    card_key = card_key.strip().upper()
    
    # 本地格式校验（快速过滤无效卡密）
    if not verify_card_format(card_key):
        return False, "卡密格式不正确", None
    
    machine_code = get_machine_code()
    
    if not machine_code:
        return False, "无法获取机器码", None
    
    # 构建请求数据
    data = {
        'card_key': card_key,
        'machine_code': machine_code,
        'timestamp': str(int(datetime.now().timestamp()))
    }
    data['sign'] = _sign_request(data)
    
    # 加密请求数据
    encrypted_data = _encrypt_request_data(data)
    
    try:
        response = requests.post(
            f"{AUTH_SERVER_URL}/api/verify",
            json=encrypted_data,
            timeout=REQUEST_TIMEOUT
        )
        
        result = _decrypt_response_data(response.json())
        
        if result.get('success'):
            expire_info = result.get('data', {})
            # 更新验证状态
            with _auth_lock:
                _auth_state['verified'] = True
                _auth_state['card_key'] = card_key
                _auth_state['last_check'] = int(datetime.now().timestamp())
            # 保存本地登录信息
            save_local_auth(card_key, expire_info)
            return True, "验证成功", expire_info
        else:
            with _auth_lock:
                _auth_state['verified'] = False
            return False, result.get('message', '验证失败'), None
            
    except requests.exceptions.ConnectionError:
        return False, "连接服务器失败", None
    except requests.exceptions.Timeout:
        return False, "服务器响应超时", None
    except Exception as e:
        return False, f"验证出错: {str(e)}", None


def auto_login():
    """自动登录"""
    # 调试器检测
    if _check_debugger():
        return False, "检测到调试环境", None
    
    local_auth = load_local_auth()
    if not local_auth:
        return False, "未找到本地登录信息", None
    
    card_key = local_auth.get('card_key')
    saved_machine = local_auth.get('machine_code')
    current_machine = get_machine_code()
    
    if saved_machine != current_machine:
        clear_local_auth()
        return False, "机器码不匹配，请重新登录", None
    
    return verify_card(card_key)


def is_verified():
    """检查是否已验证（供其他模块调用）"""
    with _auth_lock:
        if not _auth_state['verified']:
            return False
        # 检查是否超过30分钟未验证
        if datetime.now().timestamp() - _auth_state['last_check'] > 1800:
            return False
        return True


def get_verified_card():
    """获取已验证的卡密"""
    with _auth_lock:
        if _auth_state['verified']:
            return _auth_state['card_key']
    return None


def heartbeat(card_key=None):
    """心跳检测（加密传输）"""
    global _auth_state
    
    if card_key is None:
        card_key = get_verified_card()
    
    if not card_key:
        return False, "未登录"
    
    machine_code = get_machine_code()
    if not machine_code:
        return False, "无法获取机器码"
    
    data = {
        'card_key': card_key.strip().upper(),
        'machine_code': machine_code,
        'timestamp': str(int(datetime.now().timestamp()))
    }
    data['sign'] = _sign_request(data)
    
    # 加密请求
    encrypted_data = _encrypt_request_data(data)
    
    try:
        response = requests.post(
            f"{AUTH_SERVER_URL}/api/heartbeat",
            json=encrypted_data,
            timeout=REQUEST_TIMEOUT
        )
        
        result = _decrypt_response_data(response.json())
        success = result.get('success', False)
        
        with _auth_lock:
            if success:
                _auth_state['last_check'] = int(datetime.now().timestamp())
            else:
                _auth_state['verified'] = False
        
        return success, result.get('message', '')
        
    except:
        return False, "心跳检测失败"


def start_heartbeat_thread(interval=300):
    """启动心跳检测线程（每5分钟检测一次）"""
    import time
    
    def _heartbeat_loop():
        while True:
            time.sleep(interval)
            if _auth_state['verified']:
                success, msg = heartbeat()
                if not success:
                    print(f"[Auth] 心跳检测失败: {msg}")
    
    t = threading.Thread(target=_heartbeat_loop, daemon=True)
    t.start()
    return t


def get_card_expire_info(card_key):
    """获取卡密到期信息"""
    local_auth = load_local_auth()
    if local_auth and local_auth.get('card_key', '').upper() == card_key.upper():
        return local_auth.get('expire_info')
    return None


def get_unbind_info(card_key):
    """
    查询解绑信息
    返回: (success, data) 或 (False, message)
    """
    machine_code = get_machine_code()
    if not machine_code:
        return False, "无法获取机器码"
    
    data = {
        'card_key': card_key.strip().upper(),
        'machine_code': machine_code,
        'timestamp': str(int(datetime.now().timestamp()))
    }
    data['sign'] = _sign_request(data)
    
    try:
        response = requests.post(
            f"{AUTH_SERVER_URL}/api/unbind_info",
            json=data,
            timeout=REQUEST_TIMEOUT
        )
        
        result = response.json()
        if result.get('success'):
            return True, result.get('data', {})
        return False, result.get('message', '查询失败')
        
    except:
        return False, "查询失败"


def unbind_card(card_key):
    """
    用户自助解绑（扣除8小时）
    返回: (success, message)
    """
    machine_code = get_machine_code()
    if not machine_code:
        return False, "无法获取机器码"
    
    data = {
        'card_key': card_key.strip().upper(),
        'machine_code': machine_code,
        'timestamp': str(int(datetime.now().timestamp()))
    }
    data['sign'] = _sign_request(data)
    
    try:
        response = requests.post(
            f"{AUTH_SERVER_URL}/api/unbind",
            json=data,
            timeout=REQUEST_TIMEOUT
        )
        
        result = response.json()
        if result.get('success'):
            # 清除本地登录信息
            clear_local_auth()
            with _auth_lock:
                _auth_state['verified'] = False
                _auth_state['card_key'] = None
        
        return result.get('success', False), result.get('message', '解绑失败')
        
    except requests.exceptions.ConnectionError:
        return False, "无法连接到服务器"
    except requests.exceptions.Timeout:
        return False, "服务器响应超时"
    except Exception as e:
        return False, f"解绑出错: {str(e)}"


# 模块加载时的检查
if _check_debugger():
    print("[Auth] 警告: 检测到调试环境")
