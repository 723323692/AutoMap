# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'

import math
import os
import re

import cv2
import numpy as np

import config as config_
from dnf.stronger.logger_config import logger
from utils.monster_cluster import MonsterCluster
from utils.utilities import match_template_one


def try_again_is_disabled(img_again):
    """
    判断"再次挑战"是灰色还是金色,决定是否可以继续再次挑战
    # todo 计算两种情况的平均颜色值
    """

    hsv_roi = cv2.cvtColor(img_again, cv2.COLOR_BGR2HSV)
    # 定义灰色和金色的HSV范围
    gray_lower = np.array([0, 0, 70])
    gray_upper = np.array([180, 50, 220])
    gold_lower = np.array([20, 100, 100])
    gold_upper = np.array([30, 255, 255])
    # 创建掩膜
    gray_mask = cv2.inRange(hsv_roi, gray_lower, gray_upper)
    gold_mask = cv2.inRange(hsv_roi, gold_lower, gold_upper)
    # 计算掩膜中的非零像素数
    gray_count = cv2.countNonZero(gray_mask)
    gold_count = cv2.countNonZero(gold_mask)
    if gray_count > gold_count:
        again_is_gray = True
        logger.debug("再次挑战按钮禁用了")
    else:
        again_is_gray = False
    return again_is_gray


# todo 截好图传参，判断图片
def detect_try_again_button(full_screen_img):
    """
    识别"再次挑战"按钮的情况,按钮是否识别到,文本是否识别到,是否可以点击
    """
    # full_screen = window_utils.capture_window_BGRX(handle)
    gray_screenshot = cv2.cvtColor(full_screen_img, cv2.COLOR_BGR2GRAY)
    template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/try_again_gold_1067_600.jpg'),
                                cv2.IMREAD_COLOR)
    template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
    matches = match_template_one(gray_screenshot, template_again_gray, threshold=0.9)
    logger.debug(f'模板匹配"再次挑战": {len(matches)}')
    btn_exist = len(matches) > 0  # 按钮是否存在
    text_exist = False  # 文本是否识别到
    clickable = False  # 是否可以点击
    if len(matches) > 0:
        # 获取匹配区域的尺寸
        for (x1, y1), (x2, y2) in matches:
            # 截取匹配区域
            roi = full_screen_img[y1:y2, x1:x2]
            # 对截取的区域进行文字识别
            # text = pytesseract.image_to_string(roi, lang='chi_sim')
            # logger.debug(f"识别的文本: {text}")
            # if text.strip() == '再次挑战' or '挑战' in text:
            text_exist = True
            again_is_gray = try_again_is_disabled(roi)
            logger.debug(f"再次挑战禁用: {again_is_gray}")
            if not again_is_gray:
                clickable = True
    return btn_exist, text_exist, clickable


def detect_1and1_next_map_button(full_screen_img):
    """
    识别"再次挑战"按钮的情况,按钮是否识别到,文本是否识别到,是否可以点击
    """
    # full_screen = window_utils.capture_window_BGRX(handle)
    gray_screenshot = cv2.cvtColor(full_screen_img, cv2.COLOR_BGR2GRAY)
    template_again = cv2.imread(
        os.path.normpath(f'{config_.project_base_path}/assets/img/to_next_daily_map_1607_600.jpg'),
        cv2.IMREAD_COLOR)
    template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
    matches = match_template_one(gray_screenshot, template_again_gray, threshold=0.9)
    logger.debug(f'模板匹配 "前往下一地下城": {len(matches)}')
    btn_exist = len(matches) > 0  # 按钮是否存在
    text_exist = False  # 文本是否识别到
    clickable = False  # 是否可以点击
    if len(matches) > 0:
        # 获取匹配区域的尺寸
        for (x1, y1), (x2, y2) in matches:
            # 截取匹配区域
            roi = full_screen_img[y1:y2, x1:x2]
            # 对截取的区域进行文字识别
            # text = pytesseract.image_to_string(roi, lang='chi_sim')
            # logger.debug(f"识别的文本: {text}")
            # if text.strip() == '再次挑战' or '挑战' in text:
            text_exist = True
            again_is_gray = try_again_is_disabled(roi)
            logger.debug(f"再次挑战禁用: {again_is_gray}")
            if not again_is_gray:
                clickable = True
    return btn_exist, text_exist, clickable


def extract_fatigue_number(text):
    """
    从识别文本中提取正确的疲劳值
    :param text:
    :return:
    """
    if "/" not in text:
        return None
    # 去除空格
    cleaned_text = re.sub(r'\s+', '', text)
    cleaned_text = re.sub(r'[^\d/]', '', cleaned_text)

    # 提取第一个数字（斜杠前的部分）
    match = re.match(r'^(\d+)/', cleaned_text)
    return int(match.group(1)) if match else None


def get_closest_obj(obj_list, hero_xywh):
    """
    获取距离最近的目标
    
    Args:
        obj_list: 目标列表，每个元素为 [x, y, w, h]
        hero_xywh: 角色位置 [x, y, w, h]
        
    Returns:
        (最近的目标, 距离)
    """
    min_distance = float("inf")
    closest_obj = None
    
    for box in obj_list:
        dis = ((hero_xywh[0] - box[0]) ** 2 + (hero_xywh[1] - box[1]) ** 2) ** 0.5
        if dis < min_distance:
            closest_obj = box
            min_distance = dis
    
    return closest_obj, min_distance


def find_densest_monster_cluster(monster_xywh_list, role_attack_center, max_distance=400):
    """
    找密集堆
    """
    def distance(p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    if not monster_xywh_list:
        return None
    if len(monster_xywh_list) == 1:
        return monster_xywh_list[0][:2]
    if len(monster_xywh_list) == 2:
        x1, y1 = monster_xywh_list[0][:2]
        x2, y2 = monster_xywh_list[1][:2]
        if distance((x1, y1), (x2, y2)) <= max_distance:
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            return center
        else:
            distance1 = distance(role_attack_center, monster_xywh_list[0])
            distance2 = distance(role_attack_center, monster_xywh_list[1])
            if distance1 < distance2:
                return monster_xywh_list[0]
            else:
                return monster_xywh_list[1]

    cluster = MonsterCluster(monster_xywh_list, max_distance)
    result = cluster.find_densest_cluster()

    if result is None:
        return None
    else:
        center, count = result
        if count <= 1:
            monster_box, _ = get_closest_obj(monster_xywh_list, role_attack_center)
            return monster_box
        return center


def find_door_by_position(doors_xywh, position='RIGHT'):
    """
    根据方向 找最远的那个门
    """
    door_box_temp = None
    for box in doors_xywh:
        if position == 'UP':
            if door_box_temp is None or box[1] < door_box_temp[1]:
                door_box_temp = box
        elif position == 'DOWN':
            if door_box_temp is None or box[1] > door_box_temp[1]:
                door_box_temp = box
        elif position == 'LEFT':
            if door_box_temp is None or box[0] < door_box_temp[0]:
                door_box_temp = box
        elif position == 'RIGHT':
            if door_box_temp is None or box[0] > door_box_temp[0]:
                door_box_temp = box

    return door_box_temp


def exist_near(target_xywh, xywh_list, threshold=100):

    if len(xywh_list) == 0 or xywh_list is None:
        return False

    # 获取 material 的中心坐标
    material_center_x, material_center_y, _, _ = target_xywh  # material_box 直接使用中心坐标

    for door in xywh_list:
        door_center_x, door_center_y, _, _ = door  # door 也直接使用中心坐标

        # 计算中心坐标之间的距离
        distance = math.sqrt((material_center_x - door_center_x) ** 2 +
                             (material_center_y - door_center_y) ** 2)

        # 如果距离小于等于阈值，就返回 True
        if distance <= threshold:
            return door

    return False


def get_objs_in_range(target_xywh, xywh_list, threshold=100):
    res = []

    if len(xywh_list) == 0 or xywh_list is None:
        return res

    # 获取 material 的中心坐标
    material_center_x, material_center_y, _, _ = target_xywh  # material_box 直接使用中心坐标

    for door in xywh_list:
        door_center_x, door_center_y, _, _ = door  # door 也直接使用中心坐标

        # 计算中心坐标之间的距离
        distance = math.sqrt((material_center_x - door_center_x) ** 2 + (material_center_y - door_center_y) ** 2)

        # 如果距离小于等于阈值，就返回 True
        if distance <= threshold:
            # logger.info(f"{door},{target_xywh}--->{distance}")
            res.append(door)

    return res


def is_hero_in_region(hero_xywh, img_shape, direction, fraction):
    hero_x, hero_y, hero_w, hero_h = hero_xywh
    img_h, img_w = img_shape[:2]  # img_shape是(height, width, channels)格式

    if direction == 'UP':
        region_height = img_h * fraction
        return hero_y < region_height
    elif direction == 'DOWN':
        region_start = img_h * (1 - fraction)
        return hero_y > region_start
    elif direction == 'LEFT':
        region_width = img_w * fraction
        return hero_x < region_width
    elif direction == 'RIGHT':
        region_start = img_w * (1 - fraction)
        return hero_x > region_start


def get_opposite_direction(direction):
    # 定义方向与反方向的映射关系
    opposite_map = {
        "LEFT": "RIGHT",
        "RIGHT": "LEFT",
        "UP": "DOWN",
        "DOWN": "UP"
    }

    # 获取反方向，如果输入无效则返回提示
    return opposite_map.get(direction, None)
