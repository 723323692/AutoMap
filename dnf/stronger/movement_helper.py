# -*- coding:utf-8 -*-
"""
移动辅助模块 - 统一处理角色移动到目标位置的逻辑
"""

__author__ = "723323692"
__version__ = '1.0'

from typing import Tuple, Optional
from utils.keyboard_move_controller import MovementController


def calculate_move_direction(
    hero_pos: Tuple[float, float],
    target_pos: Tuple[float, float],
    y_threshold: float = 15,
    prefer_diagonal: bool = True
) -> Optional[str]:
    """
    计算从角色位置到目标位置的移动方向
    
    Args:
        hero_pos: 角色位置 (x, y)
        target_pos: 目标位置 (x, y)
        y_threshold: Y方向对齐阈值，小于此值认为Y方向已对齐
        prefer_diagonal: 是否优先使用斜向移动
        
    Returns:
        移动方向字符串，如 "RIGHT", "LEFT_UP" 等
    """
    dx = target_pos[0] - hero_pos[0]  # 正数表示目标在右边
    dy = target_pos[1] - hero_pos[1]  # 正数表示目标在下边
    abs_dx = abs(dx)
    abs_dy = abs(dy)
    
    # Y方向已经对齐，只需要水平移动
    if abs_dy < y_threshold:
        return "RIGHT" if dx > 0 else "LEFT" if dx < 0 else None
    
    # X方向已经对齐，只需要垂直移动
    if abs_dx < y_threshold:
        return "DOWN" if dy > 0 else "UP" if dy < 0 else None
    
    # 需要斜向或单向移动
    if prefer_diagonal and abs_dx > y_threshold and abs_dy > y_threshold:
        # 优先斜向移动
        if dx > 0 and dy < 0:
            return "RIGHT_UP"
        elif dx > 0 and dy > 0:
            return "RIGHT_DOWN"
        elif dx < 0 and dy < 0:
            return "LEFT_UP"
        else:
            return "LEFT_DOWN"
    
    # X方向距离更远，优先水平移动
    if abs_dx > abs_dy:
        if dx > 0 and dy < 0:
            return "RIGHT_UP" if prefer_diagonal else "RIGHT"
        elif dx > 0 and dy > 0:
            return "RIGHT_DOWN" if prefer_diagonal else "RIGHT"
        elif dx < 0 and dy < 0:
            return "LEFT_UP" if prefer_diagonal else "LEFT"
        else:
            return "LEFT_DOWN" if prefer_diagonal else "LEFT"
    # Y方向距离更远，优先垂直移动
    else:
        return "UP" if dy < 0 else "DOWN"


def move_to_target(
    mover: MovementController,
    hero_pos: Tuple[float, float],
    target_pos: Tuple[float, float],
    y_threshold: float = 15,
    move_mode: str = 'running',
    stop_immediately: bool = False
) -> Optional[str]:
    """
    移动角色到目标位置
    
    Args:
        mover: 移动控制器
        hero_pos: 角色位置 (x, y)
        target_pos: 目标位置 (x, y)
        y_threshold: Y方向对齐阈值
        move_mode: 移动模式 ('running' 或 'walking')
        stop_immediately: 是否立即停止（用于精确拾取）
        
    Returns:
        实际移动的方向
    """
    direction = calculate_move_direction(hero_pos, target_pos, y_threshold)
    
    if direction:
        if stop_immediately:
            mover.move_stop_immediately(target_direction=direction, move_mode=move_mode, stop=True)
        else:
            mover.move(target_direction=direction, move_mode=move_mode)
    
    return direction


def is_in_range(
    hero_pos: Tuple[float, float],
    target_pos: Tuple[float, float],
    range_x: float,
    range_y: float
) -> bool:
    """
    判断目标是否在范围内
    
    Args:
        hero_pos: 角色位置 (x, y)
        target_pos: 目标位置 (x, y)
        range_x: X方向范围
        range_y: Y方向范围
        
    Returns:
        是否在范围内
    """
    dx = abs(target_pos[0] - hero_pos[0])
    dy = abs(target_pos[1] - hero_pos[1])
    return dx < range_x and dy < range_y


def get_distance(pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
    """计算两点之间的距离"""
    return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5
