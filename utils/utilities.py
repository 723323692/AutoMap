# -*- coding:utf-8 -*-
"""
通用工具函数模块
"""

__author__ = "723323692"
__version__ = '1.0'

import hashlib
import random
from typing import List, Tuple, Optional, Union

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

# 类型别名
Point = Tuple[int, int]
BBox = Tuple[Point, Point]
BBoxWithConf = Tuple[Point, Point, float]
Color = Union[Tuple[int, int, int], List[int]]


def plot_one_box(
    xyxy: Union[np.ndarray, List[float]],
    img: np.ndarray,
    color: Optional[Color] = None,
    label: Optional[str] = None,
    line_thickness: Optional[int] = None
) -> None:
    """
    在图像上绘制一个边界框
    
    Args:
        xyxy: 边界框坐标 [x1, y1, x2, y2]
        img: 要绘制的图像
        color: 边框颜色 (B, G, R)
        label: 标签文本
        line_thickness: 线条粗细
    """
    tl = line_thickness or round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1
    color = color or [random.randint(0, 255) for _ in range(3)]
    c1, c2 = (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3]))
    cv2.rectangle(img, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
    if label:
        tf = max(tl - 1, 1)
        t_size = cv2.getTextSize(label, 0, fontScale=tl / 3, thickness=tf)[0]
        c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
        cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)
        cv2.putText(img, label, (c1[0], c1[1] - 2), 0, tl / 3, [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)


def match_template(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8
) -> List[BBox]:
    """
    模板匹配，返回所有匹配位置
    
    Args:
        image: 源图像
        template: 模板图像
        threshold: 匹配阈值
        
    Returns:
        匹配矩形列表 [((x1,y1), (x2,y2)), ...]
    """
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(result >= threshold)
    matches = []
    for pt in zip(*loc[::-1]):
        bottom_right = (pt[0] + template.shape[1], pt[1] + template.shape[0])
        matches.append((pt, bottom_right))
    return matches


def match_template_by_roi(
    image: np.ndarray,
    roi_xywh: Tuple[int, int, int, int],
    template: np.ndarray,
    threshold: float = 0.8
) -> List[BBox]:
    """
    在ROI区域内进行模板匹配
    
    Args:
        image: 源图像
        roi_xywh: ROI区域 (x, y, width, height)
        template: 模板图像
        threshold: 匹配阈值
        
    Returns:
        匹配矩形列表（坐标相对于原图）
    """
    x, y, w, h = roi_xywh
    roi = image[y:y + h, x:x + w]
    t_h, t_w = template.shape[:2]

    result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(result >= threshold)
    matches = []
    for pt in zip(*loc[::-1]):
        left_top = (pt[0] + x, pt[1] + y)
        right_bottom = (left_top[0] + t_w, left_top[1] + t_h)
        matches.append((left_top, right_bottom))
    return matches


def match_template_one(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8
) -> List[BBox]:
    """
    模板匹配，返回置信度最高的一个
    
    Args:
        image: 源图像
        template: 模板图像
        threshold: 匹配阈值
        
    Returns:
        匹配结果列表（最多一个元素）
    """
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        pt = max_loc
        bottom_right = (pt[0] + template.shape[1], pt[1] + template.shape[0])
        return [(pt, bottom_right)]
    return []


def match_template_one_with_conf(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8
) -> List[BBoxWithConf]:
    """
    模板匹配，返回置信度最高的一个（带置信度）
    
    Args:
        image: 源图像
        template: 模板图像
        threshold: 匹配阈值
        
    Returns:
        匹配结果列表 [((x1,y1), (x2,y2), confidence)]
    """
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        pt = max_loc
        bottom_right = (pt[0] + template.shape[1], pt[1] + template.shape[0])
        return [(pt, bottom_right, max_val)]
    return []


def compare_images(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    比较两张图片的相似度（使用SSIM）
    
    Args:
        img1: 第一张图片
        img2: 第二张图片
        
    Returns:
        相似度分数 (0-1)，如果图片无效返回0
    """
    # 检查图片是否为空
    if img1 is None or img2 is None:
        return 0.0
    if img1.size == 0 or img2.size == 0:
        return 0.0
    
    try:
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        return ssim(gray1, gray2)
    except cv2.error:
        return 0.0


def match_template_with_confidence(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8
) -> List[BBoxWithConf]:
    """
    模板匹配，返回所有匹配位置及置信度
    
    Args:
        image: 源图像
        template: 模板图像
        threshold: 匹配阈值
        
    Returns:
        匹配结果列表 [((x1,y1), (x2,y2), confidence), ...]
    """
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(result >= threshold)

    matches = []
    for pt in zip(*loc[::-1]):
        match_score = result[pt[1], pt[0]]
        bottom_right = (pt[0] + template.shape[1], pt[1] + template.shape[0])
        matches.append((pt, bottom_right, match_score))
    return matches


def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
    """
    将十六进制颜色转换为BGR三元组
    
    Args:
        hex_color: 十六进制颜色字符串，如 "#523294"
        
    Returns:
        BGR颜色元组 (B, G, R)
    """
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return (b, g, r)


def calculate_sha256(file_path: str) -> str:
    """
    计算文件的SHA-256哈希值
    
    Args:
        file_path: 文件路径
        
    Returns:
        SHA-256哈希值字符串
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()
