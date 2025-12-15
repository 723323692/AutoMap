# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'

from datetime import datetime
import time

import cv2
import cv2 as cv
import numpy as np
from pynput.keyboard import Key
from skimage.metrics import structural_similarity as ssim

from dnf.stronger.logger_config import logger
from dnf.stronger.role_config import RoleConfig, Skill
from utils import keyboard_utils as kbu

# x1, y1 = 527, 645
# x2, y2 = 770, 712
x1, y1 = 434, 534
x2, y2 = 648, 593

# skill_height = int((y2 - y1) / 2)
# skill_width = int((x2 - x1) / 7)
skill_height = 28
skill_width = 28

# 技能栏按键列表（可以通过GUI修改，对应游戏内的技能栏按键）
# 14个槽位：上排7个 + 下排7个
ACTUAL_KEYS = ["y", "w", "e", "r", "t", "ctrl_l", "", "a", "s", "d", "f", "g", "h", "alt_l"]

def _get_actual_keys():
    """动态获取实际按键列表"""
    import sys
    if 'dnf.stronger.skill_util' in sys.modules:
        mod = sys.modules['dnf.stronger.skill_util']
        return getattr(mod, 'ACTUAL_KEYS', ACTUAL_KEYS)
    return ACTUAL_KEYS

# 根据实际按键构建 skill_dict
def _build_skill_dict():
    """根据 ACTUAL_KEYS 构建 skill_dict"""
    keys = _get_actual_keys()
    result = {}
    for i, key in enumerate(keys):
        if i < 7:
            pos = (x1 + skill_width * i, y1)
        else:
            pos = (x1 + skill_width * (i - 7), y1 + skill_height)
        # 转换特殊按键
        if key == 'ctrl_l':
            result[Key.ctrl_l] = pos
        elif key == 'alt_l':
            result[Key.alt_l] = pos
        elif key == 'tab':
            result[Key.tab] = pos
        elif key == 'space':
            result[Key.space] = pos
        else:
            result[key] = pos
    return result

def get_skill_dict():
    """动态获取 skill_dict（每次调用都重新构建）"""
    return _build_skill_dict()

# 初始化 skill_dict（兼容旧代码）
skill_dict = _build_skill_dict()


# 计算给定图像 img 中亮度高于阈值127的像素的比例
def score(img):
    counter = 0
    for i in range(img.shape[0]):
        for j in range(img.shape[1]):
            if img[i, j] > 127:
                counter += 1
    return counter / (img.shape[0] * img.shape[1])


def score_by_warm(img):
    # 转换为HSV颜色空间
    hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 分离通道
    h, s, _ = cv2.split(hsv_img)

    # 计算符合暖色调条件的像素比例
    warm_pixels = np.sum(np.frompyfunc(is_warm_color, 2, 1)(h, s))
    total_pixels = h.size

    warm_ratio = warm_pixels / total_pixels

    return warm_ratio


def img_show(img):
    cv.imshow("win", img)
    cv.waitKey(0)
    cv.destroyAllWindows()


# 判断技能是否恢复CD了
def skill_ready(skill_name, img):
    # print(f"识别{skill_name}")
    if skill_name == "x":
        return True
    skill_img = img[skill_dict[skill_name][1]: skill_dict[skill_name][1] + skill_height,
                    skill_dict[skill_name][0]: skill_dict[skill_name][0] + skill_width]
    # cv.imshow("skill", skill_img)
    # cv.waitKey(0)
    s = score(skill_img)
    # print(s)
    if s > 0.1:
        return True
    else:
        return False


def ensure_gray(img):
    # 如果图像是四通道（BGRX 或 BGRA），去掉第4个通道，并转换为灰度图
    if len(img.shape) == 3 and img.shape[2] == 4:
        # print("图像是四通道，去掉第4个通道")
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        return img_gray
    # 如果图像是三通道（BGR），直接转换为灰度图
    elif len(img.shape) == 3 and img.shape[2] == 3:
        # print("图像是三通道，直接转换为灰度图")
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img_gray
    # 如果图像已经是灰度图，直接返回
    elif len(img.shape) == 2:
        return img
    else:
        raise ValueError("图像格式不正确，无法判断是否为灰度图")


def is_warm_color(hue, saturation):
    # 定义暖色调的HSV范围
    warm_colors = [
        ((0, 22), (100, 255)),  # 红色到橙色
        ((22, 38), (100, 255)),  # 橙色到黄色
        ((38, 50), (50, 255)),  # 黄色（包括浅黄色）
        ((300, 360), (50, 255)),  # 紫红色
    ]
    for (hue_range, sat_range) in warm_colors:
        if hue_range[0] <= hue <= hue_range[1] and sat_range[0] <= saturation <= sat_range[1]:
            return True
    return False


def skill_ready_warm_colors(skill_name, img):
    # 都>0.4 都小于0.3
    if skill_name == "x":
        return True
    current_skill_dict = get_skill_dict()
    keys_list = list(current_skill_dict.keys())
    if skill_name not in keys_list:
        return False
    index = keys_list.index(skill_name)
    x = 434 + (28 + 3) * (index % 7)
    y = 534 + (28 + 3) * (index // 7)
    skill_img = img[y:y + skill_height, x:x + skill_width]
    # 扣去顶部和底部带字的部分
    # skill_img = skill_img[7:-7, :]

    warm_ratio = score_by_warm(skill_img)

    # 判断技能是否可用
    is_ready = warm_ratio > 0.2

    # print(f"技能 {skill_name} - 暖色调比例: {warm_ratio:.2f}")
    # cv2.imwrite(f'./skill{datetime.fromtimestamp(time.time()).strftime("%Y%m%d_%H%M%S")}.jpg', skill_img)
    # cv2.imshow('a',skill_img)
    return is_ready


def suggest_skill(role: RoleConfig, img0):
    # 随机一个技能名
    skill_name = 'x'

    checked_skill_name = search_available_skill_from_list(skills=role.custom_priority_skills, img0=img0)
    if checked_skill_name:
        return checked_skill_name
    logger.debug("自定义技能 没有合适的!!!")
    for _ in range(10):
        skill_name = role.candidate_hotkeys[int(np.random.randint(len(role.candidate_hotkeys), size=1)[0])]
        logger.debug(f'随机技能名字 【{skill_name}】')
        if skill_ready_warm_colors(skill_name, img0):
            break
        else:
            logger.debug('不行 再找一个技能名字', skill_name)
            pass
    return skill_name


def check_one_skill_cd(skill_key, img, skill_images):
    if skill_key == "x":
        return True
    current_skill_dict = get_skill_dict()
    keys_list = list(current_skill_dict.keys())
    if skill_key not in keys_list:
        return False
    index = keys_list.index(skill_key)
    x = 434 + (28 + 3) * (index % 7)
    y = 534 + (28 + 3) * (index // 7)
    skill_img = img[y:y + skill_height, x:x + skill_width]
    init_skill_img = skill_images[skill_key]
    gray = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)
    similarity_score = ssim(init_skill_img, gray)
    # logger.debug(f'技能【{skill_key}】相似度:【{similarity_score}】')

    # combined_img = np.hstack((init_skill_img, gray))
    # cv2.imwrite(f'./skill_img/debug_skill_{datetime.fromtimestamp(time.time()).strftime("%Y%m%d_%H%M%S")}_{skill_key}_[{similarity_score}].jpg', combined_img)
    # print(f'./skill_img/debug_skill_{datetime.fromtimestamp(time.time()).strftime("%Y%m%d_%H%M%S")}_{skill_key}_[{similarity_score}].jpg')

    if similarity_score > 0.92:
        return True
    return False


def suggest_skill_by_img_match(role: RoleConfig, img0, skill_images):
    # 随机一个技能名
    skill_name = 'x'
    ok_skill = get_available_skill_from_list_by_match(skills=role.custom_priority_skills, img0=img0, skill_images=skill_images)
    if ok_skill:
        return ok_skill
    logger.debug("查找技能 没有合适的!!!")
    return skill_name


def suggest_skill_powerful(role: RoleConfig, img0):
    return search_available_skill_from_list(skills=role.powerful_skills, img0=img0)


def search_available_skill_from_list(skills, img0):
    """
    从候选技能列表中找已经恢复CD的技能，（通过计算暖色调像素判断）
    :param skills:
    :param img0:
    :return:
    """
    for s in skills:
        if isinstance(s, str) or isinstance(s, Key):
            if skill_ready_warm_colors(s, img0):
                logger.debug(f"字符串技能:【{s}】 已恢复cd(识别)")
                return s
        elif isinstance(s, list):
            return s
        elif isinstance(s, Skill):
            if s.cd:
                t = time.time()
                if t - s.cd > s.recent_use_time + 0.1:
                    logger.debug(f"Skill:【{s.name}】 已恢复cd(计算)")
                    # s.recent_use_time = t  # 更新最近使用时间
                    return s
            elif len(s.command) == 1 or s.hot_key is not None:
                sname = s.hot_key if s.hot_key is not None else s.command[0]
                if skill_ready_warm_colors(sname, img0):
                    logger.debug(f"Skill:【{s.name}】 已恢复cd(识别)")
                    return s
            logger.debug('未恢复cd,再找')
    return None


def get_available_skill_from_list_by_match(skills, img0, skill_images):
    """
    从候选技能列表中找已经恢复CD的技能，（通过技能图片对比判断）
    :param skills:
    :param img0:
    :param skill_images:
    :return:
    """
    for s in skills:
        # logger.debug(f"CD判断:【{s}】")
        if isinstance(s, str) or isinstance(s, Key):
            if check_one_skill_cd(s, img0, skill_images):
                logger.debug(f"字符串技能:【{s}】 已恢复cd(识别)")
                return s
        elif isinstance(s, list):
            return s
        elif isinstance(s, Skill):
            if s.cd:
                t = time.time()
                if t - s.cd > s.recent_use_time + 0.1:
                    logger.debug(f"Skill:【{s.name}】 已恢复cd(计算)")
                    # s.recent_use_time = t  # 更新最近使用时间
                    return s
                else:
                    logger.debug(f'{s}未恢复计算cd,再找')
            elif s.hotkey_cd_command_cast and s.hot_key and s.command:  # 需要用快捷键识别CD，但是又需要多个指令操作的情况
                sname = s.hot_key
                if check_one_skill_cd(sname, img0, skill_images):
                    logger.debug(f"Skill:【{s.name}】 已恢复cd(识别指令)")
                    return s
                else:
                    logger.debug(f'{s}未恢复识别cd,再找')
            elif len(s.command) == 1 or s.hot_key is not None:
                sname = s.hot_key if s.hot_key is not None else s.command[0]
                if check_one_skill_cd(sname, img0, skill_images):
                    logger.debug(f"Skill:【{s.name}】 已恢复cd(识别)")
                    return s
                else:
                    logger.debug(f'{s}未恢复识别cd,再找')
            logger.debug('未恢复cd,再找')
    return None


def cast_skill(s):
    """
    放技能
    :param s:
    :return:
    """
    logger.debug(f"放技能:{s}")

    # 按键指令操作
    if isinstance(s, str) or isinstance(s, Key):
        kbu.do_press(s)
    elif isinstance(s, list):
        kbu.do_command_wait_time(s, 0)
    elif isinstance(s, Skill):
        if s.cd:
            s.recent_use_time = time.time()  # 更新最近使用时间
        if s.hot_key and not s.hotkey_cd_command_cast:
            kbu.do_press(s.hot_key)
        elif s.command:
            if s.concurrent:
                kbu.do_concurrent_command_wait_time(s.command, 0)
            else:
                kbu.do_command_wait_time(s.command, 0)

    # 技能动作时间
    if isinstance(s, Skill) and s.animation_time is not None and s.animation_time > 0:
        logger.debug(f"技能等待时间:{s.animation_time}")
        time.sleep(s.animation_time)
    elif s == 'x':
        time.sleep(0.1)
    else:
        time.sleep(0.6)


def get_skill_initial_images(full_image):
    """
    初始化技能图片
    :param full_image:
    :return:
    """
    skill_images = {}
    current_skill_dict = get_skill_dict()
    # 遍历技能快捷栏
    for index, key in enumerate(current_skill_dict.keys()):
        _x = 434 + (28 + 3) * (index % 7)
        _y = 534 + (28 + 3) * (index // 7)
        # print()

        # 扣出技能格子图片
        skill_img = full_image[_y:_y + skill_height, _x:_x + skill_width]
        # 灰度化
        skill_img = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)
        # 存字典
        skill_images[key] = skill_img
    return skill_images


if __name__ == '__main__':
    pass
    # img = cv.imread("./ff8.png")
    # cv.imshow("img", img)
    # cv.waitKey(0)

    # print(skill_ready('q', img))
    # print(skill_ready('w', img))
    # print(skill_ready('e', img))
    # print(skill_ready('r', img))
    # print(skill_ready('t', img))
    # print(skill_ready('v', img))
    # print(skill_ready(Key.ctrl_l, img))

    # print(skill_ready2('q', img))
    # print(skill_ready2('w', img))
    # print(skill_ready2('e', img))
    # print(skill_ready2('r', img))
    # print(skill_ready2('t', img))
    # print(skill_ready2('v', img))
    # print(skill_ready2(Key.ctrl_l, img))
    #
    # print(skill_ready2('a', img))
    # print(skill_ready2('s', img))
    # print(skill_ready2('d', img))
    # print(skill_ready2('f', img))
    # print(skill_ready2('g', img))
    # print(skill_ready2(Key.tab, img))
    # print(skill_ready2('h', img))

    # print(skill_ready_warm_colors('q', img))
    # print(skill_ready_warm_colors('w', img))
    # print(skill_ready_warm_colors('e', img))
    # print(skill_ready_warm_colors('r', img))
    # print(skill_ready_warm_colors('t', img))
    # print(skill_ready_warm_colors('v', img))
    # print(skill_ready_warm_colors(Key.ctrl_l, img))
    #
    # print(skill_ready_warm_colors('a', img))
    # print(skill_ready_warm_colors('s', img))
    # print(skill_ready_warm_colors('d', img))
    # print(skill_ready_warm_colors('f', img))
    # print(skill_ready_warm_colors('g', img))
    # print(skill_ready_warm_colors(Key.tab, img))
    # print(skill_ready_warm_colors('h', img))

    # imgfull_for_skill = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250718-222758.png')
    # skills = get_skill_initial_images(imgfull_for_skill)
    # img = cv2.imread(r'D:\win\Users\nianling\Desktop\dnf\fatigue\QQ20250718-224426.png')
    #
    # print('q', check_one_skill_cd('q', img, skills))
    # print('w', check_one_skill_cd('w', img, skills))
    # print('e', check_one_skill_cd('e', img, skills))
    # print('r', check_one_skill_cd('r', img, skills))
    # print('t', check_one_skill_cd('t', img, skills))
    # print('v', check_one_skill_cd('v', img, skills))
    # print('ctrl', check_one_skill_cd(Key.ctrl_l, img, skills))
    # print('a', check_one_skill_cd('a', img, skills))
    # print('s', check_one_skill_cd('s', img, skills))
    # print('d', check_one_skill_cd('d', img, skills))
    # print('f', check_one_skill_cd('f', img, skills))
    # print('g', check_one_skill_cd('g', img, skills))
    # print('tab', check_one_skill_cd(Key.tab, img, skills))
    # print('h', check_one_skill_cd('h', img, skills))
