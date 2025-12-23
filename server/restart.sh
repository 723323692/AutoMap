#!/bin/bash
# 重启卡密验证服务

cd "$(dirname "$0")"

echo "停止服务..."
pkill -f "python3 auth_server.py"
sleep 1

echo "启动服务..."
export AUTH_API_SECRET="BabyBus2024SecretKey"
nohup python3 auth_server.py > server.log 2>&1 &

sleep 2

if pgrep -f "python3 auth_server.py" > /dev/null; then
    echo "服务启动成功"
    echo "进程ID: $(pgrep -f 'python3 auth_server.py')"
else
    echo "服务启动失败，查看日志:"
    tail -20 server.log
fi
