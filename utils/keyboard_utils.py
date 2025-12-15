# -*- coding:utf-8 -*-
"""
键盘操作工具模块
"""

__author__ = "723323692"
__version__ = '1.0'

import random
import time
from typing import List, Optional, Union, Set

from pynput.keyboard import Controller, Key, KeyCode
from dnf.dnf_config import direct_dic

keyboard = Controller()

# 方向常量
DIRECTION_SET: Set[str] = {"UP", "DOWN", "LEFT", "RIGHT", "RIGHT_UP", "RIGHT_DOWN", "LEFT_UP", "LEFT_DOWN"}
SINGLE_DIRECTIONS: List[str] = ["LEFT", "RIGHT", "UP", "DOWN"]
DOUBLE_DIRECTIONS: List[str] = ["RIGHT_UP", "RIGHT_DOWN", "LEFT_UP", "LEFT_DOWN"]

# 向后兼容的别名
direct_set = DIRECTION_SET
single_direct = SINGLE_DIRECTIONS
double_direct = DOUBLE_DIRECTIONS

# 类型别名
KeyType = Union[str, Key, KeyCode]


def do_release(key: KeyType) -> None:
    """释放按键"""
    keyboard.release(key)


def do_press(key: KeyType) -> None:
    """
    按键（带随机延迟）
    
    Args:
        key: 要按的键
    """
    random_float = random.uniform(40, 60)
    do_press_with_time(key, random_float, random_float)


def do_press_with_time(key: KeyType, duration: float, after_release: float) -> None:
    """
    按键，指定按下时长和释放后等待时间
    
    Args:
        key: 要按的键
        duration: 按下持续时间（毫秒）
        after_release: 释放后等待时间（毫秒）
    """
    keyboard.press(key)
    time.sleep(duration / 1000)
    keyboard.release(key)
    if after_release:
        time.sleep(after_release / 1000)


def do_skill(key: Optional[KeyType]) -> None:
    """
    按技能键，按完后等待技能动作结束
    
    Args:
        key: 技能按键
    """
    if key == '' or key is None:
        return
    random_float = random.uniform(980, 1100)
    do_skill_with_time(key, random_float)


def do_skill_with_time(key: Optional[KeyType], wait_time: float) -> None:
    """
    按技能键，指定等待时间
    
    Args:
        key: 技能按键
        wait_time: 等待时间（毫秒）
    """
    if key == '' or key is None:
        return
    do_press(key)
    time.sleep(wait_time / 1000)


def do_command_wait_time(key_arr: List[KeyType], wait_time: float) -> None:
    """
    执行组合键指令，之后等待指定时间
    
    Args:
        key_arr: 按键序列，如 [前, 前, 空格]
        wait_time: 等待时间（秒）
    """
    for key in key_arr:
        if key == ' ' or key == '':
            time.sleep(0.1)
            continue
        do_press(key)
    time.sleep(wait_time)


def do_concurrent_command_wait_time(key_arr: List[KeyType], wait_time: float) -> None:
    """
    同时按下多个键，之后等待指定时间
    
    Args:
        key_arr: 按键序列
        wait_time: 等待时间（秒）
    """
    for key in key_arr:
        keyboard.press(key)
        time.sleep(0.05)

    for key in key_arr:
        keyboard.release(key)
    time.sleep(wait_time)


def do_buff(key_arr: List[KeyType]) -> None:
    """
    上Buff，之后等待随机时间
    
    Args:
        key_arr: Buff技能组合
    """
    wait_time = random.uniform(1, 1.5)
    do_command_wait_time(key_arr, wait_time)


def do_run(key: KeyType, span: float) -> None:
    """
    跑动指定时间
    
    Args:
        key: 方向键
        span: 持续时间（秒）
    """
    keyboard.press(key)
    time.sleep(random.uniform(50, 100) / 1000)
    keyboard.release(key)
    time.sleep(random.uniform(50, 100) / 1000)

    keyboard.press(key)
    time.sleep(span)
    keyboard.release(key)
    time.sleep(random.uniform(50, 100) / 1000)


def release_all_direct() -> None:
    """释放所有方向键"""
    for d in SINGLE_DIRECTIONS:
        keyboard.release(direct_dic[d])
        time.sleep(0.02)


def move(
    direct: str,
    walk: bool = False,
    pressed_direct_cache: Optional[str] = None,
    press_delay: float = 0.1,
    release_delay: float = 0.1,
    pickup: bool = False
) -> Optional[str]:
    """
    移动角色到指定方向
    
    Args:
        direct: 目标方向
        walk: 是否为走（否则为跑）
        pressed_direct_cache: 之前按下的方向缓存
        press_delay: 按键延迟
        release_delay: 释放延迟
        pickup: 是否为拾取模式
        
    Returns:
        当前方向，如果释放了则返回None
    """
    result = direct
    release_delay = 0.05
    press_delay = 0.05
    
    # 单方向移动
    if direct in SINGLE_DIRECTIONS:
        if pressed_direct_cache is not None:
            if pressed_direct_cache != direct:
                release_all_direct()
                keyboard.press(direct_dic[direct])

                if not walk:
                    time.sleep(press_delay)
                    keyboard.release(direct_dic[direct])
                    time.sleep(release_delay)
                    keyboard.press(direct_dic[direct])
                else:
                    if pickup:
                        time.sleep(0.05)
                        keyboard.release(direct_dic[direct])
                        result = None
        else:
            keyboard.press(direct_dic[direct])
            if not walk:
                time.sleep(press_delay)
                keyboard.release(direct_dic[direct])
                time.sleep(release_delay)
                keyboard.press(direct_dic[direct])
            else:
                if pickup:
                    time.sleep(0.05)
                    keyboard.release(direct_dic[direct])
                    result = None
    else:
        # 双方向移动（斜向）
        left_or_right = direct.strip().split("_")[0]
        up_or_down = direct.strip().split("_")[1]
        
        if pressed_direct_cache is not None:
            if pressed_direct_cache != direct:
                release_all_direct()

                if not walk:
                    keyboard.press(direct_dic[left_or_right])
                    time.sleep(press_delay)
                    keyboard.release(direct_dic[left_or_right])
                    time.sleep(release_delay)
                    keyboard.press(direct_dic[left_or_right])
                    time.sleep(press_delay)
                else:
                    keyboard.press(direct_dic[left_or_right])

                keyboard.press(direct_dic[up_or_down])

                if walk and pickup:
                    time.sleep(0.05)
                    keyboard.release(direct_dic[left_or_right])
                    keyboard.release(direct_dic[up_or_down])
                    result = None
        else:
            if not walk:
                keyboard.press(direct_dic[left_or_right])
                time.sleep(press_delay)
                keyboard.release(direct_dic[left_or_right])
                time.sleep(release_delay)
                keyboard.press(direct_dic[left_or_right])
                time.sleep(press_delay)
            else:
                keyboard.press(direct_dic[left_or_right])

            keyboard.press(direct_dic[up_or_down])

            if walk and pickup:
                time.sleep(0.05)
                keyboard.release(direct_dic[left_or_right])
                keyboard.release(direct_dic[up_or_down])
                result = None

    return result
