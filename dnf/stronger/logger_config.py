# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'

import os
import sys
import time
from pathlib import Path

from loguru import logger
from datetime import datetime

file_log_id = None
console_log_id = None

log_dir = f'{os.path.dirname(os.path.abspath(__file__))}/logs'
os.makedirs(log_dir, exist_ok=True)


def cleanup_old_logs(days=7):
    """
    清除指定天数之外的日志文件

    Args:
        days (int): 保留的天数，默认为7天
    """
    try:
        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)  # 计算截止时间

        log_path = Path(log_dir)

        # 遍历日志目录中的所有文件
        for log_file in log_path.iterdir():
            if log_file.is_file():
                # 检查文件修改时间是否超过截止时间
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()  # 删除文件
                    logger.info(f"已删除旧日志文件: {log_file.name}")

    except Exception as e:
        logger.error(f"清理旧日志时发生错误: {e}")


def switch_level(level):
    global file_log_id, console_log_id
    logger.remove(file_log_id)
    logger.remove(console_log_id)

    # 在创建新日志前清理旧日志
    cleanup_old_logs(7)

    file_log_id = logger.add(f'{log_dir}/{datetime.now().strftime("%Y-%m-%d.%H%M%S")}.log', level=level, retention=10,
                             enqueue=True)
    # 只有当 sys.stderr 有效时才添加控制台日志（GUI模式下可能为None）
    if sys.stderr is not None:
        console_log_id = logger.add(sys.stderr, enqueue=True)


switch_level("DEBUG")
# cleanup_old_logs(1)