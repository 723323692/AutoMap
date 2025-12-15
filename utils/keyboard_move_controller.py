# -*- coding:utf-8 -*-
"""
键盘移动控制器模块 - 用于控制游戏角色移动
"""

__author__ = "723323692"
__version__ = '1.0'

import threading
import time
from enum import Enum
from typing import Optional, Set, List

from pynput.keyboard import Key, Controller


class Direction(Enum):
    """移动方向枚举"""
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    RIGHT_UP = "RIGHT_UP"
    RIGHT_DOWN = "RIGHT_DOWN"
    LEFT_UP = "LEFT_UP"
    LEFT_DOWN = "LEFT_DOWN"


class MoveMode(Enum):
    """移动模式枚举"""
    WALKING = "walking"
    RUNNING = "running"


# 方向到按键的映射
_DIRECTION_KEY_MAP = {
    Direction.UP: [Key.up],
    Direction.DOWN: [Key.down],
    Direction.LEFT: [Key.left],
    Direction.RIGHT: [Key.right],
    Direction.RIGHT_UP: [Key.right, Key.up],
    Direction.RIGHT_DOWN: [Key.right, Key.down],
    Direction.LEFT_UP: [Key.left, Key.up],
    Direction.LEFT_DOWN: [Key.left, Key.down]
}


def _get_direction_keys(direction: str) -> List[Key]:
    """获取方向对应的按键列表"""
    return _DIRECTION_KEY_MAP[Direction(direction)]


def _get_main_direction(direction: Optional[str]) -> Optional[str]:
    """获取方向的主方向（用于跑步）"""
    if direction is None:
        return None
    if "RIGHT" in direction:
        return "RIGHT"
    elif "LEFT" in direction:
        return "LEFT"
    return direction


class MovementController:
    """
    移动控制器 - 管理角色的移动状态和按键
    
    支持走路和跑步两种模式，以及8个方向的移动
    """
    
    def __init__(self):
        self.keyboard = Controller()
        self.current_direction: Optional[str] = None
        self.current_mode: Optional[str] = None
        self.pressed_keys: Set[Key] = set()
        self._lock = threading.RLock()

    def _press_key(self, key: Key) -> None:
        """按下按键"""
        with self._lock:
            self.keyboard.press(key)
            self.pressed_keys.add(key)
            time.sleep(0.02)

    def _release_key(self, key: Key) -> None:
        """释放按键"""
        with self._lock:
            self.keyboard.release(key)
            self.pressed_keys.discard(key)
            time.sleep(0.02)

    def _release_all_keys(self) -> None:
        """释放所有按键"""
        with self._lock:
            all_direction_keys = {Key.up, Key.down, Key.left, Key.right}
            for key in all_direction_keys:
                self.keyboard.release(key)
            self.pressed_keys.clear()
            self.current_direction = None
            self.current_mode = None

    def _handle_walking_direction_change(self, target_direction: str) -> None:
        """处理走路状态下的方向改变"""
        with self._lock:
            if not self.current_direction:
                for key in _get_direction_keys(target_direction):
                    self._press_key(key)
                return

            target_keys = set(_get_direction_keys(target_direction))
            current_keys = set(_get_direction_keys(self.current_direction))

            keys_to_press = target_keys - current_keys
            keys_to_release = current_keys - target_keys

            for key in keys_to_release:
                self._release_key(key)
            for key in keys_to_press:
                self._press_key(key)

    def _setup_running(self, direction: str) -> None:
        """设置跑步状态"""
        with self._lock:
            self._release_all_keys()

            main_key: Optional[Key] = None
            if "RIGHT" in direction:
                main_key = Key.right
            elif "LEFT" in direction:
                main_key = Key.left

            if main_key:
                # 双击实现跑步
                self._press_key(main_key)
                self._release_key(main_key)
                self._press_key(main_key)

            # 添加垂直方向
            if "UP" in direction:
                self._press_key(Key.up)
            elif "DOWN" in direction:
                self._press_key(Key.down)

    def move_stop_immediately(
        self,
        target_direction: str,
        move_mode: str = 'running',
        stop: bool = False
    ) -> None:
        """
        移动后立即停止
        
        Args:
            target_direction: 目标方向
            move_mode: 移动模式
            stop: 是否立即停止
        """
        with self._lock:
            self.move(target_direction, move_mode)
            if stop:
                time.sleep(0.04)
                self._release_all_keys()

    def move(self, target_direction: Optional[str], move_mode: str = 'running') -> None:
        """
        移动角色到指定方向
        
        Args:
            target_direction: 目标方向
            move_mode: 移动模式 ("walking" 或 "running")
        """
        with self._lock:
            if not target_direction:
                return

            # 如果方向和模式都没变，无需操作
            if target_direction == self.current_direction and move_mode == self.current_mode:
                return

            direction_enum = Direction(target_direction)
            mode_enum = MoveMode(move_mode)

            if mode_enum == MoveMode.RUNNING:
                current_main = _get_main_direction(self.current_direction)
                target_main = _get_main_direction(direction_enum.value)

                if current_main != target_main or self.current_mode != MoveMode.RUNNING.value:
                    self._setup_running(direction_enum.value)
                else:
                    # 主方向相同，只处理垂直方向变化
                    current_dir = self.current_direction or ""
                    target_dir = direction_enum.value
                    
                    if "UP" in current_dir and "UP" not in target_dir:
                        self._release_key(Key.up)
                    elif "DOWN" in current_dir and "DOWN" not in target_dir:
                        self._release_key(Key.down)

                    if "UP" in target_dir and "UP" not in current_dir:
                        self._press_key(Key.up)
                    elif "DOWN" in target_dir and "DOWN" not in current_dir:
                        self._press_key(Key.down)
            else:
                # 走路模式
                if self.current_mode == MoveMode.RUNNING.value:
                    self._release_all_keys()
                self._handle_walking_direction_change(direction_enum.value)

            self.current_direction = direction_enum.value
            self.current_mode = mode_enum.value

    def get_current_direction(self) -> Optional[str]:
        """获取当前移动方向"""
        with self._lock:
            return self.current_direction

    def stop(self) -> None:
        """停止移动"""
        self._release_all_keys()
