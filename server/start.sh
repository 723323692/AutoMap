#!/bin/bash
# 启动卡密验证服务

export AUTH_API_SECRET="BabyBus2024SecretKey"

# 检查是否已运行
if pgrep -f "gunicorn.*auth_server" > /dev/null; then
    echo "服务已在运行"
    exit 0
fi

# 启动
cd "$(dirname "$0")"
nohup gunicorn -w 2 -b 0.0.0.0:5000 auth_server:app > server.log 2>&1 &

echo "服务已启动"
