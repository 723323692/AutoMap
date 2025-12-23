#!/bin/bash
# 卡密验证服务部署脚本 - Linux

# 设置API密钥
export AUTH_API_SECRET="BabyBus2024SecretKey"

# 安装依赖
echo "安装依赖..."
pip3 install flask gunicorn

# 启动服务（后台运行）
echo "启动服务..."
nohup gunicorn -w 2 -b 0.0.0.0:5000 auth_server:app > server.log 2>&1 &

echo "服务已启动，端口: 5000"
echo "日志文件: server.log"
echo "查看日志: tail -f server.log"
