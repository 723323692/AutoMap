# -*- coding:utf-8 -*-
"""
自定义线程池实现
"""

__author__ = "723323692"
__version__ = '1.0'

import concurrent.futures
from concurrent.futures import Future
import threading
from typing import Callable, Any, Optional


class SingleTaskThreadPool:
    """单任务线程池 - 同时只允许一个任务运行"""
    
    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._lock = threading.Lock()
        self._task_running = False

    def submit(self, func: Callable, *args, **kwargs) -> Optional[Future]:
        """
        提交任务，如果已有任务运行则忽略
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Future对象，如果任务被忽略则返回None
        """
        with self._lock:
            if not self._task_running:
                self._task_running = True
                future = self.executor.submit(func, *args, **kwargs)
                future.add_done_callback(self._on_task_done)
                return future
            return None

    def _on_task_done(self, future: Future):
        with self._lock:
            self._task_running = False

    def shutdown(self, wait: bool = True):
        """关闭线程池"""
        self.executor.shutdown(wait=wait)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False


class LimitedTaskThreadPool:
    """有限任务线程池 - 限制同时运行的任务数量"""
    
    def __init__(self, max_workers: int):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
        self._running_tasks = 0
        self.max_workers = max_workers

    def submit(self, func: Callable, *args, **kwargs) -> Optional[Future]:
        """
        提交任务，如果达到最大任务数则忽略
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Future对象，如果任务被忽略则返回None
        """
        with self._lock:
            if self._running_tasks < self.max_workers:
                self._running_tasks += 1
                future = self.executor.submit(func, *args, **kwargs)
                future.add_done_callback(self._on_task_done)
                return future
            return None

    def _on_task_done(self, future: Future):
        with self._lock:
            self._running_tasks -= 1

    def shutdown(self, wait: bool = True):
        """关闭线程池"""
        self.executor.shutdown(wait=wait)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False


# 保持向后兼容的别名
ThreadPoolExecutor = LimitedTaskThreadPool


if __name__ == '__main__':
    import time
    
    def worker(x: int) -> int:
        print(f'Working on {x}')
        time.sleep(3)
        return x * x

    with LimitedTaskThreadPool(max_workers=2) as pool:
        pool.submit(worker, 1)
        time.sleep(1)
        pool.submit(worker, 2)
        time.sleep(1)
        pool.submit(worker, 3)
        time.sleep(1)
        pool.submit(worker, 4)
        time.sleep(10)
