# -*- coding:utf-8 -*-
"""
卡密验证服务端 - SQLite + 安全防护 + 加密传输版本
"""

import os
import hashlib
import sqlite3
import time
import json
import base64
from datetime import datetime
from functools import wraps
from collections import defaultdict
from flask import Flask, request, jsonify, g

app = Flask(__name__)

# 配置
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(DATA_DIR, 'cards.db')
API_SECRET = os.environ.get('AUTH_API_SECRET', 'BabyBus2024SecretKey')
ENCRYPT_KEY = os.environ.get('AUTH_ENCRYPT_KEY', 'BabyBusEncrypt2024')

# ========== 加密函数 ==========
def xor_encrypt(data, key):
    """XOR加密"""
    key_bytes = key.encode('utf-8')
    data_bytes = data.encode('utf-8')
    encrypted = bytes([data_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data_bytes))])
    return base64.b64encode(encrypted).decode('utf-8')


def xor_decrypt(encrypted_data, key):
    """XOR解密"""
    try:
        key_bytes = key.encode('utf-8')
        data_bytes = base64.b64decode(encrypted_data)
        decrypted = bytes([data_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data_bytes))])
        return decrypted.decode('utf-8')
    except:
        return None


def decrypt_request():
    """解密请求数据"""
    data = request.get_json() or {}
    if 'encrypted' in data and data.get('v') == '2':
        decrypted = xor_decrypt(data['encrypted'], ENCRYPT_KEY)
        if decrypted:
            return json.loads(decrypted)
    return data  # 兼容未加密请求


def encrypt_response(data):
    """加密响应数据"""
    json_str = json.dumps(data, ensure_ascii=False)
    encrypted = xor_encrypt(json_str, ENCRYPT_KEY)
    return jsonify({'encrypted': encrypted, 'v': '2'})


# ========== 安全防护配置 ==========
RATE_LIMIT_WINDOW = 60          # 限流时间窗口（秒）
RATE_LIMIT_MAX_REQUESTS = 30    # 每个IP每分钟最大请求数
VERIFY_RATE_LIMIT = 5           # 验证接口每分钟最大尝试次数
BLOCK_DURATION = 300            # 封禁时长（秒）
MAX_FAILED_ATTEMPTS = 10        # 最大失败次数后封禁
TIMESTAMP_TOLERANCE = 300       # 时间戳容差（秒）

# 内存存储（生产环境建议用Redis）
request_counts = defaultdict(list)      # IP请求计数
failed_attempts = defaultdict(int)      # 失败尝试次数
blocked_ips = {}                        # 封禁的IP


def get_client_ip():
    """获取客户端真实IP"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


def is_ip_blocked(ip):
    """检查IP是否被封禁"""
    if ip in blocked_ips:
        if time.time() < blocked_ips[ip]:
            return True
        else:
            del blocked_ips[ip]
            failed_attempts[ip] = 0
    return False


def block_ip(ip):
    """封禁IP"""
    blocked_ips[ip] = time.time() + BLOCK_DURATION


def check_rate_limit(ip, limit=RATE_LIMIT_MAX_REQUESTS):
    """检查请求频率"""
    now = time.time()
    # 清理过期记录
    request_counts[ip] = [t for t in request_counts[ip] if now - t < RATE_LIMIT_WINDOW]
    
    if len(request_counts[ip]) >= limit:
        return False
    
    request_counts[ip].append(now)
    return True


def record_failed_attempt(ip):
    """记录失败尝试"""
    failed_attempts[ip] += 1
    if failed_attempts[ip] >= MAX_FAILED_ATTEMPTS:
        block_ip(ip)
        return True
    return False


def security_check(verify_endpoint=False):
    """安全检查装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ip = get_client_ip()
            
            # 检查是否被封禁
            if is_ip_blocked(ip):
                return jsonify({'success': False, 'message': '请求过于频繁，请稍后再试'}), 429
            
            # 检查请求频率
            limit = VERIFY_RATE_LIMIT if verify_endpoint else RATE_LIMIT_MAX_REQUESTS
            if not check_rate_limit(ip, limit):
                return jsonify({'success': False, 'message': '请求过于频繁'}), 429
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_db():
    """获取数据库连接"""
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
    # 添加新字段（如果表已存在）
    try:
        conn.execute('ALTER TABLE cards ADD COLUMN unbind_count INTEGER DEFAULT 0')
    except:
        pass
    try:
        conn.execute('ALTER TABLE cards ADD COLUMN max_unbind_count INTEGER DEFAULT 3')
    except:
        pass
    try:
        conn.execute('ALTER TABLE cards ADD COLUMN total_deducted_hours INTEGER DEFAULT 0')
    except:
        pass
    try:
        conn.execute('ALTER TABLE cards ADD COLUMN expire_days INTEGER')
    except:
        pass
    
    # 创建日志表
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


def log_access(card_key, ip, action, result, message=''):
    """记录访问日志"""
    try:
        db = get_db()
        db.execute('''
            INSERT INTO access_logs (card_key, ip, action, result, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (card_key, ip, action, result, message, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        db.commit()
    except:
        pass


def sign_request(data, secret):
    """生成请求签名"""
    sorted_data = '&'.join(f"{k}={v}" for k, v in sorted(data.items()) if k != 'sign')
    return hashlib.md5(f"{sorted_data}&secret={secret}".encode()).hexdigest()


def verify_sign(func):
    """验证请求签名（支持加密请求）"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        ip = get_client_ip()
        
        # 解密请求数据
        data = decrypt_request()
        
        # 将解密后的数据存储到 g 对象供后续使用
        g.decrypted_data = data
        
        # 验证时间戳（防重放攻击）
        timestamp = data.get('timestamp', '')
        if timestamp:
            try:
                req_time = int(timestamp)
                if abs(time.time() - req_time) > TIMESTAMP_TOLERANCE:
                    log_access(data.get('card_key', ''), ip, 'verify', 'fail', '时间戳过期')
                    return encrypt_response({'success': False, 'message': '请求已过期'})
            except:
                pass
        
        # 验证签名
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


@app.route('/api/verify', methods=['POST'])
@security_check(verify_endpoint=True)
@verify_sign
def verify_card():
    """验证卡密（加密传输）"""
    ip = get_client_ip()
    data = g.decrypted_data  # 使用解密后的数据
    card_key = data.get('card_key', '').strip().upper()
    machine_code = data.get('machine_code', '').strip()
    
    if not card_key or not machine_code:
        return encrypt_response({'success': False, 'message': '参数不完整'})
    
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
        # 支持两种格式
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
        # 首次激活，设置到期时间（只有expire_date为空时才计算）
        expire_days = row['expire_days']
        expire_date = row['expire_date']  # 获取当前的expire_date
        if expire_days and not expire_date:
            # 只有没有expire_date时才根据expire_days计算
            from datetime import timedelta
            expire_date = (datetime.now() + timedelta(days=expire_days)).strftime('%Y-%m-%d %H:%M:%S')
            db.execute('UPDATE cards SET machine_code = ?, bind_time = ?, expire_date = ? WHERE card_key = ?',
                       (machine_code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), expire_date, card_key))
        else:
            # 已有expire_date（解绑后重新绑定）或永久卡密，只更新绑定信息
            db.execute('UPDATE cards SET machine_code = ?, bind_time = ? WHERE card_key = ?',
                       (machine_code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), card_key))
        # 重新获取更新后的数据
        row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
        expire_date = row['expire_date']
    
    db.execute('UPDATE cards SET last_use = ?, last_ip = ? WHERE card_key = ?',
               (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip, card_key))
    db.commit()
    
    # 重置失败计数
    failed_attempts[ip] = 0
    
    days_left = -1
    hours_left = -1
    minutes_left = -1
    seconds_left = -1
    expire_datetime = None
    if expire_date:
        # 支持两种格式：纯日期和带时间
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
    data = g.decrypted_data  # 使用解密后的数据
    card_key = data.get('card_key', '').strip().upper()
    machine_code = data.get('machine_code', '').strip()
    
    if not card_key or not machine_code:
        return jsonify({'success': False, 'message': '参数不完整'})
    
    db = get_db()
    row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    
    if not row:
        return jsonify({'success': False, 'message': '卡密不正确'})
    
    if row['disabled']:
        return jsonify({'success': False, 'message': '卡密已被禁用'})
    
    expire_date = row['expire_date']
    if expire_date:
        # 支持两种格式
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


@app.route('/api/unbind_info', methods=['POST'])
@security_check(verify_endpoint=False)
@verify_sign
def get_unbind_info():
    """查询解绑信息（剩余次数等）"""
    data = request.get_json()
    card_key = data.get('card_key', '').strip().upper()
    machine_code = data.get('machine_code', '').strip()
    
    if not card_key:
        return jsonify({'success': False, 'message': '参数不完整'})
    
    db = get_db()
    row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    
    if not row:
        return jsonify({'success': False, 'message': '卡密不正确'})
    
    unbind_count = row['unbind_count'] or 0
    max_unbind = 3
    remaining = max_unbind - unbind_count
    is_bound = row['machine_code'] is not None
    is_current_device = row['machine_code'] == machine_code
    
    return jsonify({
        'success': True,
        'data': {
            'unbind_count': unbind_count,
            'max_unbind': max_unbind,
            'remaining': remaining,
            'is_bound': is_bound,
            'is_current_device': is_current_device,
            'deduct_hours': 8
        }
    })


@app.route('/api/unbind', methods=['POST'])
@security_check(verify_endpoint=True)
@verify_sign
def user_unbind():
    """用户自助解绑（扣除8小时）"""
    from datetime import timedelta
    
    DEDUCT_HOURS = 8      # 每次扣除小时数
    
    ip = get_client_ip()
    data = request.get_json()
    card_key = data.get('card_key', '').strip().upper()
    machine_code = data.get('machine_code', '').strip()
    
    if not card_key or not machine_code:
        return jsonify({'success': False, 'message': '参数不完整'})
    
    db = get_db()
    row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    
    if not row:
        return jsonify({'success': False, 'message': '卡密不正确'})
    
    # 检查卡密是否已绑定
    if not row['machine_code']:
        return jsonify({'success': False, 'message': '该卡密未绑定设备'})
    
    # 检查解绑次数（使用卡密自己的最大解绑次数）
    unbind_count = row['unbind_count'] or 0
    max_unbind = row['max_unbind_count'] if row['max_unbind_count'] is not None else 3
    if unbind_count >= max_unbind:
        log_access(card_key, ip, 'unbind', 'fail', '解绑次数已用完')
        return jsonify({'success': False, 'message': f'解绑次数已用完（最多{max_unbind}次）'})
    
    # 检查有效期，扣除8小时
    expire_date = row['expire_date']
    if expire_date:
        if ' ' in expire_date:
            expire_dt = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
        else:
            expire_dt = datetime.strptime(expire_date, '%Y-%m-%d')
            expire_dt = expire_dt.replace(hour=23, minute=59, second=59)
        
        new_expire = expire_dt - timedelta(hours=DEDUCT_HOURS)
        
        # 检查扣除后是否已过期
        if new_expire < datetime.now():
            return jsonify({'success': False, 'message': f'剩余时间不足{DEDUCT_HOURS}小时，无法解绑'})
        
        new_expire_str = new_expire.strftime('%Y-%m-%d %H:%M:%S')
        total_deducted = (row['total_deducted_hours'] or 0) + DEDUCT_HOURS
        
        db.execute('''
            UPDATE cards SET 
                machine_code = NULL, 
                bind_time = NULL, 
                expire_date = ?,
                unbind_count = ?,
                total_deducted_hours = ?
            WHERE card_key = ?
        ''', (new_expire_str, unbind_count + 1, total_deducted, card_key))
        
        db.commit()
        remaining = max_unbind - unbind_count - 1
        
        # 计算剩余时间
        delta = new_expire - datetime.now()
        total_seconds = max(0, delta.total_seconds())
        days_left = int(total_seconds // 86400)
        hours_left = int((total_seconds % 86400) // 3600)
        minutes_left = int((total_seconds % 3600) // 60)
        seconds_left = int(total_seconds % 60)
        
        log_access(card_key, ip, 'unbind', 'success', f'用户自助解绑，剩余{remaining}次')
        
        return jsonify({
            'success': True, 
            'message': f'解绑成功，已扣除{DEDUCT_HOURS}小时，剩余解绑次数: {remaining}次',
            'data': {
                'days_left': days_left,
                'hours_left': hours_left,
                'minutes_left': minutes_left,
                'seconds_left': seconds_left,
                'expire_datetime': new_expire_str
            }
        })
    else:
        # 永久卡密也记录解绑次数
        db.execute('''
            UPDATE cards SET 
                machine_code = NULL, 
                bind_time = NULL,
                unbind_count = ?
            WHERE card_key = ?
        ''', (unbind_count + 1, card_key))
        
        db.commit()
        remaining = max_unbind - unbind_count - 1
        log_access(card_key, ip, 'unbind', 'success', f'用户自助解绑，剩余{remaining}次')
        
        return jsonify({
            'success': True, 
            'message': f'解绑成功，剩余解绑次数: {remaining}次',
            'data': {
                'days_left': -1,
                'hours_left': -1,
                'expire_datetime': '永久'
            }
        })


# ========== 管理接口 ==========

def admin_required(func):
    """管理员权限验证"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        admin_key = request.headers.get('X-Admin-Key', '')
        if admin_key != API_SECRET:
            return jsonify({'success': False, 'message': '无权限'}), 403
        return func(*args, **kwargs)
    return wrapper


@app.route('/api/admin/cards', methods=['GET'])
@admin_required
def list_cards():
    """获取所有卡密列表"""
    db = get_db()
    rows = db.execute('SELECT * FROM cards ORDER BY create_time DESC').fetchall()
    cards = {row['card_key']: row_to_dict(row) for row in rows}
    return jsonify({'success': True, 'data': cards})


@app.route('/api/admin/card', methods=['POST'])
@admin_required
def create_card():
    """创建卡密"""
    data = request.get_json()
    card_key = data.get('card_key', '').strip().upper()
    expire_days = data.get('expire_days')  # 有效天数
    remark = data.get('remark', '')
    
    if not card_key:
        return jsonify({'success': False, 'message': '卡密不能为空'})
    
    db = get_db()
    existing = db.execute('SELECT 1 FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    if existing:
        return jsonify({'success': False, 'message': '卡密已存在'})
    
    # 不设置expire_date，激活时才设置
    db.execute('''
        INSERT INTO cards (card_key, expire_days, create_time, remark, disabled)
        VALUES (?, ?, ?, ?, 0)
    ''', (card_key, expire_days, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), remark))
    db.commit()
    
    return jsonify({'success': True, 'message': '创建成功'})


@app.route('/api/admin/card/<card_key>', methods=['DELETE'])
@admin_required
def delete_card(card_key):
    """删除卡密"""
    card_key = card_key.upper()
    db = get_db()
    result = db.execute('DELETE FROM cards WHERE card_key = ?', (card_key,))
    db.commit()
    
    if result.rowcount > 0:
        return jsonify({'success': True, 'message': '删除成功'})
    return jsonify({'success': False, 'message': '卡密不存在'})


@app.route('/api/admin/card/<card_key>/toggle', methods=['POST'])
@admin_required
def toggle_card(card_key):
    """启用/禁用卡密"""
    card_key = card_key.upper()
    db = get_db()
    row = db.execute('SELECT disabled FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    
    if row:
        new_status = 0 if row['disabled'] else 1
        db.execute('UPDATE cards SET disabled = ? WHERE card_key = ?', (new_status, card_key))
        db.commit()
        status = '禁用' if new_status else '启用'
        return jsonify({'success': True, 'message': f'已{status}'})
    
    return jsonify({'success': False, 'message': '卡密不存在'})


@app.route('/api/admin/card/<card_key>/unbind', methods=['POST'])
@admin_required
def unbind_card(card_key):
    """解绑卡密"""
    card_key = card_key.upper()
    db = get_db()
    result = db.execute('UPDATE cards SET machine_code = NULL, bind_time = NULL WHERE card_key = ?', (card_key,))
    db.commit()
    
    if result.rowcount > 0:
        return jsonify({'success': True, 'message': '解绑成功'})
    return jsonify({'success': False, 'message': '卡密不存在'})


@app.route('/api/admin/card/<card_key>/update', methods=['POST'])
@admin_required
def update_card(card_key):
    """更新卡密信息"""
    card_key = card_key.upper()
    data = request.get_json()
    
    db = get_db()
    row = db.execute('SELECT * FROM cards WHERE card_key = ?', (card_key,)).fetchone()
    if not row:
        return jsonify({'success': False, 'message': '卡密不存在'})
    
    updates = []
    params = []
    
    # 更新已用解绑次数
    if 'unbind_count' in data:
        unbind_count = int(data['unbind_count'])
        if unbind_count < 0:
            unbind_count = 0
        updates.append('unbind_count = ?')
        params.append(unbind_count)
    
    # 更新最大解绑次数
    if 'max_unbind_count' in data:
        max_unbind = int(data['max_unbind_count'])
        if max_unbind < 0:
            max_unbind = 0
        updates.append('max_unbind_count = ?')
        params.append(max_unbind)
    
    # 更新到期时间
    if 'expire_date' in data:
        updates.append('expire_date = ?')
        params.append(data['expire_date'])
    
    # 更新有效天数
    if 'expire_days' in data:
        updates.append('expire_days = ?')
        params.append(data['expire_days'])
    
    # 更新备注
    if 'remark' in data:
        updates.append('remark = ?')
        params.append(data['remark'])
    
    # 更新禁用状态
    if 'disabled' in data:
        updates.append('disabled = ?')
        params.append(int(data['disabled']))
    
    # 更新机器码
    if 'machine_code' in data:
        updates.append('machine_code = ?')
        params.append(data['machine_code'])
    
    # 更新绑定时间
    if 'bind_time' in data:
        updates.append('bind_time = ?')
        params.append(data['bind_time'])
    
    if not updates:
        return jsonify({'success': False, 'message': '没有要更新的字段'})
    
    params.append(card_key)
    sql = f"UPDATE cards SET {', '.join(updates)} WHERE card_key = ?"
    db.execute(sql, params)
    db.commit()
    
    return jsonify({'success': True, 'message': '更新成功'})


@app.route('/api/admin/cards/batch_time', methods=['POST'])
@admin_required
def batch_update_time():
    """
    批量调整卡密时间
    参数:
    - bind_date_start: 绑定时间起始（可选）
    - bind_date_end: 绑定时间结束（可选）
    - hours: 调整小时数（正数增加，负数减少）
    """
    from datetime import timedelta
    
    data = request.get_json()
    bind_date_start = data.get('bind_date_start')
    bind_date_end = data.get('bind_date_end')
    hours = data.get('hours', 0)
    
    if not hours:
        return jsonify({'success': False, 'message': '请指定调整小时数'})
    
    hours = int(hours)
    
    db = get_db()
    
    # 构建查询条件
    conditions = ['expire_date IS NOT NULL']  # 只处理有到期时间的卡密
    params = []
    
    if bind_date_start:
        conditions.append('bind_time >= ?')
        params.append(bind_date_start)
    
    if bind_date_end:
        conditions.append('bind_time <= ?')
        params.append(bind_date_end)
    
    where_clause = ' AND '.join(conditions)
    
    # 查询符合条件的卡密
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
    return jsonify({
        'success': True, 
        'message': f'成功{action}{abs(hours)}小时，共更新{updated_count}张卡密'
    })


@app.route('/api/admin/cards/search', methods=['GET'])
@admin_required
def search_cards():
    """
    搜索卡密
    参数:
    - bind_date_start: 绑定时间起始
    - bind_date_end: 绑定时间结束
    - status: 状态（bound=已绑定, unbound=未绑定, all=全部）
    """
    bind_date_start = request.args.get('bind_date_start')
    bind_date_end = request.args.get('bind_date_end')
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
    
    if status == 'bound':
        conditions.append('machine_code IS NOT NULL')
    elif status == 'unbound':
        conditions.append('machine_code IS NULL')
    
    where_clause = ' AND '.join(conditions) if conditions else '1=1'
    
    rows = db.execute(f'SELECT * FROM cards WHERE {where_clause} ORDER BY bind_time DESC', params).fetchall()
    
    cards = []
    for row in rows:
        try:
            card = dict(row)
            card['unbind_count'] = card.get('unbind_count') or 0
            card['disabled'] = bool(card.get('disabled'))
            cards.append(card)
        except Exception:
            continue
    
    return jsonify({'success': True, 'data': cards, 'count': len(cards)})


@app.route('/api/admin/sql', methods=['POST'])
@admin_required
def execute_sql():
    """
    执行自定义SQL查询（仅支持SELECT）
    """
    data = request.get_json()
    sql = data.get('sql', '').strip()
    
    if not sql:
        return jsonify({'success': False, 'message': 'SQL不能为空'})
    
    # 安全检查：只允许SELECT查询
    sql_upper = sql.upper()
    if not sql_upper.startswith('SELECT'):
        return jsonify({'success': False, 'message': '只支持SELECT查询'})
    
    # 禁止危险操作
    dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
    for word in dangerous:
        if word in sql_upper:
            return jsonify({'success': False, 'message': f'不允许使用 {word} 操作'})
    
    try:
        db = get_db()
        rows = db.execute(sql).fetchall()
        
        results = []
        for row in rows:
            results.append(dict(row))
        
        return jsonify({
            'success': True, 
            'data': results, 
            'count': len(results),
            'columns': list(results[0].keys()) if results else []
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'SQL执行错误: {str(e)}'})


@app.route('/api/admin/logs', methods=['GET'])
@admin_required
def get_logs():
    """获取访问日志"""
    limit = request.args.get('limit', 100, type=int)
    db = get_db()
    rows = db.execute('SELECT * FROM access_logs ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    logs = [dict(row) for row in rows]
    return jsonify({'success': True, 'data': logs})


@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_stats():
    """获取统计信息"""
    db = get_db()
    total = db.execute('SELECT COUNT(*) FROM cards').fetchone()[0]
    active = db.execute('SELECT COUNT(*) FROM cards WHERE disabled = 0').fetchone()[0]
    bound = db.execute('SELECT COUNT(*) FROM cards WHERE machine_code IS NOT NULL').fetchone()[0]
    
    return jsonify({
        'success': True,
        'data': {
            'total_cards': total,
            'active_cards': active,
            'bound_cards': bound,
            'blocked_ips': len(blocked_ips)
        }
    })


# 初始化数据库
init_db()

if __name__ == '__main__':
    print("卡密验证服务启动中...")
    print(f"数据库: {DB_FILE}")
    print("安全防护已启用")
    app.run(host='0.0.0.0', port=5000, debug=False)
