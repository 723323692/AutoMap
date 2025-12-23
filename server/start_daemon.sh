#!/bin/bash
# 带自动重启的守护进程启动脚本

cd "$(dirname "$0")"

export AUTH_API_SECRET="BabyBus2024SecretKey"
export AUTH_ENCRYPT_KEY="BabyBusEncrypt2024"

LOG_FILE="server.log"
PID_FILE="server.pid"
CHECK_INTERVAL=10  # 检查间隔（秒）

start_server() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动服务..." >> $LOG_FILE
    gunicorn -w 2 -b 0.0.0.0:5000 auth_server:app >> $LOG_FILE 2>&1 &
    echo $! > $PID_FILE
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 服务已启动，PID: $(cat $PID_FILE)" >> $LOG_FILE
}

check_and_restart() {
    if [ -f $PID_FILE ]; then
        PID=$(cat $PID_FILE)
        if ! kill -0 $PID 2>/dev/null; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 检测到服务异常停止，正在重启..." >> $LOG_FILE
            start_server
        fi
    else
        start_server
    fi
}

# 停止已有的守护进程
pkill -f "gunicorn.*auth_server" 2>/dev/null
sleep 1

echo "启动守护进程..."
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 守护进程启动" >> $LOG_FILE

# 首次启动
start_server

# 守护循环
while true; do
    sleep $CHECK_INTERVAL
    check_and_restart
done
