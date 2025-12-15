# -*- coding:utf-8 -*-
"""
固定长度队列模块
"""

__author__ = "723323692"
__version__ = '1.0'

from collections import deque
from typing import TypeVar, Generic, Optional, List, Tuple, Any

T = TypeVar('T')


class FixedLengthQueue(Generic[T]):
    """固定长度队列 - 超出长度时自动移除最老的元素"""
    
    def __init__(self, max_length: int = 5):
        """
        初始化固定长度队列
        
        Args:
            max_length: 队列最大长度
        """
        self.queue: deque[T] = deque(maxlen=max_length)

    def enqueue(self, item: T) -> None:
        """
        入队，队列满时自动移除最老元素
        
        Args:
            item: 要入队的元素
        """
        self.queue.append(item)

    def peek(self) -> Optional[T]:
        """
        查看队首元素（不移除）
        
        Returns:
            队首元素，队列为空时返回None
        """
        return self.queue[0] if not self.is_empty() else None

    def dequeue(self) -> Optional[T]:
        """
        出队
        
        Returns:
            队首元素，队列为空时返回None
        """
        if not self.is_empty():
            return self.queue.popleft()
        return None

    def is_empty(self) -> bool:
        """判断队列是否为空"""
        return len(self.queue) == 0

    def size(self) -> int:
        """返回队列当前大小"""
        return len(self.queue)

    def clear(self) -> None:
        """清空队列"""
        self.queue.clear()

    def __repr__(self) -> str:
        return f"FixedLengthQueue(max_length={self.queue.maxlen}, current_size={len(self.queue)})"

    def coords_is_stable(self, threshold: float = 15, window_size: int = 20) -> bool:
        """
        检查最近的坐标是否稳定（用于检测角色是否卡住）
        
        Args:
            threshold: 坐标偏差阈值
            window_size: 检查窗口大小
            
        Returns:
            坐标是否稳定
        """
        if len(self.queue) < window_size:
            return False

        recent_coords: List[Tuple[float, float]] = []
        self.queue.rotate(window_size)
        for _ in range(window_size):
            recent_coords.append(self.queue[0])
            self.queue.rotate(-1)

        avg_x = sum(coord[0] for coord in recent_coords) / window_size
        avg_y = sum(coord[1] for coord in recent_coords) / window_size

        for x, y in recent_coords:
            if abs(x - avg_x) > threshold or abs(y - avg_y) > threshold:
                return False

        return True

    def room_is_same(self, min_size: int = 20) -> bool:
        """
        检查最近的房间是否相同（用于检测是否卡在同一房间）
        
        Args:
            min_size: 最小检查数量
            
        Returns:
            房间是否相同
        """
        if len(self.queue) < min_size:
            return False

        recent_rooms: List[Any] = []
        self.queue.rotate(min_size)
        for _ in range(min_size):
            recent_rooms.append(self.queue[0])
            self.queue.rotate(-1)

        recent_room = recent_rooms[0]

        for room in recent_rooms:
            if recent_room != room:
                return False
        return True


if __name__ == "__main__":
    fq: FixedLengthQueue[Tuple[int, int]] = FixedLengthQueue(max_length=50)
    coordinates = [
        (100, 100), (101, 101), (102, 102), (110, 110), (110, 110),
        (110, 110), (110, 110), (110, 110), (110, 110), (110, 110)
    ]

    for coord in coordinates:
        fq.enqueue(coord)

    print(fq.coords_is_stable(threshold=5, window_size=9))
