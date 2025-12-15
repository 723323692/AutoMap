# -*- coding:utf-8 -*-
"""
DNF脚本模块包
"""

__author__ = "723323692"
__version__ = '1.0'

from dnf.dnf_config import (
    window_title,
    direct_dic,
    key_try_again,
    key_return_to_town,
    Key_collect_loot,
    Key_collect_role,
    key_pause_script,
    key_stop_script,
    key_start_script,
    enable_picture_log,
)
from dnf.common import (
    COLOR_RED,
    COLOR_GREEN,
    COLOR_BLUE,
    COLOR_YELLOW,
    COLOR_PURPLE,
    KeyboardController,
    DisplayThread,
    analyse_det_result_common,
    draw_debug_points,
    generate_random_colors,
)
from dnf.constants import (
    UI,
    DETECTION,
    WINDOW,
)

__all__ = [
    # config
    'window_title',
    'direct_dic',
    'key_try_again',
    'key_return_to_town',
    'Key_collect_loot',
    'Key_collect_role',
    'key_pause_script',
    'key_stop_script',
    'key_start_script',
    'enable_picture_log',
    # common
    'COLOR_RED',
    'COLOR_GREEN',
    'COLOR_BLUE',
    'COLOR_YELLOW',
    'COLOR_PURPLE',
    'KeyboardController',
    'DisplayThread',
    'analyse_det_result_common',
    'draw_debug_points',
    'generate_random_colors',
    # constants
    'UI',
    'DETECTION',
    'WINDOW',
]
