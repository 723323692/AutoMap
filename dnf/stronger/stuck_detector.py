# -*- coding:utf-8 -*-
"""
卡死检测模块 - 检测角色是否卡住并尝试恢复
"""

__author__ = "723323692"
__version__ = '1.0'

import time
import random
from typing import Optional, Tuple, List
from dataclasses import dataclass, field

from dnf.stronger.logger_config import logger


@dataclass
class StuckState:
    """卡死状态"""
    is_stuck: bool = False
    stuck_time: float = 0.0
    stuck_position: Optional[Tuple[float, float]] = None
    stuck_room: Optional[Tuple[int, int]] = None
    recovery_attempts: int = 0


class StuckDetector:
    """
    卡死检测器
    
    通过监控角色位置和房间变化来检测是否卡住
    """
    
    def __init__(
        self,
        position_threshold: float = 30.0,
        time_threshold: float = 5.0,
        max_recovery_attempts: int = 3
    ):
        """
        初始化卡死检测器
        
        Args:
            position_threshold: 位置变化阈值，小于此值认为没有移动
            time_threshold: 时间阈值，超过此时间没有移动认为卡住
            max_recovery_attempts: 最大恢复尝试次数
        """
        self.position_threshold = position_threshold
        self.time_threshold = time_threshold
        self.max_recovery_attempts = max_recovery_attempts
        
        self._last_position: Optional[Tuple[float, float]] = None
        self._last_room: Optional[Tuple[int, int]] = None
        self._last_move_time: float = time.time()
        self._state = StuckState()
        self._position_history: List[Tuple[float, float, float]] = []  # (x, y, timestamp)
    
    def update(
        self,
        position: Optional[Tuple[float, float]],
        room: Optional[Tuple[int, int]] = None
    ) -> StuckState:
        """
        更新检测状态
        
        Args:
            position: 当前角色位置 (x, y)
            room: 当前房间 (row, col)
            
        Returns:
            当前卡死状态
        """
        now = time.time()
        
        if position is None:
            return self._state
        
        # 记录位置历史
        self._position_history.append((position[0], position[1], now))
        # 只保留最近10秒的历史
        self._position_history = [
            p for p in self._position_history 
            if now - p[2] < 10.0
        ]
        
        # 检查是否有移动
        if self._last_position is not None:
            distance = self._calculate_distance(position, self._last_position)
            
            if distance > self.position_threshold:
                # 有明显移动，重置状态
                self._last_move_time = now
                self._state.is_stuck = False
                self._state.recovery_attempts = 0
            else:
                # 没有明显移动，检查是否超时
                stuck_duration = now - self._last_move_time
                if stuck_duration > self.time_threshold:
                    if not self._state.is_stuck:
                        logger.warning(f"检测到角色卡住，已持续 {stuck_duration:.1f} 秒")
                    self._state.is_stuck = True
                    self._state.stuck_time = stuck_duration
                    self._state.stuck_position = position
                    self._state.stuck_room = room
        
        # 检查房间变化
        if room is not None and self._last_room is not None:
            if room != self._last_room:
                # 房间变化，重置状态
                self._last_move_time = now
                self._state.is_stuck = False
                self._state.recovery_attempts = 0
                logger.debug(f"房间变化: {self._last_room} -> {room}")
        
        self._last_position = position
        self._last_room = room
        
        return self._state
    
    def get_recovery_direction(self) -> Optional[str]:
        """
        获取恢复方向建议
        
        Returns:
            建议的移动方向
        """
        if not self._state.is_stuck:
            return None
        
        if self._state.recovery_attempts >= self.max_recovery_attempts:
            logger.error("恢复尝试次数已达上限")
            return None
        
        self._state.recovery_attempts += 1
        
        # 根据尝试次数选择不同的恢复策略
        directions = ["LEFT", "RIGHT", "UP", "DOWN", "LEFT_UP", "RIGHT_DOWN"]
        
        # 分析位置历史，尝试往相反方向移动
        if len(self._position_history) >= 2:
            first = self._position_history[0]
            last = self._position_history[-1]
            dx = last[0] - first[0]
            dy = last[1] - first[1]
            
            # 往相反方向移动
            if abs(dx) > abs(dy):
                return "LEFT" if dx > 0 else "RIGHT"
            else:
                return "UP" if dy > 0 else "DOWN"
        
        # 随机选择方向
        return random.choice(directions)
    
    def reset(self):
        """重置检测器状态"""
        self._last_position = None
        self._last_room = None
        self._last_move_time = time.time()
        self._state = StuckState()
        self._position_history.clear()
    
    def _calculate_distance(
        self,
        pos1: Tuple[float, float],
        pos2: Tuple[float, float]
    ) -> float:
        """计算两点距离"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5


class RoomStuckDetector:
    """
    房间卡死检测器
    
    检测是否在同一房间停留过长时间
    """
    
    def __init__(self, time_threshold: float = 60.0):
        """
        Args:
            time_threshold: 在同一房间的时间阈值（秒）
        """
        self.time_threshold = time_threshold
        self._current_room: Optional[Tuple[int, int]] = None
        self._room_enter_time: float = time.time()
    
    def update(self, room: Optional[Tuple[int, int]]) -> bool:
        """
        更新房间状态
        
        Args:
            room: 当前房间
            
        Returns:
            是否在同一房间停留过长
        """
        if room is None:
            return False
        
        now = time.time()
        
        if room != self._current_room:
            self._current_room = room
            self._room_enter_time = now
            return False
        
        duration = now - self._room_enter_time
        if duration > self.time_threshold:
            logger.warning(f"在房间 {room} 停留过长: {duration:.1f} 秒")
            return True
        
        return False
    
    def reset(self):
        """重置状态"""
        self._current_room = None
        self._room_enter_time = time.time()
