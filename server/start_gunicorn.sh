#!/bin/bash
# 使用 Gunicorn 多进程启动服务器

cd "$(dirname "$0")"

# 激活虚拟环境（如果有）
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# 安装依赖
pip install gunicorn pycryptodome -q

# 初始化数据库
python -c "from auth_server_v2 import init_db; init_db()"

# 启动 Gunicorn
echo "Starting server with Gunicorn (multi-process)..."
gunicorn -c gunicorn_config.py auth_server_v2:app
