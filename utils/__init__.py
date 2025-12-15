# -*- coding:utf-8 -*-
"""
工具模块包
"""

__author__ = "723323692"
__version__ = '1.0'

from utils.utilities import (
    plot_one_box,
    match_template,
    match_template_by_roi,
    match_template_one,
    match_template_one_with_conf,
    match_template_with_confidence,
    compare_images,
    hex_to_bgr,
    calculate_sha256,
)
from utils.custom_thread_pool_executor import (
    SingleTaskThreadPool,
    LimitedTaskThreadPool,
)
from utils.window_utils import (
    WindowCapture,
    get_window_handle,
    get_window_rect,
    capture_window_image,
    capture_window_BGRX,
    crop_image,
)

__all__ = [
    # utilities
    'plot_one_box',
    'match_template',
    'match_template_by_roi',
    'match_template_one',
    'match_template_one_with_conf',
    'match_template_with_confidence',
    'compare_images',
    'hex_to_bgr',
    'calculate_sha256',
    # thread pool
    'SingleTaskThreadPool',
    'LimitedTaskThreadPool',
    # window utils
    'WindowCapture',
    'get_window_handle',
    'get_window_rect',
    'capture_window_image',
    'capture_window_BGRX',
    'crop_image',
]
