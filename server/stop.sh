#!/bin/bash
# 停止卡密验证服务

pkill -f "gunicorn.*auth_server"
echo "服务已停止"
