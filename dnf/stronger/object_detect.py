# -*- coding:utf-8 -*-
"""
CV目标检测模块 - 使用模板匹配进行特定目标检测
"""

__author__ = "723323692"
__version__ = '1.0'

import os
from typing import Dict, Any, Optional

import cv2
import numpy as np

import config as config_
from utils.utilities import match_template_by_roi


class ObjectDetector:
    """CV目标检测器 - 单例模式，避免重复加载模板"""
    
    _instance: Optional['ObjectDetector'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载所有检测模板"""
        template_configs = {
            "death": {
                "description": "幽灵状态",
                "path": "assets/img/death.png",
                "roi_xywh": (478, 422, 110, 26),
                "threshold": 0.8
            }
        }
        
        for name, config in template_configs.items():
            template_path = os.path.normpath(f'{config_.project_base_path}/{config["path"]}')
            template = cv2.imread(template_path)
            if template is not None:
                self._templates[name] = {
                    "template": template,
                    "roi_xywh": config["roi_xywh"],
                    "threshold": config["threshold"]
                }
    
    def detect(self, image: np.ndarray, targets: Optional[list] = None) -> Dict[str, Any]:
        """
        执行目标检测
        
        Args:
            image: 输入图像
            targets: 要检测的目标列表，None表示检测所有
            
        Returns:
            检测结果字典
        """
        results = {}
        detect_targets = targets or self._templates.keys()
        
        for name in detect_targets:
            if name in self._templates:
                config = self._templates[name]
                results[name] = match_template_by_roi(
                    image, 
                    config['roi_xywh'], 
                    config['template'], 
                    config['threshold']
                )
        
        return results


# 全局检测器实例
_detector: Optional[ObjectDetector] = None


def object_detection_cv(image: np.ndarray) -> Dict[str, Any]:
    """
    目标检测（兼容旧接口）
    
    Args:
        image: 输入图像
        
    Returns:
        检测结果字典
    """
    global _detector
    if _detector is None:
        _detector = ObjectDetector()
    return _detector.detect(image)
