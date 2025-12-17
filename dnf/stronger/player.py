# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'

import os
import time

import cv2
# import easyocr
import numpy as np
from pynput.keyboard import Key
from pynput.mouse import Button
from pathlib import Path
from skimage.metrics import structural_similarity as ssim

import config as config_
from dnf.stronger.method import (
    extract_fatigue_number
)
from dnf.stronger.logger_config import logger
from utils import keyboard_utils as kbu
from utils import mouse_utils as mu
from utils import window_utils as window_utils
from utils.utilities import (
    match_template, compare_images,
    match_template_one,
    match_template_with_confidence,
    match_template_one_with_conf
)

reader = None


# todo x,y如果传了，没传自己获取
def sale_equipment_to_sailiya(x, y):
    """
    一键出售装备,给赛丽亚
    """
    logger.info('一键出售装备,给赛丽亚')
    # 点击赛丽亚
    mu.do_smooth_move_to(x + 556, y + 189)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.1)
    # 点击弹出的商店
    cur_x, cur_y = mu.get_current_position()
    mu.do_smooth_move_to(cur_x + 51, cur_y + 51)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    # 点击装备栏,准备卖出
    mu.do_smooth_move_to(x + 632, y + 275)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.1)
    # 按下a,一键出售
    kbu.do_press('a')
    # 按下a,一键选择出售
    kbu.do_press('a')
    # 点击卖出
    kbu.do_press(Key.space)
    time.sleep(0.2)

    # 计算弹出的确认按钮位置
    # cur_x, cur_y = mu.get_current_position()
    # mu.do_smooth_move_to(cur_x - 92, cur_y)
    # time.sleep(0.5)
    # mu.do_click(Button.left)
    kbu.do_press(Key.space)
    time.sleep(0.1)
    # 两下esc完全关闭商店
    kbu.do_press(Key.esc)
    time.sleep(0.2)
    kbu.do_press(Key.esc)
    time.sleep(0.2)


def transfer_materials_to_account_vault(x, y):
    """
    转移材料到账号金库
    """
    logger.info('转移材料到账号金库')
    # 点击仓库
    mu.do_smooth_move_to(x + 366, y + 353)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(1)
    # 两下tab切换到账号金库
    # kbu.do_press(Key.tab)
    # time.sleep(0.2)
    # kbu.do_press(Key.tab)
    # time.sleep(0.2)
    # 按下a,一键转移物品
    kbu.do_press('a')
    time.sleep(0.2)
    # 空格,确定
    kbu.do_press(Key.space)
    time.sleep(1.5)
    kbu.do_press(Key.space)
    time.sleep(0.2)

    # esc 取消仓库
    kbu.do_press(Key.esc)
    time.sleep(0.2)


def transfer_gold_to_account_vault(x, y):
    """
    转移金币到账号金库
    """
    logger.info('转移金币到账号金库')
    # 点击仓库
    mu.do_smooth_move_to(x + 366, y + 353)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    # 两下tab切换到账号金库
    kbu.do_press(Key.tab)
    time.sleep(0.1)
    kbu.do_press(Key.tab)
    time.sleep(0.1)

    # 整理金币到账号金库
    mu.do_smooth_move_to(x + 413, y + 465)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)

    # esc 取消仓库
    kbu.do_press(Key.esc)
    time.sleep(0.2)


def finish_daily_challenge(x, y, daily1and1=False):
    """
    点击每日任务
    """
    # 点击畅玩任务(1446,1108)，从下往上依次点击一遍（需要移动鼠标）(1006,838) 1007,711  1004,599 1006,494
    logger.info('点击畅玩任务,完成每日任务')
    mu.do_smooth_move_to(x + 767, y + 542)  # 不等比
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    if daily1and1:
        mu.do_smooth_move_to(x + 494, y + 444)
        time.sleep(0.1)
        mu.do_click(Button.left)
        time.sleep(0.1)
    mu.do_smooth_move_to(x + 494, y + 361)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    mu.do_smooth_move_to(x + 494, y + 295)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    mu.do_smooth_move_to(x + 494, y + 230)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    mu.do_smooth_move_to(x + 494, y + 165)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    # esc关闭畅玩任务
    kbu.do_press(Key.esc)
    time.sleep(0.2)


def finish_daily_challenge_by_all(x, y, daily1and1=False):
    """
    点击每日任务
    """
    # 点击畅玩任务，点两次全部领取
    logger.info('点击畅玩任务,完成每日任务')
    mu.do_smooth_move_to(x + 767, y + 542)  # 不等比
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(0.1)
    mu.do_smooth_move_to(x + 497, y + 504)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.2)
    kbu.do_press(Key.space)
    time.sleep(0.4)
    mu.do_click(Button.left)
    time.sleep(0.2)
    # esc关闭畅玩任务
    kbu.do_press(Key.esc)
    time.sleep(0.3)


def teleport_to_sailiya(x, y):
    """
    刷了图的情况下(图标位置不一样,刷图第三个,不刷图第四个),鼠标移动到瞬移赛丽亚旅馆
    都一样了 都是第四个
    """
    logger.info('瞬移赛丽亚旅馆')
    # 鼠标移动到瞬移赛丽亚旅馆
    mu.do_smooth_move_to(x + 818, y + 543)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.2)
    kbu.do_press(Key.space)
    time.sleep(0.2)
    kbu.do_press_with_time(Key.up, 140, 200)


def match_and_click(img_full_color, x, y, template_gray, default_position, threshold=0.9):
    """
    匹配,移动鼠标到目标位置，点击一下
    """
    matched = False
    try:
        gray_screenshot = cv2.cvtColor(img_full_color, cv2.COLOR_BGRA2GRAY)
        matches = match_template(gray_screenshot, template_gray, threshold=threshold)
        if len(matches) > 0:
            matched = True
            top_left, bottom_right = matches[0]
            x1, y1 = top_left
            x2, y2 = bottom_right
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            mu.do_move_to(x + center_x, y + center_y)
            time.sleep(0.3)
            mu.do_click(Button.left)
    except Exception as e:
        logger.error(e)
        if default_position:
            mu.do_move_to(x + default_position[0], y + default_position[1])
            time.sleep(0.3)
            mu.do_click(Button.left)
    time.sleep(0.3)
    return matched


def match_get_center(img_full_color, x, y, template_gray, threshold=0.9):
    """
    匹配,获取中心点（x,y）
    """
    center = None
    try:
        gray_screenshot = cv2.cvtColor(img_full_color, cv2.COLOR_BGRA2GRAY)
        matches = match_template(gray_screenshot, template_gray, threshold=threshold)
        if len(matches) > 0:
            top_left, bottom_right = matches[0]
            x1, y1 = top_left
            x2, y2 = bottom_right
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            print('center', center_x, center_y)
            center = x + center_x, y + center_y
    except Exception as e:
        logger.error(e)
    return center


title_gray = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/xb_fighting.png'), cv2.IMREAD_GRAYSCALE)


def calc_role_height(img_full_color, x, y):
    title_center = match_get_center(img_full_color, x, y, title_gray)
    if title_center:
        height = 160 - (title_center[1] - (y + 273))
        return height
    return None


def clik_to_quit_game(handle, x, y):
    """
    结束游戏
    """
    logger.info('结束游戏')
    time.sleep(0.5)

    kbu.do_press(Key.esc)
    time.sleep(0.5)

    full_screen = window_utils.capture_window_BGRX(handle)
    template_quit_game = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/quit_game1.png'), cv2.IMREAD_GRAYSCALE)
    step1 = match_and_click(full_screen, x, y, template_quit_game, (679, 497))
    time.sleep(0.5)

    full_screen = window_utils.capture_window_BGRX(handle)
    template_again_gray = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/return_btn.png'), cv2.IMREAD_GRAYSCALE)
    return_btn_center = match_get_center(full_screen, x, y, template_again_gray)
    if return_btn_center:
        mu.do_move_to(return_btn_center[0] + 65, return_btn_center[1])
        time.sleep(0.5)
        mu.do_click(Button.left)
        time.sleep(0.5)



# # todo todo 截好图传参(先移动鼠标,)，判断图片
# def do_ocr_fatigue(handle, x, y, model):
#     """
#     easyocr，识别疲劳值
#     :param model:
#     :param handle:
#     :param x:
#     :param y:
#     :return:
#     """
#     # mu.do_smooth_move_to(x + 1038, y + 713)
#     # mu.do_smooth_move_to(x + 865, y + 594)
#     mu.do_smooth_move_to(x + 875, y + 594)
#     time.sleep(0.2)
#     # img_fatigue = window_utils.capture_window_BGRX(handle, (985, 689, 92, 17))
#     # img_fatigue = window_utils.capture_window_BGRX(handle, (976, 687, 111, 18)) # 整体部分 976, 687 1087 705
#     # img_fatigue = window_utils.capture_window_BGRX(handle, (1032, 687, 55, 18))  # 数值部分
#     # img_fatigue = window_utils.capture_window_BGRX(handle, (1035, 687, 52, 18))  # 数值部分
#     img_fatigue = window_utils.capture_window_BGRX(handle, (880, 574, 43, 13))  # 数值部分
#
#     # 放大图像
#     resize = cv2.resize(img_fatigue, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
#
#     # 转换为灰度图
#     gray = cv2.cvtColor(resize, cv2.COLOR_BGRA2GRAY)
#
#     # 二值化
#     _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#
#     # 去噪
#     denoised = cv2.medianBlur(thresh, 3)
#
#     # 边缘增强
#     kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
#     sharpened = cv2.filter2D(denoised, -1, kernel)
#
#     # # 膨胀和腐蚀
#     # kernel = np.ones((2, 2), np.uint8)
#     # dilated = cv2.dilate(sharpened, kernel, iterations=1)
#     # eroded = cv2.erode(dilated, kernel, iterations=1)
#
#     # # 对比度调整
#     # adjusted = cv2.convertScaleAbs(eroded, alpha=1.5, beta=0)
#
#     # cv2.imshow('img_fatigue', img_fatigue)
#     # cv2.imwrite('./img_fatigue.png', img_fatigue)
#     #
#     # cv2.imshow('resize', resize)
#     # cv2.imwrite('./resize.png', resize)
#     #
#     # cv2.imshow('gray', gray)
#     # cv2.imwrite('./gray.png', gray)
#     #
#     # cv2.imshow('thresh', thresh)
#     # cv2.imwrite('./thresh.png', thresh)
#     #
#     # cv2.imshow('denoised', denoised)
#     # cv2.imwrite('./denoised.png', denoised)
#     #
#     # cv2.imshow('sharpened', sharpened)
#     # cv2.imwrite('./sharpened.png', sharpened)
#
#     # cv2.imshow('eroded', eroded)
#     # cv2.imshow('adjusted', adjusted)
#
#     # cv2.waitKey(0)
#     global reader
#
#     if reader is None:
#         if model is not None:
#             reader = model
#         else:
#             reader = easyocr.Reader(['en'])
#
#     result = reader.readtext(sharpened, allowlist="0123456789/", detail=0)
#     logger.debug('识别文本:{}', result)
#
#     mu.do_smooth_move_to(x + 1027, y + 561)
#
#     # 解析结果并提取匹配模式的文本
#     for detection in result:
#         # logger.debug('---------->', detection)
#         # text = detection
#         # if pattern_pl.search(text):
#         #     matched_text = pattern_pl.search(text).group()
#         #     logger.debug(f"识别疲劳值->:{matched_text}")
#         #     parts = matched_text.split("/")
#         #     return int(parts[0])
#         fatigue = extract_fatigue_number(detection)
#         if fatigue is not None:
#             logger.debug(f"识别疲劳值1->:{fatigue}")
#             return fatigue
#     if len(result) > 0:
#         fatigue = result[0].strip()
#         logger.debug(f"识别疲劳值2->:{fatigue}")
#         return int(fatigue)
#     logger.error("识别疲劳值为空!")
#     return None


# 提前先加载疲劳数字
pl_num_images = {}
for i in range(10):
    pl_i = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/img_pl/{i}.png'), cv2.IMREAD_COLOR)
    pl_i = cv2.cvtColor(pl_i, cv2.COLOR_BGR2GRAY)
    pl_num_images[i] = pl_i


def do_recognize_fatigue(img):
    """
    识别疲劳值
    :param img: 截图图像 (BGR格式)
    :return: 疲劳值 (0-999)
    """
    # 5*5 *3
    x1, y1, x2, y2 = 842, 592, 856 + 1, 596 + 1
    fatigue_region = img[y1:y2, x1:x2]

    # cv2.imwrite('./fatigue_region.png', fatigue_region)
    # cv2.imshow("fatigue_region", fatigue_region)
    # cv2.waitKey(0)

    fatigue_region = cv2.cvtColor(fatigue_region, cv2.COLOR_BGR2GRAY)

    # 百位 十位 个位
    hundreds_place_region = fatigue_region[:, :int(fatigue_region.shape[1] / 3)]
    tens_place_region = fatigue_region[:, int(fatigue_region.shape[1] / 3):int(fatigue_region.shape[1] * 2 / 3)]
    ones_place_region = fatigue_region[:, int(fatigue_region.shape[1] * 2 / 3):]

    pl_hundreds = 0
    pl_tens = 0
    pl_ones = 0

    for i in pl_num_images.keys():
        # logger.debug(f"匹配数字->:{i}")
        result = match_template_one_with_conf(ones_place_region, pl_num_images[i], 0.95)
        if len(result) > 0:
            # logger.debug(f"百位 匹配到->:{i},---->{result[0]}")
            pl_ones = i

        result = match_template_one_with_conf(tens_place_region, pl_num_images[i], 0.95)
        if len(result) > 0:
            # logger.debug(f"十位 匹配到->:{i},---->{result[0]}")
            pl_tens = i
        result = match_template_one_with_conf(hundreds_place_region, pl_num_images[i], 0.95)
        if len(result) > 0:
            # logger.debug(f"个位 匹配到->:{i},---->{result[0]}")
            pl_hundreds = i

    pl_result = pl_hundreds * 100 + pl_tens * 10 + pl_ones
    logger.debug(f"识别疲劳值-->:{pl_result}")
    return pl_result



def do_ocr_fatigue_retry(handle, x, y, model, retry=1, default_fatigue=10):
    """
    允许重试的疲劳值获取
    :param model:
    :param y:
    :param x:
    :param handle:
    :param retry:
    :param default_fatigue:
    :return:
    """
    # for attempt in range(retry):
    #     result = do_ocr_fatigue(handle, x, y, model)  # todo
    #     if result is not None:
    #         return result
    #     else:
    #         logger.warning(f"第{attempt + 1}次识别疲劳值失败,重试中...")
    logger.warning(f"识别疲劳值失败...")
    return default_fatigue


# todo todo 截好图传参，判断图片
# todo 只截取部分匹配，或者直接对比
def detect_return_town_button_when_choose_map(full_screen):
    """
    识别选择地图页面的'返回城镇'按钮
    """
    # full_screen = window_utils.capture_window_BGRX(handle)
    gray_screenshot = cv2.cvtColor(full_screen, cv2.COLOR_BGRA2GRAY)
    template_again = cv2.imread(
        os.path.normpath(f'{config_.project_base_path}/assets/img/return_button_on_choose_map_1067_600.jpg'),
        cv2.IMREAD_COLOR)
    template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
    matches = match_template(gray_screenshot, template_again_gray, threshold=0.95)
    return len(matches) > 0


def from_sailiya_to_abyss(x, y):
    """
    传送到深渊/妖气门口
    :return:
    """
    # 打开地图
    kbu.do_press('n')
    time.sleep(0.2)
    # 切换至收藏
    kbu.do_press(Key.f2)
    time.sleep(0.2)
    # 默认第一个 深渊
    mu.do_smooth_move_to(x + 145, y + 120)
    time.sleep(0.1)
    mu.do_click(Button.left)
    time.sleep(2.2)


def crusader_to_battle(x, y):
    """
    奶爸,切换输出护石
    """
    logger.info("奶爸,准备切换锤子护石...")
    time.sleep(2)
    # 奶爸切换锤子护石
    # 打开物品栏
    kbu.do_press('i')
    time.sleep(0.2)
    # 点击护石
    # mu.do_smooth_move_to(x + 926, y + 98)
    mu.do_smooth_move_to(x + 785, y + 70)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.2)
    # 点开护石方案列表
    # mu.do_smooth_move_to(x + 976, y + 123)
    mu.do_smooth_move_to(x + 828, y + 93)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.2)
    # 默认第二项是锤子
    # mu.do_smooth_move_to(x + 1071, y + 187)
    mu.do_smooth_move_to(x + 870, y + 149)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.2)
    # 点击应用
    # mu.do_smooth_move_to(x + 1112, y + 218)
    mu.do_smooth_move_to(x + 947, y + 174)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.5)
    # esc 关闭装备栏
    kbu.do_press(Key.esc)
    time.sleep(0.2)
    logger.info("奶爸,切换锤子护石完毕...")


def goto_white_map(x, y):
    """
    去白图，（跌宕群岛）
    :param x:
    :param y:
    :return:
    """

    # 有可能本来就选中了，需要重置并选级别
    # 先重置可能得级别
    kbu.do_press(Key.left)
    time.sleep(0.15)
    kbu.do_press(Key.left)
    time.sleep(0.15)
    kbu.do_press(Key.left)
    time.sleep(0.15)
    kbu.do_press(Key.left)
    time.sleep(0.15)
    kbu.do_press(Key.right)
    time.sleep(0.15)
    kbu.do_press(Key.right)
    time.sleep(0.1)

    # mu.do_smooth_move_to(x + 357, y + 106)  # 妖怪追踪
    # mu.do_smooth_move_to(x + 551, y + 176)  # 妖气歼灭
    mu.do_smooth_move_to(x + 620, y + 305)  # 跌宕群岛
    # mu.do_smooth_move_to(x + 835, y + 309)  # 萧索的回廊
    mu.do_click(Button.left)
    time.sleep(0.5)

    # 先重置可能得级别
    kbu.do_press(Key.left)
    time.sleep(0.2)
    kbu.do_press(Key.left)
    time.sleep(0.2)
    kbu.do_press(Key.left)
    time.sleep(0.2)
    kbu.do_press(Key.left)
    time.sleep(0.2)
    kbu.do_press(Key.right)
    time.sleep(0.2)
    kbu.do_press(Key.right)
    time.sleep(0.2)

    # 确认进入
    mu.do_click(Button.left)
    time.sleep(0.2)

    time.sleep(2)


def goto_white_map_level(x, y, press_cnt=2):
    """
    去白图，（跌宕群岛）
    :param press_cnt:
    :param x:
    :param y:
    :return:
    """

    # 有可能本来就选中了，需要重置并选级别
    # 先重置可能得级别
    kbu.do_press(Key.left)
    time.sleep(0.15)
    kbu.do_press(Key.left)
    time.sleep(0.15)
    kbu.do_press(Key.left)
    time.sleep(0.15)
    kbu.do_press(Key.left)
    time.sleep(0.15)
    for i in range(press_cnt):
        kbu.do_press(Key.right)
        time.sleep(0.15)

    # mu.do_smooth_move_to(x + 357, y + 106)  # 妖怪追踪
    # mu.do_smooth_move_to(x + 551, y + 176)  # 妖气歼灭
    mu.do_smooth_move_to(x + 620, y + 305)  # 跌宕群岛
    # mu.do_smooth_move_to(x + 835, y + 309)  # 萧索的回廊
    mu.do_click(Button.left)
    time.sleep(0.5)

    # 先重置可能得级别
    kbu.do_press(Key.left)
    time.sleep(0.2)
    kbu.do_press(Key.left)
    time.sleep(0.2)
    kbu.do_press(Key.left)
    time.sleep(0.2)
    kbu.do_press(Key.left)
    time.sleep(0.2)
    for i in range(press_cnt):
        kbu.do_press(Key.right)
        time.sleep(0.15)

    # 确认进入
    mu.do_click(Button.left)
    time.sleep(0.2)

    time.sleep(2)


def goto_zhuizong(x, y):
    """
    去白图，（跌宕群岛）
    :param x:
    :param y:
    :return:
    """
    mu.do_smooth_move_to(x + 357, y + 106)  # 妖怪追踪
    # mu.do_smooth_move_to(x + 551, y + 176)  # 妖气歼灭
    # mu.do_smooth_move_to(x + 620, y + 305)  # 跌宕群岛
    # mu.do_smooth_move_to(x + 835, y + 309)  # 萧索的回廊
    mu.do_click(Button.left)
    time.sleep(0.5)

    # 确认进入
    mu.do_click(Button.left)
    time.sleep(0.2)

    time.sleep(2)


def goto_jianmie(x, y):
    """
    去白图，（跌宕群岛）
    :param x:
    :param y:
    :return:
    """
    # mu.do_smooth_move_to(x + 357, y + 106)  # 妖怪追踪
    mu.do_smooth_move_to(x + 551, y + 176)  # 妖气歼灭
    # mu.do_smooth_move_to(x + 620, y + 305)  # 跌宕群岛
    # mu.do_smooth_move_to(x + 835, y + 309)  # 萧索的回廊
    mu.do_click(Button.left)
    time.sleep(0.5)

    # 确认进入
    mu.do_click(Button.left)
    time.sleep(0.2)

    time.sleep(2)


def goto_abyss(x, y):
    """
    去白图，（跌宕群岛）
    :param x:
    :param y:
    :return:
    """
    mu.do_smooth_move_to(x + 720, y + 470)
    mu.do_click(Button.left)
    time.sleep(0.5)

    # 确认进入
    mu.do_click(Button.left)
    time.sleep(0.2)

    time.sleep(2)


def goto_daily_1and1(x, y):
    """
    去白图，（跌宕群岛）
    :param x:
    :param y:
    :return:
    """
    logger.info('点击畅玩任务')
    mu.do_smooth_move_to(x + 767, y + 542)  # 不等比
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.2)

    mu.do_smooth_move_to(x + 494, y + 444)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.2)

    # 按下之后到了选择地图页面
    kbu.do_press(Key.space)
    time.sleep(1)

    # 空格进入地图
    kbu.do_press(Key.space)
    time.sleep(0.2)

    # 按下可能存在的角色绑定提示
    kbu.do_press(Key.space)
    time.sleep(0.2)

    time.sleep(2)


def detect_aolakou(full_screen):
    """
    识别"再次挑战"按钮的情况,按钮是否识别到,文本是否识别到,是否可以点击
    """
    gray_screenshot = cv2.cvtColor(full_screen, cv2.COLOR_BGRA2GRAY)
    template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/activity/act_aolakou1.jpg'),
                                cv2.IMREAD_COLOR)
    template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
    matches = match_template(gray_screenshot, template_again_gray, threshold=0.8)
    if len(matches) > 0:
        logger.debug("有普通奥拉扣！！")
        return True

    template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/activity/act_aolakou2.jpg'),
                                cv2.IMREAD_COLOR)
    template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
    matches = match_template(gray_screenshot, template_again_gray, threshold=0.8)
    if len(matches) > 0:
        logger.debug("有特殊奥拉扣！！")
        return True

    return False


def detect_daily_1and1_clickable(full_screen):
    """
    检查每日1+1是否可点击
    :param full_screen:
    :return:
    """
    x1, y1 = 475, 431
    x2, y2 = 514 + 1, 452 + 1
    daily_crop = full_screen[y1:y2, x1:x2]
    daily_img = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/daily_1and1_goto.png'))
    scores = compare_images(daily_crop, daily_img)
    # print(scores)
    return scores > 0.6


def hide_right_bottom_icon(full_screen, x, y):
    x1, y1 = 736, 534
    x2, y2 = 748 + 1, 549 + 1
    icon_crop = full_screen[y1:y2, x1:x2]
    icon_img = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/activity_icon.png'))
    scores = compare_images(icon_crop, icon_img)
    if scores < 0.5:
        pass
    else:
        mu.do_move_and_click(x + 744, y + 577)
        time.sleep(0.1)


def show_right_bottom_icon(full_screen, x, y):
    x1, y1 = 736, 534
    x2, y2 = 748 + 1, 549 + 1
    icon_crop = full_screen[y1:y2, x1:x2]
    icon_img = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/activity_icon.png'))
    scores = compare_images(icon_crop, icon_img)
    if scores > 0.6:
        pass
    else:
        mu.do_move_and_click(x + 744, y + 577)
        time.sleep(0.1)


def buy_from_mystery_shop(full_screen, x, y):
    """
    神秘商店购买
    """
    logger.info('出现神秘商店！')
    gray_screenshot = cv2.cvtColor(full_screen, cv2.COLOR_BGRA2GRAY)
    template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/ticket.png'), cv2.IMREAD_COLOR)
    template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
    matches = match_template_with_confidence(gray_screenshot, template_again_gray, threshold=0.85)
    logger.info(f"发现门票{len(matches)}个。{matches}")

    for top_left, bottom_right, _ in matches:
        x1, y1 = top_left
        x2, y2 = bottom_right
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        mu.do_move_to(x + center_x, y + center_y)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        logger.info("购买门票一次")


def buy_tank_from_mystery_shop(full_screen, x, y, buy_type: int = 2):
    """
    神秘商店购买
    buy_type: 0，不买，1买传说，2买史诗，3买史诗+传说
    """
    logger.info('出现神秘商店！')
    gray_screenshot = cv2.cvtColor(full_screen, cv2.COLOR_BGRA2GRAY)
    template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/tank_legend.png'), cv2.IMREAD_COLOR)
    template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
    matches = match_template_with_confidence(gray_screenshot, template_again_gray, threshold=0.85)
    logger.info(f"发现罐子{len(matches)}个。{matches}")

    for top_left, bottom_right, _ in matches:
        x1, y1 = top_left
        x2, y2 = bottom_right
        tank_crop = full_screen[y1:y2, x1:x2]
        avg_b, avg_g, avg_r = cv2.mean(tank_crop)[:3]
        weighted_average = 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b
        logger.info(f"buy_type：{buy_type}， {weighted_average}")
        # buy_type: 0，不买，1买传说，2买史诗，3买史诗+传说
        if buy_type == 0:
            logger.debug(f"不买")
            return
        if buy_type == 1 and weighted_average > 90:
            logger.debug(f"不买")
            return
        if buy_type == 2 and weighted_average < 90:
            logger.debug(f"不买")
            return
        if buy_type == 3:
            ...
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        mu.do_move_to(x + center_x, y + center_y)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        logger.info("购买罐子一次")


def buy_bell_from_mystery_shop(full_screen, x, y, buy_type: int = 2):
    """
    神秘商店购买
    buy_type: 0，不买，1买粉罐子，2买传说罐子，3买粉+传说罐子
    """
    logger.info('出现神秘商店！')
    gray_screenshot = cv2.cvtColor(full_screen, cv2.COLOR_BGRA2GRAY)
    template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/bell26.png'), cv2.IMREAD_COLOR)
    template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
    matches = match_template_with_confidence(gray_screenshot, template_again_gray, threshold=0.85)
    logger.info(f"发现铃铛{len(matches)}个。{matches}")

    for top_left, bottom_right, _ in matches:
        x1, y1 = top_left
        x2, y2 = bottom_right
        tank_crop = full_screen[y1:y2, x1:x2]
        avg_b, avg_g, avg_r = cv2.mean(tank_crop)[:3]
        weighted_average = 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b
        logger.info(f"buy_type：{buy_type}， {weighted_average}")
        # buy_type: 0，不买，1买粉罐子，2买传说罐子，3买粉+传说罐子
        if buy_type == 0:
            logger.debug(f"不买")
            return
        if buy_type == 1 and weighted_average > 100:
            logger.debug(f"不买")
            return
        if buy_type == 2 and weighted_average < 100:
            logger.debug(f"不买")
            return
        if buy_type == 3:
            ...
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        mu.do_move_to(x + center_x, y + center_y)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        logger.info("购买铃铛一次")


def buy_shanshanming_from_mystery_shop(full_screen, x, y, buy_type: int = 2):
    """
    神秘商店购买
    buy_type: 0，不买，1买粉罐子，2买传说罐子，3买粉+传说罐子
    """
    logger.info('出现神秘商店！')
    gray_screenshot = cv2.cvtColor(full_screen, cv2.COLOR_BGRA2GRAY)
    matches = []
    # buy_type: 0，不买，1买粉罐子，2买传说罐子，3买粉+传说罐子
    if buy_type == 0:
        logger.debug(f"不买")
        return
    if buy_type == 1:
        logger.debug(f"买小的")
        template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/shanshanming26.png'), cv2.IMREAD_COLOR)
        template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
        matches = match_template_with_confidence(gray_screenshot, template_again_gray, threshold=0.85)
    if buy_type == 2:
        logger.debug("买大的")
        template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/shanshanming26-2.png'), cv2.IMREAD_COLOR)
        template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
        matches = match_template_with_confidence(gray_screenshot, template_again_gray, threshold=0.85)
    if buy_type == 3:
        logger.debug("买小的+大的")
        template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/shanshanming26.png'), cv2.IMREAD_COLOR)
        template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
        matches1 = match_template_with_confidence(gray_screenshot, template_again_gray, threshold=0.85)
        template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/shanshanming26-2.png'), cv2.IMREAD_COLOR)
        template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
        matches2 = match_template_with_confidence(gray_screenshot, template_again_gray, threshold=0.85)
        matches = matches1 + matches2

    # 史诗必买
    template_again = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/shanshanming26-3.png'), cv2.IMREAD_COLOR)
    template_again_gray = cv2.cvtColor(template_again, cv2.COLOR_BGR2GRAY)
    matches3 = match_template_with_confidence(gray_screenshot, template_again_gray, threshold=0.85)
    if matches3:
        logger.info(f"发财了！出现史诗闪闪明{len(matches3)}个！")
    matches = matches + matches3
    logger.info(f"发现闪闪明{len(matches)}个。{matches}")

    for top_left, bottom_right, _ in matches:
        x1, y1 = top_left
        x2, y2 = bottom_right
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        mu.do_move_to(x + center_x, y + center_y)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        logger.info("购买闪闪明一次")


def buy_catalyst_from_mystery_shop(full_screen, x, y, buy_type: int = 0):
    """
    神秘商店购买催化剂
    buy_type: 0不买，1买传说，2买史诗，3买太初，4买传说+史诗，5买史诗+太初，6买传说+太初，7买全部
    
    催化剂品级说明：
    - 传说(橙色): catalyst_legend.png
    - 史诗(紫色): catalyst_epic.png  
    - 太初(金色): catalyst_taichu.png
    """
    if buy_type == 0:
        logger.debug("催化剂：不买")
        return
    
    logger.info(f'检查神秘商店催化剂，购买类型: {buy_type}')
    gray_screenshot = cv2.cvtColor(full_screen, cv2.COLOR_BGRA2GRAY)
    all_matches = []
    
    # 根据buy_type决定要匹配的模板
    templates_to_check = []
    
    # 1:传说, 2:史诗, 3:太初, 4:传说+史诗, 5:史诗+太初, 6:传说+太初, 7:全部
    if buy_type in [1, 4, 6, 7]:  # 包含传说
        templates_to_check.append(('catalyst_legend.png', '传说'))
    if buy_type in [2, 4, 5, 7]:  # 包含史诗
        templates_to_check.append(('catalyst_epic.png', '史诗'))
    if buy_type in [3, 5, 6, 7]:  # 包含太初
        templates_to_check.append(('catalyst_taichu.png', '太初'))
    
    for template_name, grade_name in templates_to_check:
        template_path = os.path.normpath(f'{config_.project_base_path}/assets/img/{template_name}')
        if not os.path.exists(template_path):
            logger.warning(f"催化剂模板图片不存在: {template_path}")
            continue
        
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            logger.warning(f"无法读取催化剂模板: {template_path}")
            continue
            
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        matches = match_template_with_confidence(gray_screenshot, template_gray, threshold=0.85)
        
        if matches:
            logger.info(f"发现{grade_name}催化剂 {len(matches)} 个")
            all_matches.extend(matches)
    
    logger.info(f"共发现催化剂 {len(all_matches)} 个")
    
    for top_left, bottom_right, conf in all_matches:
        x1, y1 = top_left
        x2, y2 = bottom_right
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        
        mu.do_move_to(x + center_x, y + center_y)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        logger.info(f"购买催化剂一次 (置信度: {conf:.2f})")


def process_mystery_shop(img, x, y, buy_tank_type, buy_bell_ticket, buy_shanshanming, buy_catalyst=0):
    """
    处理神秘商店购买
    
    Args:
        img: 截图
        x, y: 窗口坐标
        buy_tank_type: 罐子购买类型
        buy_bell_ticket: 铃铛购买类型
        buy_shanshanming: 闪闪明购买类型
        buy_catalyst: 催化剂购买类型 (0不买，1传说，2史诗，3太初，4传说+史诗，5史诗+太初，6传说+太初，7全部)
    """
    buy_from_mystery_shop(img, x, y)
    time.sleep(0.5)
    buy_tank_from_mystery_shop(img, x, y, buy_tank_type)
    if buy_bell_ticket:
        time.sleep(0.5)
        buy_bell_from_mystery_shop(img, x, y, buy_bell_ticket)
    if buy_shanshanming:
        time.sleep(0.5)
        buy_shanshanming_from_mystery_shop(img, x, y, buy_shanshanming)
    if buy_catalyst:
        time.sleep(0.5)
        buy_catalyst_from_mystery_shop(img, x, y, buy_catalyst)


def activity_live(x, y):
    """
    垃圾直播活动
    """
    logger.info('垃圾活动')
    time.sleep(0.4)
    # 活动图标
    mu.do_smooth_move_to(x + 843, y + 516)
    time.sleep(0.2)
    mu.do_click(Button.left)
    time.sleep(0.2)

    mu.do_smooth_move_to(x + 712, y + 517)
    time.sleep(0.2)

    for _ in range(1):
        mu.do_click(Button.left)
        time.sleep(1)

    # esc 取消仓库
    kbu.do_press(Key.esc)
    time.sleep(0.2)


template_mail1 = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/mail_icon1.png'), cv2.IMREAD_GRAYSCALE)
template_mail2 = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/mail_icon2.png'), cv2.IMREAD_GRAYSCALE)


def receive_mail(img, x, y):
    """
    领取邮件
    """
    try:
        logger.info('准备领取邮件')

        have_mail = False
        icon1 = match_and_click(img, x, y, template_mail1, None)
        if icon1:
            logger.info('有邮件,已打开收件箱！')
            have_mail = True
        else:
            icon2 = match_and_click(img, x, y, template_mail2, None)
            if icon2:
                logger.info('有叹号邮件,已打开收件箱！')
                have_mail = True
            else:
                logger.info('没有邮件。')

        if have_mail:
            time.sleep(1)
            mu.do_move_to(x + 414, y + 458)
            time.sleep(0.2)
            mu.do_click(Button.left)
            time.sleep(2)
            logger.info('领取邮件完毕')

            time.sleep(0.2)
            kbu.do_press(Key.esc)

        time.sleep(0.2)
    except Exception as e:
        logger.error('领邮件出错', e)


def close_new_day_dialog(handle, x, y, capturer=None):
    """
    关闭0点弹窗/活动弹窗
    检测时机：脚本开始，换角色，出图后，
    :param capturer: WindowCapture实例，如果为None则创建临时实例
    :return: True 如果检测到并关闭了弹窗，False 如果没有检测到弹窗
    """
    # 使用WindowCapture截图（支持DX游戏）
    if capturer is None:
        capturer = window_utils.WindowCapture(handle)
        temp_capturer = True
    else:
        temp_capturer = False
    
    try:
        full_screen = capturer.capture()
        # 转换为BGRA格式
        if full_screen.shape[2] == 3:
            full_screen = cv2.cvtColor(full_screen, cv2.COLOR_BGR2BGRA)
        
        # 先检测"X"按钮（小按钮，匹配率更高）
        template_btn_x = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/dialog-btn-X.png'), cv2.IMREAD_GRAYSCALE)
        if template_btn_x is not None:
            matched1 = match_and_click(full_screen, x, y, template_btn_x, None, threshold=0.85)
            if matched1:
                logger.info("检测到弹窗（X按钮），已关闭")
                return True

        # 检测"关闭"按钮
        template_btn_close = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/dialog-btn-close.png'), cv2.IMREAD_GRAYSCALE)
        if template_btn_close is not None:
            matched2 = match_and_click(full_screen, x, y, template_btn_close, None, threshold=0.75)
            if matched2:
                logger.info("检测到弹窗（关闭按钮），已关闭")
                return True
        
        # 检测"确认"按钮（活动弹窗常用）
        template_btn_confirm = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/dialog-btn-confirm.png'), cv2.IMREAD_GRAYSCALE)
        if template_btn_confirm is not None:
            matched3 = match_and_click(full_screen, x, y, template_btn_confirm, None, threshold=0.75)
            if matched3:
                logger.info("检测到弹窗（确认按钮），已关闭")
                return True
        
        return False
    finally:
        if temp_capturer:
            capturer.release()


if __name__ == '__main__':
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250718-222758.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250718-223839.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250718-223950.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250718-224414.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250718-224426.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250718-224700.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250719-005935.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250719-010108.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250719-010155.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250719-010242.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250719-010318.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250719-010422.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250719-010458.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250719-010532.png')
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250719-010548.png')

    # do_recognize_fatigue(img)
    close_new_day_dialog(1, 1, 1)
