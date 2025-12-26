# -*- coding:utf-8 -*-
"""
卡密验证模块 - 网络验证 + 防破解 + AES加密传输版本
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

# ========== 配置（AES加密存储）==========
# 固定种子（不依赖文件路径，避免打包后路径变化导致解密失败）
_CFG_SEED = 'BabyBus2024AuthConfig'

def _get_cfg_key():
    """获取配置解密密钥"""
    return hashlib.sha256(_CFG_SEED.encode()).digest()

def _aes_decrypt_cfg(encrypted_b64):
    """AES解密配置"""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    key = _get_cfg_key()
    data = base64.b64decode(encrypted_b64)
    iv = data[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(data[16:]), AES.block_size)
    return decrypted.decode('utf-8')

# 加密后的配置（使用 generate_keys.py 生成）
_CFG = {
    's': 'OC522dpqJVr0VH30x2ep0yQVdSGaQA+qE4NmmY7JykIfQ+SKrKM1hGFZ9yoPwNh+',
    'k': '4dukJ73Xe5m0eahnxz6h9pTMB1WbacgWGJJhDdEpyXc7wDOesKC82TAP0P8nMqiB',
    'e': 'CFyVszblUHw+s7jjszc7bd1QTr17rOzjPHfszciEf7syUyvHimwxHeQGaufe6IjV',
}

def _load_config():
    """加载配置"""
    return {
        'server': _aes_decrypt_cfg(_CFG['s']),
        'secret': _aes_decrypt_cfg(_CFG['k']),
        'encrypt': _aes_decrypt_cfg(_CFG['e']),
    }

# 延迟加载配置
_config_cache = None
def _get_config():
    global _config_cache
    if _config_cache is None:
        _config_cache = _load_config()
    return _config_cache

# 实际使用时通过函数获取
def _get_server(): return os.environ.get('AUTH_SERVER_URL') or _get_config()['server']
def _get_secret(): return os.environ.get('AUTH_API_SECRET') or _get_config()['secret']
def _get_encrypt_key(): return os.environ.get('AUTH_ENCRYPT_KEY') or _get_config()['encrypt']

REQUEST_TIMEOUT = 10

# 全局验证状态
_auth_state = {
    'verified': False,
    'card_key': None,
    'check_count': 0,
    'last_check': 0
}
_auth_lock = threading.Lock()


# ========== AES加密 ==========
def _get_aes_key():
    """获取AES密钥（32字节）"""
    return hashlib.sha256(_get_encrypt_key().encode()).digest()


def _aes_encrypt(data):
    """AES加密"""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    key = _get_aes_key()
    cipher = AES.new(key, AES.MODE_CBC)
    encrypted = cipher.iv + cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    return base64.b64encode(encrypted).decode('utf-8')


def _aes_decrypt(encrypted_data):
    """AES解密"""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    key = _get_aes_key()
    data = base64.b64decode(encrypted_data)
    iv = data[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(data[16:]), AES.block_size)
    return decrypted.decode('utf-8')


def _encrypt_request_data(data):
    """加密请求数据"""
    json_str = json.dumps(data, ensure_ascii=False)
    encrypted = _aes_encrypt(json_str)
    return {'encrypted': encrypted, 'v': '3'}


def _decrypt_response_data(response_json):
    """解密响应数据"""
    if 'encrypted' in response_json:
        decrypted = _aes_decrypt(response_json['encrypted'])
        if decrypted:
            return json.loads(decrypted)
    return response_json


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
    return hashlib.md5(f"{sorted_data}&secret={_get_secret()}".encode()).hexdigest()


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
            f"{_get_server()}/api/verify",
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
            f"{_get_server()}/api/heartbeat",
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


def start_heartbeat_thread(interval=60):
    """启动心跳检测线程（每1分钟检测一次）"""
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
    查询解绑信息（加密传输）
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
    
    # 加密请求数据
    encrypted_data = _encrypt_request_data(data)
    
    try:
        response = requests.post(
            f"{_get_server()}/api/unbind_info",
            json=encrypted_data,
            timeout=REQUEST_TIMEOUT
        )
        
        result = _decrypt_response_data(response.json())
        if result.get('success'):
            return True, result.get('data', {})
        return False, result.get('message', '查询失败')
        
    except:
        return False, "查询失败"


def unbind_card(card_key):
    """
    用户自助解绑（扣除8小时，加密传输）
    返回: (success, message, expire_info)
    """
    machine_code = get_machine_code()
    if not machine_code:
        return False, "无法获取机器码", None
    
    data = {
        'card_key': card_key.strip().upper(),
        'machine_code': machine_code,
        'timestamp': str(int(datetime.now().timestamp()))
    }
    data['sign'] = _sign_request(data)
    
    # 加密请求数据
    encrypted_data = _encrypt_request_data(data)
    
    try:
        response = requests.post(
            f"{_get_server()}/api/unbind",
            json=encrypted_data,
            timeout=REQUEST_TIMEOUT
        )
        
        result = _decrypt_response_data(response.json())
        if result.get('success'):
            # 清除本地登录信息
            clear_local_auth()
            with _auth_lock:
                _auth_state['verified'] = False
                _auth_state['card_key'] = None
        
        expire_info = result.get('data', None)
        return result.get('success', False), result.get('message', '解绑失败'), expire_info
        
    except requests.exceptions.ConnectionError:
        return False, "无法连接到服务器", None
    except requests.exceptions.Timeout:
        return False, "服务器响应超时", None
    except Exception as e:
        return False, f"解绑出错: {str(e)}", None


# ========== 随机验证点（混淆函数名）==========
import random as _r
import time as _t

# 验证缓存
_vc = {'t': 0, 'r': True, 'n': 0}

def _x7k9m2():
    """验证点A"""
    with _auth_lock:
        if not _auth_state['verified']:
            return False
        if _auth_state['last_check'] > _t.time() + 60:
            return False
    return True

def _p3q8n1():
    """验证点B"""
    return not _check_debugger()

def _w5r2j6():
    """验证点C"""
    return _integrity_check()

def _h4t9k7():
    """验证点D - 网络心跳"""
    global _vc
    now = _t.time()
    if now - _vc['t'] < 300:
        return _vc['r']
    card = get_verified_card()
    if not card:
        _vc['r'] = False
        return False
    try:
        success, _ = heartbeat(card)
        _vc['t'] = now
        _vc['r'] = success
        return success
    except:
        return _vc['r']

def _c2v8b4(silent=True):
    """随机验证入口"""
    global _vc
    _vc['n'] += 1
    if _vc['n'] % 10 != 0:
        return _vc.get('r', True)
    checks = [_x7k9m2, _p3q8n1, _w5r2j6]
    result = _r.choice(checks)()
    if _vc['n'] % 50 == 0:
        result = result and _h4t9k7()
    _vc['r'] = result
    if not result and not silent:
        raise RuntimeError("E01")
    return result

def _d9f5g0():
    """静默验证"""
    return True if _c2v8b4(True) else None

# 导出
runtime_check = _c2v8b4
silent_verify = _d9f5g0


# 模块加载时的检查
if _check_debugger():
    print("[Auth] 警告: 检测到调试环境")
