# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'


import os
import sys

from loguru import logger
from datetime import datetime

file_log_id = None
console_log_id = None

log_dir = f'{os.path.dirname(os.path.abspath(__file__))}/logs'
os.makedirs(log_dir, exist_ok=True)


def switch_level(level):
    global file_log_id, console_log_id
    logger.remove(file_log_id)
    logger.remove(console_log_id)
    file_log_id = logger.add(f'{log_dir}/{datetime.now().strftime("%Y-%m-%d.%H%M%S")}.log', level=level, retention=10,
                             enqueue=True)
    # console_log_id = logger.add(sys.stderr, level=level)
    console_log_id = logger.add(sys.stderr, enqueue=True)


switch_level("INFO")
