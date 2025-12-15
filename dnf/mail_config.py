# -*- coding:utf-8 -*-
"""
邮件配置模块 - 从环境变量或.env文件读取敏感信息
"""

__author__ = "723323692"
__version__ = '1.0'

import os
from pathlib import Path

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    # 查找项目根目录的 .env 文件
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv 未安装时跳过

# 邮件配置 - 从环境变量读取敏感信息
config = {
    # 发件人信息
    "sender": os.environ.get("DNF_MAIL_SENDER", ""),  # 发件人邮箱
    "password": os.environ.get("DNF_MAIL_PASSWORD", ""),  # 授权码

    # SMTP 设置 默认QQ邮箱
    "smtp_server": os.environ.get("DNF_SMTP_SERVER", "smtp.qq.com"),  # SMTP服务器地址
    "smtp_port": int(os.environ.get("DNF_SMTP_PORT", "465")),  # SSL端口

    # 收件人
    "receiver": os.environ.get("DNF_MAIL_RECEIVER", ""),
}


def is_configured() -> bool:
    """检查邮件配置是否完整"""
    return bool(config.get("sender") and config.get("password") and config.get("receiver"))
