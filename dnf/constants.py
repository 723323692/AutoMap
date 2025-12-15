# -*- coding:utf-8 -*-
"""
DNF脚本常量定义 - 集中管理UI坐标和其他魔法数字
"""

__author__ = "723323692"
__version__ = '1.0'

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class UICoordinates:
    """UI坐标常量（基于1067x600窗口）"""
    
    # 畅玩任务按钮
    DAILY_TASK_BTN: Tuple[int, int] = (767, 542)
    
    # 每日任务领取位置
    DAILY_REWARD_1: Tuple[int, int] = (494, 444)
    DAILY_REWARD_2: Tuple[int, int] = (494, 361)
    DAILY_REWARD_3: Tuple[int, int] = (494, 295)
    DAILY_REWARD_4: Tuple[int, int] = (494, 230)
    DAILY_REWARD_5: Tuple[int, int] = (494, 165)
    DAILY_REWARD_ALL: Tuple[int, int] = (497, 504)
    
    # 菜单相关
    MENU_BTN: Tuple[int, int] = (832, 576)
    SELECT_ROLE_BTN: Tuple[int, int] = (506, 504)
    
    # 传送相关
    TELEPORT_SAILIYA: Tuple[int, int] = (818, 543)
    
    # 地图选择
    MAP_ZHUIZONG: Tuple[int, int] = (357, 106)  # 妖怪追踪
    MAP_JIANMIE: Tuple[int, int] = (551, 176)   # 妖气歼灭
    MAP_DIEDANG: Tuple[int, int] = (620, 305)   # 跌宕群岛
    MAP_XIAOSUO: Tuple[int, int] = (835, 309)   # 萧索的回廊
    MAP_ABYSS: Tuple[int, int] = (720, 470)     # 深渊
    
    # 仓库
    WAREHOUSE_BTN: Tuple[int, int] = (366, 353)
    WAREHOUSE_GOLD_BTN: Tuple[int, int] = (413, 465)
    
    # 赛丽亚商店
    SAILIYA_NPC: Tuple[int, int] = (556, 189)
    SHOP_EQUIPMENT_TAB: Tuple[int, int] = (632, 275)
    
    # 物品栏
    INVENTORY_TALISMAN: Tuple[int, int] = (785, 70)
    TALISMAN_DROPDOWN: Tuple[int, int] = (828, 93)
    TALISMAN_OPTION_2: Tuple[int, int] = (870, 149)
    TALISMAN_APPLY: Tuple[int, int] = (947, 174)
    
    # 活动图标
    ACTIVITY_ICON: Tuple[int, int] = (744, 577)
    ACTIVITY_LIVE_BTN: Tuple[int, int] = (843, 516)
    ACTIVITY_LIVE_CLICK: Tuple[int, int] = (712, 517)
    
    # 邮件
    MAIL_RECEIVE_BTN: Tuple[int, int] = (414, 458)
    
    # 疲劳值识别区域
    FATIGUE_REGION: Tuple[int, int, int, int] = (842, 592, 857, 597)
    
    # 鼠标重置位置
    MOUSE_RESET: Tuple[int, int] = (1027, 561)
    MOUSE_FATIGUE_HOVER: Tuple[int, int] = (875, 594)


@dataclass(frozen=True)
class DetectionParams:
    """检测参数常量"""
    
    # 高度偏移
    BOSS_HEIGHT: int = 120
    MONSTER_HEIGHT: int = 57
    ELITE_MONSTER_HEIGHT: int = 100
    DOOR_HEIGHT: int = 32
    LOOT_HEIGHT: int = 0
    
    # 攻击范围
    ATTACK_X: int = 200
    ATTACK_Y: int = 80
    
    # 过门范围
    DOOR_HIT_X: int = 25
    DOOR_HIT_Y: int = 15
    
    # 拾取范围
    PICKUP_X: int = 25
    PICKUP_Y: int = 15


@dataclass(frozen=True)
class WindowSize:
    """窗口尺寸常量"""
    WIDTH: int = 1067
    HEIGHT: int = 600


# 创建全局实例
UI = UICoordinates()
DETECTION = DetectionParams()
WINDOW = WindowSize()
