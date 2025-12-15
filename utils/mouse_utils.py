# -*- coding:utf-8 -*-
"""
鼠标操作工具模块
"""

__author__ = "723323692"
__version__ = '1.0'

import math
import random
import time
from typing import Tuple

from pynput.mouse import Controller, Button

mouse = Controller()


def do_smooth_move_to(x: int, y: int) -> None:
    """
    平滑移动鼠标到指定位置（仿真移动）
    
    Args:
        x: 目标X坐标
        y: 目标Y坐标
    """
    current_x, current_y = mouse.position
    steps = 10

    # 根据移动距离决定拆分步骤
    distance = math.sqrt((current_x - x) ** 2 + (current_y - y) ** 2)
    steps = min(math.ceil(distance / 100), steps)
    steps = max(steps, 1)

    step_x = (x - current_x) / steps
    step_y = (y - current_y) / steps

    for step in range(steps):
        next_x = current_x + step_x + random.uniform(-1, 1)
        next_y = current_y + step_y + random.uniform(-1, 1)
        if step == (steps - 1):
            next_x = x
            next_y = y
        mouse.position = (int(next_x), int(next_y))
        time.sleep(random.uniform(0.01, 0.02))
    time.sleep(0.1)


def do_move_to(x: int, y: int) -> None:
    """
    直接移动鼠标到指定位置
    
    Args:
        x: 目标X坐标
        y: 目标Y坐标
    """
    mouse.position = (x, y)
    time.sleep(0.1)


def do_move_and_click(x: int, y: int) -> None:
    """
    移动到指定位置并点击左键
    
    Args:
        x: 目标X坐标
        y: 目标Y坐标
    """
    do_move_to(x, y)
    do_click(Button.left)
    time.sleep(0.1)


def do_click(key: Button) -> None:
    """
    鼠标点击（带随机延迟）
    
    Args:
        key: 鼠标按键
    """
    random_float = random.uniform(40, 60)
    do_click_with_time(key, random_float, random_float)


def do_click_with_time(key: Button, duration: float, after_release: float) -> None:
    """
    鼠标点击，指定按下时长和释放后等待时间
    
    Args:
        key: 鼠标按键
        duration: 按下持续时间（毫秒）
        after_release: 释放后等待时间（毫秒）
    """
    mouse.press(key)
    time.sleep(duration / 1000)
    mouse.release(key)
    time.sleep(after_release / 1000)


def get_current_position() -> Tuple[int, int]:
    """
    获取当前鼠标位置
    
    Returns:
        (x, y) 坐标元组
    """
    return mouse.position
