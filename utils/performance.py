# -*- coding:utf-8 -*-
"""
性能监控工具模块
"""

__author__ = "723323692"
__version__ = '1.0'

import time
from functools import wraps
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


class FPSCounter:
    """帧率计数器"""
    
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.timestamps: list = []
    
    def tick(self) -> float:
        """记录一帧，返回当前FPS"""
        now = time.time()
        self.timestamps.append(now)
        
        # 保持窗口大小
        if len(self.timestamps) > self.window_size:
            self.timestamps.pop(0)
        
        # 计算FPS
        if len(self.timestamps) < 2:
            return 0.0
        
        elapsed = self.timestamps[-1] - self.timestamps[0]
        if elapsed <= 0:
            return 0.0
        
        return (len(self.timestamps) - 1) / elapsed
    
    def reset(self):
        """重置计数器"""
        self.timestamps.clear()


class Timer:
    """计时器上下文管理器"""
    
    def __init__(self, name: str = "", log: bool = False):
        self.name = name
        self.log = log
        self.start_time = 0.0
        self.elapsed = 0.0
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start_time
        if self.log and self.name:
            logger.debug(f"{self.name}: {self.elapsed*1000:.2f}ms")


def timing(func: Callable) -> Callable:
    """计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__name__}: {elapsed*1000:.2f}ms")
        return result
    return wrapper


class RateLimiter:
    """速率限制器 - 限制每秒执行次数"""
    
    def __init__(self, max_rate: float):
        """
        Args:
            max_rate: 每秒最大执行次数
        """
        self.min_interval = 1.0 / max_rate
        self.last_time = 0.0
    
    def wait(self) -> float:
        """等待直到可以执行，返回实际等待时间"""
        now = time.time()
        elapsed = now - self.last_time
        
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            time.sleep(wait_time)
            self.last_time = time.time()
            return wait_time
        
        self.last_time = now
        return 0.0
    
    def can_execute(self) -> bool:
        """检查是否可以执行（不等待）"""
        return time.time() - self.last_time >= self.min_interval
