# Gunicorn 配置文件
# 使用方法: gunicorn -c gunicorn_config.py auth_server_v2:app

import multiprocessing

# 绑定地址
bind = "0.0.0.0:5000"

# 工作进程数 = CPU核心数 * 2 + 1
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"

# 超时时间
timeout = 30

# 最大请求数后重启worker（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 日志
accesslog = "access.log"
errorlog = "error.log"
loglevel = "info"

# 进程名
proc_name = "auth_server"

# 守护进程模式
daemon = False
