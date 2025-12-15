# -*- coding:utf-8 -*-
"""
怪物聚类分析模块
"""

__author__ = "723323692"
__version__ = '1.0'

from typing import List, Tuple, Optional

import numpy as np
from scipy.spatial.distance import pdist, squareform


class MonsterCluster:
    """怪物聚类分析器 - 用于找到怪物最密集的区域"""
    
    def __init__(self, monster_xywh_list: List[List[float]], max_distance: float = 400):
        """
        初始化聚类分析器
        
        Args:
            monster_xywh_list: 怪物位置列表 [[x, y, w, h], ...]
            max_distance: 聚类最大距离
        """
        self.monster_xywh_list = monster_xywh_list
        self.max_distance = max_distance
        self.coordinates = np.array([[m[0], m[1]] for m in monster_xywh_list]) if monster_xywh_list else np.array([])

    def find_densest_cluster(self) -> Tuple[Optional[List[float]], int]:
        """
        找到最密集的怪物聚类中心
        
        Returns:
            (中心坐标 [x, y], 聚类内怪物数量)
        """
        if len(self.coordinates) == 0:
            return None, 0

        # 计算所有点之间的距离矩阵
        dist_matrix = squareform(pdist(self.coordinates))

        max_count = 0
        best_center: Optional[np.ndarray] = None

        # 对每个点进行检查
        for i, point in enumerate(self.coordinates):
            # 找出在最大距离范围内的所有点
            in_range = dist_matrix[i] <= self.max_distance
            count = np.sum(in_range)

            if count > max_count:
                max_count = count
                # 计算在范围内的所有点的平均位置作为中心
                best_center = np.mean(self.coordinates[in_range], axis=0)

        return best_center.tolist() if best_center is not None else None, max_count


def find_densest_point(
    points: List[List[float]],
    max_distance: float = 400
) -> Tuple[Optional[List[float]], int]:
    """
    便捷函数：找到点集中最密集的区域中心
    
    Args:
        points: 点列表 [[x, y, ...], ...]
        max_distance: 聚类最大距离
        
    Returns:
        (中心坐标 [x, y], 聚类内点数量)
    """
    cluster = MonsterCluster(points, max_distance)
    return cluster.find_densest_cluster()
