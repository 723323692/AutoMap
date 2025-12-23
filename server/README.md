# 卡密验证服务端

## 自动重启功能

### 方式1: 守护脚本（简单）
```bash
chmod +x start_daemon.sh
nohup ./start_daemon.sh &
```

### 方式2: systemd服务（推荐）
```bash
# 1. 修改 auth_server.service 中的 WorkingDirectory 为实际路径
# 2. 复制到 systemd
sudo cp auth_server.service /etc/systemd/system/

# 3. 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable auth_server
sudo systemctl start auth_server

# 查看状态
sudo systemctl status auth_server
```

## 部署步骤

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
# Linux/Mac
export AUTH_API_SECRET="你的密钥"

# Windows
set AUTH_API_SECRET=你的密钥
```

### 3. 启动服务

开发模式：
```bash
python auth_server.py
```

生产模式（推荐）：
```bash
gunicorn -w 4 -b 0.0.0.0:5000 auth_server:app
```

### 4. 配置防火墙
确保服务器的 5000 端口对外开放。

## 客户端配置

修改客户端的 `utils/auth.py` 中的配置：
```python
AUTH_SERVER_URL = 'http://你的服务器IP:5000'
API_SECRET = '你的密钥'
```

或者通过环境变量设置：
```bash
set AUTH_SERVER_URL=http://你的服务器IP:5000
set AUTH_API_SECRET=你的密钥
```

## API 接口

### 验证卡密
- POST `/api/verify`
- 参数: card_key, machine_code, timestamp, sign

### 心跳检测
- POST `/api/heartbeat`
- 参数: card_key, machine_code, timestamp, sign

### 管理接口（需要 X-Admin-Key 头）
- GET `/api/admin/cards` - 获取所有卡密
- POST `/api/admin/card` - 创建卡密
- DELETE `/api/admin/card/<key>` - 删除卡密
- POST `/api/admin/card/<key>/toggle` - 启用/禁用
- POST `/api/admin/card/<key>/unbind` - 解绑机器码
