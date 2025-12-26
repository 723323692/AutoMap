# -*- coding:utf-8 -*-
"""
卡密验证服务端 V2 - 增强安全版本
改进：
1. 多进程支持（Gunicorn）
2. 文件日志 + 请求日志
3. SQL注入防护增强
4. AES加密替代XOR
"""

import os
import re
import hashlib
import sqlite3
import time
import json
import base64
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from functools import wraps
from collections import defaultdict
from flask import Flask, request, jsonify, g

app = Flask(__name__)

# ========== 日志配置 ==========
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, 'server.log')

# 创建日志处理器
file_handler = RotatingFileHandler(
    LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# 配置应用日志
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# 请求日志
request_logger = logging.getLogger('requests')
request_logger.addHandler(file_handler)
request_logger.setLevel(logging.INFO)

# ========== 配置 ==========
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(DATA_DIR, 'cards.db')

# 加载 .env 文件（如果存在）
ENV_FILE = os.path.join(DATA_DIR, '.env')
if os.path.exists(ENV_FILE):
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

# 密钥配置（必须通过环境变量或 .env 文件设置）
API_SECRET = os.environ.get('AUTH_API_SECRET')
ENCRYPT_KEY = os.environ.get('AUTH_ENCRYPT_KEY')

if not API_SECRET or not ENCRYPT_KEY:
    raise RuntimeError('请在 .env 文件或环境变量中设置 AUTH_API_SECRET 和 AUTH_ENCRYPT_KEY')

# ========== AES加密 ==========
def get_aes_key():
    """获取AES密钥（32字节）"""
    return hashlib.sha256(ENCRYPT_KEY.encode()).digest()

def aes_encrypt(data):
    """AES加密"""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    key = get_aes_key()
    cipher = AES.new(key, AES.MODE_CBC)
    encrypted = cipher.iv + cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    return base64.b64encode(encrypted).decode('utf-8')

def aes_decrypt(encrypted_data):
    """AES解密"""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    key = get_aes_key()
    data = base64.b64decode(encrypted_data)
    iv = data[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(data[16:]), AES.block_size)
    return decrypted.decode('utf-8')

def decrypt_request():
    """解密请求数据"""
    data = request.get_json() or {}
    if 'encrypted' in data:
        try:
            decrypted = aes_decrypt(data['encrypted'])
            if decrypted:
                return json.loads(decrypted)
        except:
            pass
    return data

def encrypt_response(data):
    """加密响应数据"""
    json_str = json.dumps(data, ensure_ascii=False)
    encrypted = aes_encrypt(json_str)
    return jsonify({'encrypted': encrypted, 'v': '3'})

# ========== 请求日志中间件 ==========
@app.before_request
def log_request():
    """记录所有请求"""
    ip = get_client_ip()
    request_logger.info(f"REQUEST | {ip} | {request.method} {request.path} | {request.get_data(as_text=True)[:500]}")

@app.after_request
def log_response(response):
    """记录响应"""
    ip = get_client_ip()
    request_logger.info(f"RESPONSE | {ip} | {response.status_code}")
    return response

# ========== 安全防护配置 ==========
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 30
VERIFY_RATE_LIMIT = 5
BLOCK_DURATION = 300
MAX_FAILED_ATTEMPTS = 10
TIMESTAMP_TOLERANCE = 300

request_counts = defaultdict(list)
failed_attempts = defaultdict(int)
blocked_ips = {}

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def is_ip_blocked(ip):
    if ip in blocked_ips:
        if time.time() < blocked_ips[ip]:
            return True
        else:
            del blocked_ips[ip]
            failed_attempts[ip] = 0
    return False

def block_ip(ip):
    blocked_ips[ip] = time.time() + BLOCK_DURATION
    app.logger.warning(f"IP blocked: {ip}")

def check_rate_limit(ip, limit=RATE_LIMIT_MAX_REQUESTS):
    now = time.time()
    request_counts[ip] = [t for t in request_counts[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(request_counts[ip]) >= limit:
        return False
    request_counts[ip].append(now)
    return True

def record_failed_attempt(ip):
    failed_attempts[ip] += 1
    app.logger.warning(f"Failed attempt from {ip}, count: {failed_attempts[ip]}")
    if failed_attempts[ip] >= MAX_FAILED_ATTEMPTS:
        block_ip(ip)
        return True
    return False

def security_check(verify_endpoint=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ip = get_client_ip()
            if is_ip_blocked(ip):
                app.logger.warning(f"Blocked IP tried to access: {ip}")
                return jsonify({'success': False, 'message': '请求过于频繁，请稍后再试'}), 429
            limit = VERIFY_RATE_LIMIT if verify_endpoint else RATE_LIMIT_MAX_REQUESTS
            if not check_rate_limit(ip, limit):
                return jsonify({'success': False, 'message': '请求过于频繁'}), 429
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ========== 数据库 ==========
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            card_key TEXT PRIMARY KEY,
            expire_date TEXT,
            expire_days INTEGER,
            machine_code TEXT,
            bind_time TEXT,
            last_use TEXT,
            last_ip TEXT,
            create_time TEXT,
            remark TEXT,
            disabled INTEGER DEFAULT 0,
            unbind_count INTEGER DEFAULT 0,
            max_unbind_count INTEGER DEFAULT 3,
            total_deducted_hours INTEGER DEFAULT 0
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_key TEXT,
            ip TEXT,
            action TEXT,
            result TEXT,
            message TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    app.logger.info("Database initialized")

def log_access(card_key, ip, action, result, message=''):
    try:
        db = get_db()
        db.execute('''
            INSERT INTO access_logs (card_key, ip, action, result, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (card_key, ip, action, result, message, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        db.commit()
    except Exception as e:
        app.logger.error(f"Failed to log access: {e}")

# ========== 签名验证 ==========
def sign_request(data, secret):
    sorted_data = '&'.join(f"{k}={v}" for k, v in sorted(data.items()) if k != 'sign')
    return hashlib.md5(f"{sorted_data}&secret={secret}".encode()).hexdigest()

def verify_sign(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ip = get_client_ip()
        data = decrypt_request()
        g.decrypted_data = data
        
        timestamp = data.get('timestamp', '')
        if timestamp:
            try:
                req_time = int(timestamp)
                if abs(time.time() - req_time) > TIMESTAMP_TOLERANCE:
                    log_access(data.get('card_key', ''), ip, 'verify', 'fail', '时间戳过期')
                    return encrypt_response({'success': False, 'message': '请求已过期'})
            except:
                pass
        
        client_sign = data.get('sign', '')
        server_sign = sign_request(data, API_SECRET)
        if client_sign != server_sign:
            record_failed_attempt(ip)
            log_access(data.get('card_key', ''), ip, 'verify', 'fail', '签名错误')
            return encrypt_response({'success': False, 'message': '签名验证失败'})
        
        return func(*args, **kwargs)
    return wrapper

def row_to_dict(row):
    if row is None:
        return None
    return {
        'card_key': row['card_key'],
        'expire_date': row['expire_date'],
        'expire_days': row['expire_days'],
        'machine_code': row['machine_code'],
        'bind_time': row['bind_time'],
        'last_use': row['last_use'],
        'create_time': row['create_time'],
        'remark': row['remark'],
        'disabled': bool(row['disabled']),
        'unbind_count': row['unbind_count'] or 0,
        'max_unbind_count': row['max_unbind_count'] if row['max_unbind_count'] is not None else 3,
        'total_deducted_hours': row['total_deducted_hours'] or 0
    }


# ========== 输入验证函数 ==========
def _validate_card_key(card_key):
    """验证卡密格式（只允许字母数字）"""
    if not card_key or len(card_key) > 50:
        return False
    return bool(re.match(r'^[A-Z0-9]+$', card_key))


def _validate_machine_code(machine_code):
    """验证机器码格式（只允许字母数字和连字符）"""
    if not machine_code or len(machine_code) > 50:
        return False
    return bool(re.match(r'^[A-Z0-9\-]+$', machine_code, re.IGNORECASE))


# 解绑频率限制（每个IP每分钟最多3次）
unbind_rate_limit = defaultdict(list)


def _check_unbind_rate_limit(ip):
    """检查解绑频率限制"""
    now = datetime.now().timestamp()
    # 清理1分钟前的记录
    unbind_rate_limit[ip] = [t for t in unbind_rate_limit[ip] if now - t < 60]
    if len(unbind_rate_limit[ip]) >= 3:
        return False
    unbind_rate_limit[ip].append(now)
    return True


# ========== API接口 ==========
@app.route('/api/verify', methods=['POST'])
@security_check(verify_endpoint=True)
@verify_sign
def verify_card():
    """验证卡密"""
    ip = get_client_ip()
    data = g.decrypted_data
    card_key = data.get('card_key', '').strip().upper()
    machine_code = data.get('machine_code', '').strip()
    
    if not card_key or not machine_code:
        return encrypt_response({'success': False, 'message': '参数不完整'})
    
    # 输入验证
    if not _validate_card_key(card_key):
        app.logger.warning(f"Invalid card_key format from {ip}: {card_key[:20]}")
        return encrypt_response({'success': False, 'message': '卡密格式无效'})
    
    if not _validate_machine_code(machine_code):
        app.logger.warning(f"Invalid machine_code format from {ip}")
        return encrypt_response({'success': False, 'message': '机器码格式无效'})
    
    db = get_db()
    row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    
    if not row:
        record_failed_attempt(ip)
        log_access(card_key, ip, 'verify', 'fail', '卡密不存在')
        return encrypt_response({'success': False, 'message': '卡密不正确'})
    
    if row['disabled']:
        log_access(card_key, ip, 'verify', 'fail', '卡密已禁用')
        return encrypt_response({'success': False, 'message': '该卡密已被禁用'})
    
    expire_date = row['expire_date']
    if expire_date:
        if ' ' in expire_date:
            expire_dt = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
        else:
            expire_dt = datetime.strptime(expire_date, '%Y-%m-%d')
            expire_dt = expire_dt.replace(hour=23, minute=59, second=59)
        if datetime.now() > expire_dt:
            log_access(card_key, ip, 'verify', 'fail', '卡密已过期')
            return encrypt_response({'success': False, 'message': f'卡密已过期 ({expire_date})'})
    
    bound_machine = row['machine_code']
    if bound_machine:
        if bound_machine != machine_code:
            record_failed_attempt(ip)
            log_access(card_key, ip, 'verify', 'fail', '机器码不匹配')
            return encrypt_response({'success': False, 'message': '该卡密已绑定其他设备'})
    else:
        expire_days = row['expire_days']
        expire_date = row['expire_date']
        if expire_days and not expire_date:
            from datetime import timedelta
            expire_date = (datetime.now() + timedelta(days=expire_days)).strftime('%Y-%m-%d %H:%M:%S')
            db.execute('UPDATE cards SET machine_code = ?, bind_time = ?, expire_date = ? WHERE card_key = ?',
                       (machine_code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), expire_date, card_key))
        else:
            db.execute('UPDATE cards SET machine_code = ?, bind_time = ? WHERE card_key = ?',
                       (machine_code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), card_key))
        row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
        expire_date = row['expire_date']
    
    db.execute('UPDATE cards SET last_use = ?, last_ip = ? WHERE card_key = ?',
               (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip, card_key))
    db.commit()
    
    failed_attempts[ip] = 0
    
    days_left = hours_left = minutes_left = seconds_left = -1
    expire_datetime = None
    if expire_date:
        if ' ' in expire_date:
            expire_dt = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
        else:
            expire_dt = datetime.strptime(expire_date, '%Y-%m-%d')
            expire_dt = expire_dt.replace(hour=23, minute=59, second=59)
        
        expire_datetime = expire_dt.strftime('%Y-%m-%d %H:%M:%S')
        delta = expire_dt - datetime.now()
        total_seconds = max(0, delta.total_seconds())
        days_left = int(total_seconds // 86400)
        hours_left = int((total_seconds % 86400) // 3600)
        minutes_left = int((total_seconds % 3600) // 60)
        seconds_left = int(total_seconds % 60)
    
    log_access(card_key, ip, 'verify', 'success', '')
    app.logger.info(f"Card verified: {card_key} from {ip}")
    
    return encrypt_response({
        'success': True,
        'message': '验证成功',
        'data': {
            'expire_date': expire_date or '永久',
            'expire_datetime': expire_datetime or '永久',
            'days_left': days_left,
            'hours_left': hours_left,
            'minutes_left': minutes_left,
            'seconds_left': seconds_left,
            'remark': row['remark'] or ''
        }
    })

@app.route('/api/heartbeat', methods=['POST'])
@security_check(verify_endpoint=False)
@verify_sign
def heartbeat():
    """心跳检测"""
    ip = get_client_ip()
    data = g.decrypted_data
    card_key = data.get('card_key', '').strip().upper()
    machine_code = data.get('machine_code', '').strip()
    
    if not card_key or not machine_code:
        return jsonify({'success': False, 'message': '参数不完整'})
    
    # 输入验证
    if not _validate_card_key(card_key):
        app.logger.warning(f"Invalid card_key format in heartbeat from {ip}")
        return jsonify({'success': False, 'message': '卡密格式无效'})
    
    if not _validate_machine_code(machine_code):
        app.logger.warning(f"Invalid machine_code format in heartbeat from {ip}")
        return jsonify({'success': False, 'message': '机器码格式无效'})
    
    db = get_db()
    row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    
    if not row:
        return jsonify({'success': False, 'message': '卡密不正确'})
    
    if row['disabled']:
        return jsonify({'success': False, 'message': '卡密已被禁用'})
    
    expire_date = row['expire_date']
    if expire_date:
        if ' ' in expire_date:
            expire_dt = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
        else:
            expire_dt = datetime.strptime(expire_date, '%Y-%m-%d')
            expire_dt = expire_dt.replace(hour=23, minute=59, second=59)
        if datetime.now() > expire_dt:
            return jsonify({'success': False, 'message': '卡密已过期'})
    
    if row['machine_code'] and row['machine_code'] != machine_code:
        return jsonify({'success': False, 'message': '机器码不匹配'})
    
    return jsonify({'success': True, 'message': 'OK'})


# ========== 用户解绑接口 ==========

@app.route('/api/unbind_info', methods=['POST'])
@security_check(verify_endpoint=True)
@verify_sign
def get_unbind_info():
    """查询解绑信息"""
    ip = get_client_ip()
    
    # 解绑专用频率限制
    if not _check_unbind_rate_limit(ip):
        app.logger.warning(f"Unbind info rate limit exceeded from {ip}")
        return encrypt_response({'success': False, 'message': '请求过于频繁，请稍后再试'})
    
    # 使用解密后的数据
    data = g.decrypted_data
    
    card_key = data.get('card_key', '').strip().upper()
    machine_code = data.get('machine_code', '').strip()
    
    # 参数验证
    if not card_key or not machine_code:
        return encrypt_response({'success': False, 'message': '参数不完整'})
    
    if not _validate_card_key(card_key):
        record_failed_attempt(ip)
        app.logger.warning(f"Invalid card_key format from {ip}: {card_key[:20]}")
        return encrypt_response({'success': False, 'message': '卡密格式无效'})
    
    if not _validate_machine_code(machine_code):
        record_failed_attempt(ip)
        app.logger.warning(f"Invalid machine_code format from {ip}")
        return encrypt_response({'success': False, 'message': '机器码格式无效'})
    
    db = get_db()
    row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    
    if not row:
        record_failed_attempt(ip)
        log_access(card_key, ip, 'unbind_info', 'fail', '卡密不存在')
        return encrypt_response({'success': False, 'message': '卡密不存在'})
    
    unbind_count = row['unbind_count'] or 0
    max_unbind_count = row['max_unbind_count'] if row['max_unbind_count'] is not None else 3
    remaining = max(0, max_unbind_count - unbind_count)
    is_bound = bool(row['machine_code'])
    
    log_access(card_key, ip, 'unbind_info', 'success', '')
    
    return encrypt_response({
        'success': True,
        'data': {
            'remaining': remaining,
            'deduct_hours': 8,
            'is_bound': is_bound,
            'unbind_count': unbind_count,
            'max_unbind_count': max_unbind_count
        }
    })


@app.route('/api/unbind', methods=['POST'])
@security_check(verify_endpoint=True)
@verify_sign
def user_unbind():
    """用户自助解绑（扣除8小时）"""
    ip = get_client_ip()
    
    # 解绑专用频率限制
    if not _check_unbind_rate_limit(ip):
        app.logger.warning(f"Unbind rate limit exceeded from {ip}")
        return encrypt_response({'success': False, 'message': '请求过于频繁，请稍后再试'})
    
    # 使用解密后的数据
    data = g.decrypted_data
    
    card_key = data.get('card_key', '').strip().upper()
    machine_code = data.get('machine_code', '').strip()
    
    # 参数验证
    if not card_key or not machine_code:
        return encrypt_response({'success': False, 'message': '参数不完整'})
    
    if not _validate_card_key(card_key):
        record_failed_attempt(ip)
        app.logger.warning(f"Invalid card_key format from {ip}: {card_key[:20]}")
        return encrypt_response({'success': False, 'message': '卡密格式无效'})
    
    if not _validate_machine_code(machine_code):
        record_failed_attempt(ip)
        app.logger.warning(f"Invalid machine_code format from {ip}")
        return encrypt_response({'success': False, 'message': '机器码格式无效'})
    
    db = get_db()
    row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    
    if not row:
        record_failed_attempt(ip)
        log_access(card_key, ip, 'unbind', 'fail', '卡密不存在')
        return encrypt_response({'success': False, 'message': '卡密不存在'})
    
    if not row['machine_code']:
        return encrypt_response({'success': False, 'message': '该卡密未绑定设备'})
    
    unbind_count = row['unbind_count'] or 0
    max_unbind_count = row['max_unbind_count'] if row['max_unbind_count'] is not None else 3
    
    if unbind_count >= max_unbind_count:
        log_access(card_key, ip, 'unbind', 'fail', '解绑次数已用完')
        return encrypt_response({'success': False, 'message': '解绑次数已用完'})
    
    # 扣除8小时
    from datetime import timedelta
    deduct_hours = 8
    expire_date = row['expire_date']
    new_expire_date = None
    
    if expire_date:
        if ' ' in expire_date:
            expire_dt = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
        else:
            expire_dt = datetime.strptime(expire_date, '%Y-%m-%d')
            expire_dt = expire_dt.replace(hour=23, minute=59, second=59)
        
        new_expire_dt = expire_dt - timedelta(hours=deduct_hours)
        new_expire_date = new_expire_dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查扣除后是否已过期
        if new_expire_dt < datetime.now():
            log_access(card_key, ip, 'unbind', 'fail', '剩余时间不足')
            return encrypt_response({'success': False, 'message': '剩余时间不足，无法解绑'})
    
    # 更新数据库 - 只清除机器码，保留绑定时间
    total_deducted = (row['total_deducted_hours'] or 0) + deduct_hours
    
    if new_expire_date:
        db.execute('''UPDATE cards SET 
            machine_code = NULL, 
            unbind_count = ?, 
            total_deducted_hours = ?,
            expire_date = ?
            WHERE card_key = ?''', 
            (unbind_count + 1, total_deducted, new_expire_date, card_key))
    else:
        db.execute('''UPDATE cards SET 
            machine_code = NULL, 
            unbind_count = ?, 
            total_deducted_hours = ?
            WHERE card_key = ?''', 
            (unbind_count + 1, total_deducted, card_key))
    
    db.commit()
    
    # 计算剩余时间
    days_left = hours_left = minutes_left = seconds_left = -1
    expire_datetime = None
    
    if new_expire_date:
        new_expire_dt = datetime.strptime(new_expire_date, '%Y-%m-%d %H:%M:%S')
        expire_datetime = new_expire_date
        delta = new_expire_dt - datetime.now()
        total_seconds = max(0, delta.total_seconds())
        days_left = int(total_seconds // 86400)
        hours_left = int((total_seconds % 86400) // 3600)
        minutes_left = int((total_seconds % 3600) // 60)
        seconds_left = int(total_seconds % 60)
    
    log_access(card_key, ip, 'unbind', 'success', f'deducted {deduct_hours}h')
    app.logger.info(f"Card unbound by user: {card_key} from {ip}, deducted {deduct_hours}h")
    
    return encrypt_response({
        'success': True,
        'message': f'解绑成功，已扣除{deduct_hours}小时',
        'data': {
            'expire_date': new_expire_date or '永久',
            'expire_datetime': expire_datetime or '永久',
            'days_left': days_left,
            'hours_left': hours_left,
            'minutes_left': minutes_left,
            'seconds_left': seconds_left,
            'remaining_unbind': max_unbind_count - unbind_count - 1
        }
    })


# ========== 管理接口 ==========
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        admin_key = request.headers.get('X-Admin-Key', '')
        if admin_key != API_SECRET:
            app.logger.warning(f"Unauthorized admin access attempt from {get_client_ip()}")
            return jsonify({'success': False, 'message': '无权限'}), 403
        return func(*args, **kwargs)
    return wrapper

@app.route('/api/admin/cards', methods=['GET'])
@admin_required
def list_cards():
    db = get_db()
    rows = db.execute('SELECT * FROM cards ORDER BY create_time DESC').fetchall()
    cards = {row['card_key']: row_to_dict(row) for row in rows}
    return jsonify({'success': True, 'data': cards})

@app.route('/api/admin/card', methods=['POST'])
@admin_required
def create_card():
    data = request.get_json()
    card_key = data.get('card_key', '').strip().upper()
    expire_days = data.get('expire_days')
    remark = data.get('remark', '')
    
    if not card_key:
        return jsonify({'success': False, 'message': '卡密不能为空'})
    
    db = get_db()
    existing = db.execute('SELECT 1 FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    if existing:
        return jsonify({'success': False, 'message': '卡密已存在'})
    
    db.execute('''
        INSERT INTO cards (card_key, expire_days, create_time, remark, disabled)
        VALUES (?, ?, ?, ?, 0)
    ''', (card_key, expire_days, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), remark))
    db.commit()
    
    app.logger.info(f"Card created: {card_key}")
    return jsonify({'success': True, 'message': '创建成功'})

@app.route('/api/admin/card/<card_key>', methods=['DELETE'])
@admin_required
def delete_card(card_key):
    card_key = card_key.upper()
    db = get_db()
    result = db.execute('DELETE FROM cards WHERE card_key = ?', (card_key,))
    db.commit()
    
    if result.rowcount > 0:
        app.logger.info(f"Card deleted: {card_key}")
        return jsonify({'success': True, 'message': '删除成功'})
    return jsonify({'success': False, 'message': '卡密不存在'})

@app.route('/api/admin/card/<card_key>/toggle', methods=['POST'])
@admin_required
def toggle_card(card_key):
    card_key = card_key.upper()
    db = get_db()
    row = db.execute('SELECT disabled FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    
    if row:
        new_status = 0 if row['disabled'] else 1
        db.execute('UPDATE cards SET disabled = ? WHERE card_key = ?', (new_status, card_key))
        db.commit()
        status = '禁用' if new_status else '启用'
        app.logger.info(f"Card {card_key} {status}")
        return jsonify({'success': True, 'message': f'已{status}'})
    
    return jsonify({'success': False, 'message': '卡密不存在'})

@app.route('/api/admin/card/<card_key>/unbind', methods=['POST'])
@admin_required
def unbind_card(card_key):
    card_key = card_key.upper()
    db = get_db()
    # 只清除机器码，保留绑定时间
    result = db.execute('UPDATE cards SET machine_code = NULL WHERE card_key = ?', (card_key,))
    db.commit()
    
    if result.rowcount > 0:
        app.logger.info(f"Card unbound: {card_key}")
        return jsonify({'success': True, 'message': '解绑成功'})
    return jsonify({'success': False, 'message': '卡密不存在'})

@app.route('/api/admin/card/<card_key>/update', methods=['POST'])
@admin_required
def update_card(card_key):
    card_key = card_key.upper()
    data = request.get_json()
    
    db = get_db()
    row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    if not row:
        return jsonify({'success': False, 'message': '卡密不存在'})
    
    # 白名单字段，防止SQL注入
    allowed_fields = ['unbind_count', 'max_unbind_count', 'expire_date', 'expire_days', 
                      'remark', 'disabled', 'machine_code', 'bind_time']
    
    updates = []
    params = []
    
    for field in allowed_fields:
        if field in data:
            updates.append(f'{field} = ?')
            params.append(data[field])
    
    if not updates:
        return jsonify({'success': False, 'message': '没有要更新的字段'})
    
    params.append(card_key)
    sql = f"UPDATE cards SET {', '.join(updates)} WHERE card_key = ?"
    db.execute(sql, params)
    db.commit()
    
    app.logger.info(f"Card updated: {card_key}")
    return jsonify({'success': True, 'message': '更新成功'})

# 移除危险的 /api/admin/sql 接口，改用安全的搜索接口
@app.route('/api/admin/cards/search', methods=['GET'])
@admin_required
def search_cards():
    """安全的卡密搜索接口"""
    bind_date_start = request.args.get('bind_date_start')
    bind_date_end = request.args.get('bind_date_end')
    expire_date_end = request.args.get('expire_date_end')
    status = request.args.get('status', 'all')
    
    db = get_db()
    
    conditions = []
    params = []
    
    if bind_date_start:
        conditions.append('bind_time >= ?')
        params.append(bind_date_start)
    
    if bind_date_end:
        conditions.append('bind_time <= ?')
        params.append(bind_date_end)
    
    if expire_date_end:
        conditions.append('expire_date <= ?')
        conditions.append('expire_date IS NOT NULL')
        params.append(expire_date_end)
    
    if status == 'bound':
        conditions.append('machine_code IS NOT NULL')
    elif status == 'unbound':
        conditions.append('machine_code IS NULL')
    
    where_clause = ' AND '.join(conditions) if conditions else '1=1'
    
    rows = db.execute(f'SELECT * FROM cards WHERE {where_clause} ORDER BY bind_time DESC', params).fetchall()
    
    cards = [row_to_dict(row) for row in rows]
    
    return jsonify({'success': True, 'data': cards, 'count': len(cards)})

@app.route('/api/admin/logs', methods=['GET'])
@admin_required
def get_logs():
    limit = request.args.get('limit', 100, type=int)
    db = get_db()
    rows = db.execute('SELECT * FROM access_logs ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    logs = [dict(row) for row in rows]
    return jsonify({'success': True, 'data': logs})

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_stats():
    db = get_db()
    total = db.execute('SELECT COUNT(*) FROM cards').fetchone()[0]
    active = db.execute('SELECT COUNT(*) FROM cards WHERE disabled = 0').fetchone()[0]
    bound = db.execute('SELECT COUNT(*) FROM cards WHERE machine_code IS NOT NULL').fetchone()[0]
    
    return jsonify({
        'success': True,
        'data': {
            'total_cards': total,
            'active_cards': active,
            'bound_cards': bound
        }
    })


@app.route('/api/admin/sql', methods=['POST'])
@admin_required
def execute_sql():
    """
    执行自定义SQL查询（仅支持SELECT，增强安全防护）
    """
    import re
    
    data = request.get_json()
    sql = data.get('sql', '').strip()
    
    if not sql:
        return jsonify({'success': False, 'message': 'SQL不能为空'})
    
    # 安全检查1：只允许SELECT查询
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith('SELECT'):
        app.logger.warning(f"SQL blocked (not SELECT): {sql[:100]}")
        return jsonify({'success': False, 'message': '只支持SELECT查询'})
    
    # 安全检查2：禁止危险关键字
    dangerous_keywords = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 
        'TRUNCATE', 'REPLACE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
        'ATTACH', 'DETACH', 'PRAGMA', 'VACUUM', 'REINDEX'
    ]
    for keyword in dangerous_keywords:
        # 使用单词边界匹配，避免误判（如 SELECT 中的 DELETE）
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            app.logger.warning(f"SQL blocked (dangerous keyword {keyword}): {sql[:100]}")
            return jsonify({'success': False, 'message': f'不允许使用 {keyword} 操作'})
    
    # 安全检查3：禁止多语句执行（分号后还有内容）
    # 移除字符串中的分号再检查
    sql_no_strings = re.sub(r"'[^']*'", '', sql)  # 移除单引号字符串
    sql_no_strings = re.sub(r'"[^"]*"', '', sql_no_strings)  # 移除双引号字符串
    if ';' in sql_no_strings.rstrip(';'):  # 允许末尾分号
        app.logger.warning(f"SQL blocked (multiple statements): {sql[:100]}")
        return jsonify({'success': False, 'message': '不允许执行多条SQL语句'})
    
    # 安全检查4：禁止注释（可能用于绕过检查）
    if '--' in sql or '/*' in sql:
        app.logger.warning(f"SQL blocked (comments): {sql[:100]}")
        return jsonify({'success': False, 'message': '不允许使用SQL注释'})
    
    # 安全检查5：只允许查询 cards 和 access_logs 表
    allowed_tables = ['cards', 'access_logs']
    # 简单检查FROM子句
    from_match = re.search(r'\bFROM\s+(\w+)', sql_upper)
    if from_match:
        table_name = from_match.group(1).lower()
        if table_name not in allowed_tables:
            app.logger.warning(f"SQL blocked (table {table_name}): {sql[:100]}")
            return jsonify({'success': False, 'message': f'只允许查询 {", ".join(allowed_tables)} 表'})
    
    # 安全检查6：限制结果数量
    if 'LIMIT' not in sql_upper:
        sql = sql.rstrip(';') + ' LIMIT 1000'
    
    try:
        db = get_db()
        rows = db.execute(sql).fetchall()
        
        results = []
        for row in rows:
            results.append(dict(row))
        
        app.logger.info(f"SQL executed: {sql[:100]}... returned {len(results)} rows")
        
        return jsonify({
            'success': True, 
            'data': results, 
            'count': len(results),
            'columns': list(results[0].keys()) if results else []
        })
    except Exception as e:
        app.logger.error(f"SQL error: {sql[:100]}... - {str(e)}")
        return jsonify({'success': False, 'message': f'SQL执行错误: {str(e)}'})


@app.route('/api/admin/cards/batch_time', methods=['POST'])
@admin_required
def batch_update_time():
    """批量调整卡密时间"""
    from datetime import timedelta
    
    data = request.get_json()
    bind_date_start = data.get('bind_date_start')
    bind_date_end = data.get('bind_date_end')
    hours = data.get('hours', 0)
    
    if not hours:
        return jsonify({'success': False, 'message': '请指定调整小时数'})
    
    hours = int(hours)
    
    db = get_db()
    
    conditions = ['expire_date IS NOT NULL']
    params = []
    
    if bind_date_start:
        conditions.append('bind_time >= ?')
        params.append(bind_date_start)
    
    if bind_date_end:
        conditions.append('bind_time <= ?')
        params.append(bind_date_end)
    
    where_clause = ' AND '.join(conditions)
    
    rows = db.execute(f'SELECT card_key, expire_date FROM cards WHERE {where_clause}', params).fetchall()
    
    if not rows:
        return jsonify({'success': False, 'message': '没有找到符合条件的卡密'})
    
    updated_count = 0
    for row in rows:
        card_key = row['card_key']
        expire_date = row['expire_date']
        
        try:
            if ' ' in expire_date:
                expire_dt = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
            else:
                expire_dt = datetime.strptime(expire_date, '%Y-%m-%d')
                expire_dt = expire_dt.replace(hour=23, minute=59, second=59)
            
            new_expire = expire_dt + timedelta(hours=hours)
            new_expire_str = new_expire.strftime('%Y-%m-%d %H:%M:%S')
            
            db.execute('UPDATE cards SET expire_date = ? WHERE card_key = ?', (new_expire_str, card_key))
            updated_count += 1
        except Exception as e:
            continue
    
    db.commit()
    
    action = '增加' if hours > 0 else '减少'
    app.logger.info(f"Batch time update: {action}{abs(hours)}h, {updated_count} cards")
    return jsonify({
        'success': True, 
        'message': f'成功{action}{abs(hours)}小时，共更新{updated_count}张卡密'
    })

# ========== 启动 ==========
if __name__ == '__main__':
    init_db()
    app.logger.info("Server starting...")
    # 开发模式
    app.run(host='0.0.0.0', port=5000, debug=False)
