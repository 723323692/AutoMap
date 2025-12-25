# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'

import itertools
import math
import os
import pathlib
import random
import re
import threading
import time
from datetime import datetime
import queue
import traceback
import concurrent.futures

import cv2
import keyboard as kboard
import numpy as np
import torch
import win32con
import win32gui
import winsound
from pynput import keyboard
from pynput.keyboard import Key
from pynput.mouse import Button
from ultralytics import YOLO

import config as config_
import dnf.dnf_config as dnf
import map_util as map_util
import skill_util as skill_util
from dnf.stronger.det_result import DetResult
from dnf.stronger.method import (
    detect_try_again_button,
    detect_1and1_next_map_button,
    find_densest_monster_cluster,
    get_closest_obj,
    exist_near,
    get_objs_in_range,
    find_door_by_position,
    get_opposite_direction
)
from dnf.stronger.player import (
    transfer_materials_to_account_vault,
    finish_daily_challenge_by_all,
    teleport_to_sailiya,
    clik_to_quit_game,
    do_ocr_fatigue_retry,
    detect_return_town_button_when_choose_map,
    from_sailiya_to_abyss,
    crusader_to_battle,
    goto_daily_1and1,
    goto_white_map,
    goto_zhuizong,
    goto_jianmie,
    detect_daily_1and1_clickable,
    hide_right_bottom_icon,
    show_right_bottom_icon,
    goto_white_map_level,
    buy_from_mystery_shop,
    process_mystery_shop,
    activity_live,
    do_recognize_fatigue,
    receive_mail,
    close_new_day_dialog
)
from logger_config import logger
from utils import keyboard_utils as kbu


def get_role_config_list(account_code, use_json=True):
    """
    获取角色配置列表
    :param account_code: 账号编码
    :param use_json: True=从JSON文件加载(GUI模式)，False=从role_list.py加载(源码运行)
    """
    if use_json:
        from dnf.stronger.role_config_manager import get_role_config_list_from_json
        return get_role_config_list_from_json(account_code)
    else:
        from dnf.stronger.role_list import get_role_config_list as get_from_role_list
        return get_from_role_list(account_code)
from utils import mouse_utils as mu
from utils import window_utils as window_utils
from utils.custom_thread_pool_executor import SingleTaskThreadPool
from utils.fixed_length_queue import FixedLengthQueue
from utils.keyboard_move_controller import MovementController
from utils.utilities import plot_one_box
from utils.window_utils import WindowCapture, capture_window_image
from dnf.stronger.path_finder import PathFinder
from dnf.stronger.movement_helper import move_to_target, calculate_move_direction, is_in_range
from utils.utilities import match_template_by_roi
from utils.mail_sender import EmailSender
from dnf.mail_config import config as mail_config
from dnf.stronger.object_detect import object_detection_cv
from utils.utilities import hex_to_bgr
from dnf.stronger.skill_util import get_skill_initial_images

temp = pathlib.PosixPath
pathlib.PosixPath = pathlib.WindowsPath

#  >>>>>>>>>>>>>>>> 运行时相关的参数 >>>>>>>>>>>>>>>>

# 配置来源：True=从JSON文件加载(GUI模式)，False=从role_list.py加载(源码运行)
use_json_config = False

show = False  # 查看检测结果

# 脚本执行完之后,结束游戏
quit_game_after_finish = False
# 睡觉去了,让脚本执行完之后,自己关机
shutdown_pc_after_finish = False

# 买罐子
buy_tank_type = 0  # buy_type: 0不买，1买传说，2买史诗，3买史诗+传说
# 买铃铛
buy_bell_ticket = 0  # buy_type: 0，不买，1买粉罐子，2买传说罐子，3买粉+传说罐子
# 买闪闪明
buy_shanshanming = 2  # buy_type: 0，不买，1买粉罐子，2买传说罐子，3买粉+传说罐子
# 买催化剂
buy_catalyst = 7  # buy_type: 0不买，1传说，2史诗，3太初，4传说+史诗，5史诗+太初，6传说+太初，7全部
# 账号编码0
account_code = 1  # 1:执行自己账号,2:执行五子账号
# 执行脚本的第一个角色_编号
first_role_no = 25
last_role_no = 40
# 执行跳过角色_编号列表x
break_role = False
break_role_no = [15]
# break_role_no = [3]
# 游戏模式 1:白图（跌宕群岛），2:每日1+1，3:妖气追踪，4:妖怪歼灭，
# 5:先1+1再白图，6:先1+1在妖气追踪
game_mode = 3

# 使用此处统一配置预留的疲劳值
enable_uniform_pl = False
# enable_uniform_pl = True
uniform_default_fatigue_reserved = 180
# uniform_default_fatigue_reserved = /0

weights = os.path.join(config_.project_base_path, 'weights/stronger.pt')  # 模型存放的位置
# <<<<<<<<<<<<<<<< 运行时相关的参数 <<<<<<<<<<<<<<<<

#  >>>>>>>>>>>>>>>> 脚本所需要的变量 >>>>>>>>>>>>>>>>
# 每秒最大处理帧数XX
max_fps = 10

# 游戏窗口位置
x, y = 0, 0
handle = -1

# 全局变量 暂停
pause_event = threading.Event()
pause_event.set()  # 初始设置为未暂停状态

# 当前按下的按键集合
current_keys_control = set()

# 全局变量，停止组合键是否按下,用于控制脚本运行
stop_be_pressed = False
# 唤醒继续运行
continue_pressed = False


def check_stop():
    """检查是否需要停止，如果需要停止则抛出异常"""
    global stop_be_pressed
    if stop_be_pressed:
        raise StopIteration("用户请求停止脚本")
    return False


def safe_sleep(seconds):
    """安全的sleep，每0.1秒检查一次停止标志"""
    global stop_be_pressed
    elapsed = 0
    while elapsed < seconds:
        if stop_be_pressed:
            raise StopIteration("用户请求停止脚本")
        time.sleep(min(0.1, seconds - elapsed))
        elapsed += 0.1

# reader = easyocr.Reader(['en'])
# 疲劳值识别
pattern_pl = re.compile(r'\d+/\d+')

color_red = (0, 0, 255)  # 红色
color_green = (0, 255, 0)  # 绿色
color_blue = (255, 0, 0)  # 蓝色
color_yellow = (0, 255, 255)  # 黄色
color_purple = (255, 0, 255)  # 紫色

# ---------------------------------------------------------
# 延迟加载模型，提升启动速度
model = None
model_obstacle = None  # 障碍物检测模型
device = None
weights_obstacle = os.path.join(config_.project_base_path, 'weights', 'obstacle.pt')

def _select_best_gpu():
    """选择最佳GPU设备，优先选择独立显卡"""
    if not torch.cuda.is_available():
        return torch.device("cpu"), "CPU"
    
    gpu_count = torch.cuda.device_count()
    if gpu_count == 1:
        name = torch.cuda.get_device_name(0)
        return torch.device("cuda:0"), name
    
    # 多GPU时，选择显存最大的（通常是独显）
    best_idx = 0
    best_memory = 0
    for i in range(gpu_count):
        props = torch.cuda.get_device_properties(i)
        name = props.name.lower()
        # 跳过核显（Intel/AMD集成显卡）
        if 'intel' in name or 'integrated' in name:
            continue
        if props.total_memory > best_memory:
            best_memory = props.total_memory
            best_idx = i
    
    name = torch.cuda.get_device_name(best_idx)
    return torch.device(f"cuda:{best_idx}"), name


def get_model():
    """延迟加载YOLO模型"""
    global model, model_obstacle, device
    if model is None:
        import time as _time
        t0 = _time.time()
        
        # 先选择设备
        device, device_name = _select_best_gpu()
        logger.info(f"选择计算设备: {device} ({device_name})")
        
        # 加载主模型并移动到指定设备
        logger.info("正在加载主推理模型...")
        model = YOLO(weights)
        model.to(device)
        
        # 加载障碍物检测模型并移动到同一设备
        if os.path.exists(weights_obstacle):
            logger.info("正在加载障碍物模型...")
            model_obstacle = YOLO(weights_obstacle)
            model_obstacle.to(device)
        
        # 模型预热，让首次推理更快
        logger.info("模型预热中...")
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        model.predict(source=dummy_img, device=device, verbose=False)
        if model_obstacle:
            model_obstacle.predict(source=dummy_img, device=device, verbose=False)
        logger.info(f"模型加载完成，使用设备: {device} ({device_name})，耗时: {_time.time()-t0:.1f}秒")
    return model, device
# if device.type != 'cpu':
#     model.half()  # to FP16
names = [
    'boss',
    'card',
    'continue',
    'door',
    'gold',
    'hero',
    'loot',
    'menu',
    'monster',
    'elite-monster',
    'shop',
    'shop-mystery',
    'sss',
    'door-boss',
    'obstacle'
]

name_colors = [
    {
        "name": "boss",
        "id": 1,
        "color": "#523294",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "card",
        "id": 2,
        "color": "#5b98c6",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "continue",
        "id": 3,
        "color": "#4c7a1d",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "door",
        "id": 4,
        "color": "#4398ef",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "gold",
        "id": 5,
        "color": "#f2cb53",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "hero",
        "id": 6,
        "color": "#fefe30",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "loot",
        "id": 7,
        "color": "#a8e898",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "menu",
        "id": 8,
        "color": "#268674",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "monster",
        "id": 9,
        "color": "#fcb5fc",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "elite-monster",
        "id": 10,
        "color": "#33ddff",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "shop",
        "id": 11,
        "color": "#c8b3cb",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "shop-mystery",
        "id": 12,
        "color": "#909950",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "sss",
        "id": 13,
        "color": "#b5b5b0",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "door-boss",
        "id": 14,
        "color": "#ea6a4b",
        "type": "rectangle",
        "attributes": []
    },
    {
        "name": "obstacle",
        "id": 15,
        "color": "#ff8c00",
        "type": "rectangle",
        "attributes": []
    }
]
name_colors = [hex_to_bgr(d['color']) for d in name_colors]

colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]
# ----------------------------------------------------------
boss_h = 120  # boss高度处理
monster_h = 57  # 普通怪高度处理
em_h = 100  # 精英怪高度处理
door_h = 32  # 门高度处理
loot_h = 0  # 掉落物高度处理

attack_x = 300  # 打怪命中范围，x轴距离
attack_y = 90  # 打怪命中范围，y轴距离

door_hit_x = 50  # 过门命中范围，x轴距离（增大避免来回蹭）
door_hit_y = 45  # 过门命中范围，y轴距离（增大避免来回蹭，向下过门需要更大范围）

pick_up_x = 25  # 捡材料命中范围，x轴距离
pick_up_y = 15  # 捡材料命中范围，y轴距离

# <<<<<<<<<<<<<<<< 脚本所需要的变量 <<<<<<<<<<<<<<<<
mover = MovementController()
executor = SingleTaskThreadPool()
img_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
tool_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
mail_sender = EmailSender(mail_config)  # 初始化邮件发送器
stop_signal = [False]

# 创建一个队列，用于主线程和展示线程之间的通信（maxsize=2避免堆积）
result_queue = queue.Queue(maxsize=2)


# 展示线程停止标志
display_stop_flag = False

# 展示线程的函数
def display_results():
    global display_stop_flag
    window_name = "Game Capture"
    window_created = False
    last_frame = None
    
    while not display_stop_flag:
        try:
            # 阻塞等待新帧，超时100ms检查一次停止标志
            frame = None
            try:
                frame = result_queue.get(timeout=0.1)
                if frame is None:
                    display_stop_flag = True
                    break
                # 丢弃旧帧，只保留最新的
                while not result_queue.empty():
                    try:
                        newer_frame = result_queue.get_nowait()
                        if newer_frame is None:
                            display_stop_flag = True
                            break
                        frame = newer_frame
                    except queue.Empty:
                        break
            except queue.Empty:
                # 超时，继续循环检查停止标志
                if last_frame is not None:
                    cv2.waitKey(1)  # 保持窗口响应
                continue
            
            if display_stop_flag:
                break
                
            # 更新帧
            if frame is not None:
                last_frame = frame

            # 创建窗口
            if not window_created:
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(window_name, 640, 360)
                cv2.moveWindow(window_name, 10, 10)
                window_created = True

            # 显示
            cv2.imshow(window_name, last_frame)
            
            # waitKey 控制刷新率
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        except Exception as e:
            if not display_stop_flag:
                logger.error(f"展示显示报错: {e}")
            break

    # 清理
    try:
        cv2.destroyWindow(window_name)
        cv2.waitKey(1)
    except:
        pass


# 展示线程变量
display_thread = None


def start_display_thread():
    """启动展示线程"""
    global display_thread, display_stop_flag
    display_stop_flag = False
    
    # 清空队列
    while not result_queue.empty():
        try:
            result_queue.get_nowait()
        except:
            break
    
    if display_thread is None or not display_thread.is_alive():
        display_thread = threading.Thread(target=display_results, daemon=True)
        display_thread.start()
        logger.info("检测结果展示窗口已启动")


def stop_display_thread():
    """停止展示线程"""
    global display_stop_flag
    display_stop_flag = True
    # 发送None信号让线程退出
    try:
        result_queue.put(None)
    except:
        pass

#  >>>>>>>>>>>>>>>> 方法定义 >>>>>>>>>>>>>>>>

def _do_stop_action():
    """停止脚本的实际操作（在单独线程中执行）"""
    global stop_be_pressed, stop_signal
    winsound.PlaySound(config_.sound2, winsound.SND_FILENAME)
    stop_be_pressed = True
    stop_signal[0] = True  # 同时设置stop_signal，停止超时检测线程
    # 立即释放所有按键
    mover._release_all_keys()


def on_stop_hotkey():
    """停止脚本的热键回调 - 立即响应，耗时操作放到线程"""
    global stop_be_pressed, stop_signal
    logger.warning("监听到停止热键，停止脚本...")
    stop_be_pressed = True  # 立即设置标志
    stop_signal[0] = True  # 同时设置stop_signal，停止超时检测线程
    mover._release_all_keys()  # 立即释放按键
    threading.Thread(target=_do_stop_action, daemon=True).start()


def _do_pause_action():
    """暂停/继续的实际操作（在单独线程中执行）"""
    global continue_pressed, x, y
    winsound.PlaySound(config_.sound3, winsound.SND_FILENAME)


def _do_resume_action():
    """继续运行的实际操作（在单独线程中执行）"""
    global continue_pressed, x, y
    winsound.PlaySound(config_.sound3, winsound.SND_FILENAME)
    time.sleep(0.1)
    x, y, _, _ = window_utils.get_window_rect(handle)
    mu.do_smooth_move_to(x + 500, y + 300)
    time.sleep(0.1)
    mu.do_click(Button.left)


def on_pause_hotkey():
    """暂停/继续的热键回调 - 立即响应，耗时操作放到线程"""
    global continue_pressed
    logger.warning("监听到暂停/继续热键...")
    if pause_event.is_set():
        logger.warning("暂停运行...")
        pause_event.clear()  # 立即暂停
        mover._release_all_keys()  # 立即释放按键
        threading.Thread(target=_do_pause_action, daemon=True).start()
    else:
        logger.warning("唤醒运行...")
        continue_pressed = True
        pause_event.set()  # 立即继续
        threading.Thread(target=_do_resume_action, daemon=True).start()


def _pynput_key_to_keyboard_key(pynput_key):
    """将pynput的Key转换为keyboard库的键名"""
    key_map = {
        'Key.end': 'end',
        'Key.delete': 'delete',
        'Key.home': 'home',
        'Key.insert': 'insert',
        'Key.page_up': 'page up',
        'Key.page_down': 'page down',
        'Key.pause': 'pause',
        'Key.f1': 'f1', 'Key.f2': 'f2', 'Key.f3': 'f3', 'Key.f4': 'f4',
        'Key.f5': 'f5', 'Key.f6': 'f6', 'Key.f7': 'f7', 'Key.f8': 'f8',
        'Key.f9': 'f9', 'Key.f10': 'f10', 'Key.f11': 'f11', 'Key.f12': 'f12',
    }
    key_str = str(pynput_key)
    return key_map.get(key_str, key_str.replace('Key.', ''))


# 当前注册的热键，用于重新注册时先取消
_current_hotkeys = {'stop': None, 'pause': None}
_hotkey_listener_running = False


def _get_hotkey_config():
    """获取热键配置"""
    import importlib
    # 重新加载配置模块以获取最新配置
    importlib.reload(dnf)
    
    stop_key = 'end'
    pause_key = 'delete'
    
    try:
        if dnf.key_stop_script:
            for k in dnf.key_stop_script:
                stop_key = _pynput_key_to_keyboard_key(k)
                break
        if dnf.key_pause_script:
            for k in dnf.key_pause_script:
                pause_key = _pynput_key_to_keyboard_key(k)
                break
    except Exception as e:
        logger.warning(f"读取热键配置失败，使用默认值: {e}")
    
    return stop_key, pause_key


# Windows虚拟键码映射
_VK_CODE_MAP = {
    'end': 0x23, 'delete': 0x2E, 'home': 0x24, 'insert': 0x2D,
    'page up': 0x21, 'page down': 0x22, 'pause': 0x13,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
}


def _key_to_vk(key_name):
    """将键名转换为Windows虚拟键码"""
    return _VK_CODE_MAP.get(key_name.lower(), 0)


def reload_hotkeys():
    """重新注册热键（供GUI调用）- 使用轮询方式无需重新注册"""
    stop_key, pause_key = _get_hotkey_config()
    logger.info(f"热键配置已更新: {stop_key}=停止, {pause_key}=暂停/继续")
    return stop_key, pause_key


def start_keyboard_listener():
    """使用Windows API轮询方式监听热键，不受游戏按键影响"""
    import ctypes
    global _hotkey_listener_running
    
    _hotkey_listener_running = True
    user32 = ctypes.windll.user32
    
    # 获取热键配置
    stop_key, pause_key = _get_hotkey_config()
    stop_vk = _key_to_vk(stop_key)
    pause_vk = _key_to_vk(pause_key)
    
    logger.info(f"已启动热键轮询监听: {stop_key}(VK={hex(stop_vk)})=停止, {pause_key}(VK={hex(pause_vk)})=暂停/继续")
    
    # 防抖动 - 增加防抖时间，避免重复触发
    last_stop_time = 0
    last_pause_time = 0
    debounce_interval = 0.5  # 增加到500ms
    
    # 记录上次按键状态，只在按下瞬间触发
    last_stop_state = False
    last_pause_state = False
    
    while not stop_be_pressed and _hotkey_listener_running:
        current_time = time.time()
        
        # 检查停止键 (GetAsyncKeyState返回最高位为1表示按下)
        stop_pressed = bool(stop_vk and user32.GetAsyncKeyState(stop_vk) & 0x8000)
        if stop_pressed and not last_stop_state:  # 只在按下瞬间触发（上升沿）
            if current_time - last_stop_time >= debounce_interval:
                last_stop_time = current_time
                on_stop_hotkey()
        last_stop_state = stop_pressed
        
        # 检查暂停键
        pause_pressed = bool(pause_vk and user32.GetAsyncKeyState(pause_vk) & 0x8000)
        if pause_pressed and not last_pause_state:  # 只在按下瞬间触发（上升沿）
            if current_time - last_pause_time >= debounce_interval:
                last_pause_time = current_time
                on_pause_hotkey()
        last_pause_state = pause_pressed
        
        time.sleep(0.05)  # 50ms轮询间隔


def self_handle_stuck(hero_x, hero_y, kbd_current_direction, door_xywh_list, door_boss_xywh_list, 
                      obstacle_xywh_list, hero_xywh, img0, rows, cols, path_stack):
    """
    小卡处理函数 - 角色卡住时的绕行逻辑
    
    返回: (处理类型, 绕行方向)
    
    优先级顺序:
    1. 左上角/右上角特殊处理
    2. 小地图分析
    3. 障碍物绕行
    4. 边缘强制移动
    5. 站在门上处理
    6. 随机方向
    """
    stuck_handle_type = "随机方向"
    random_direct = random.choice(random.choice([kbu.single_direct, kbu.double_direct]))
    
    # ========== 1. 左上角/右上角特殊处理（最高优先级）==========
    if hero_y < 420 and hero_x < 300:
        return "上小卡处理-左上角", random.choice(["RIGHT", "RIGHT_DOWN", "DOWN"])
    
    if hero_y < 420 and hero_x > 750:
        return "上小卡处理-右上角", random.choice(["LEFT", "LEFT_DOWN", "DOWN"])
    
    # ========== 2. 小地图分析 ==========
    previous = None
    try:
        map_crop = map_util.get_small_map_region_img(img0, rows, cols)
        current_room = map_util.current_room_index_cropped(map_crop, rows, cols)
        if current_room != (-1, -1) and path_stack:
            if current_room in [item[0] for item in path_stack]:
                for ii in range(len(path_stack) - 1, 0, -1):
                    if path_stack[ii][0] == current_room:
                        previous = path_stack[ii - 1][1]
                        stuck_handle_type = f"小地图分析(房间{current_room},来自{previous})"
                        if hero_x < 100 and door_xywh_list and len(door_xywh_list) == 1 and door_xywh_list[0][0] < 100:
                            random_direct = random.choice(list(filter(
                                lambda x1: x1 != get_opposite_direction(previous) and x1 != kbd_current_direction and x1 not in ["DOWN", "LEFT"], kbu.single_direct)))
                        else:
                            random_direct = random.choice(list(filter(
                                lambda x1: x1 != get_opposite_direction(previous) and x1 != kbd_current_direction, kbu.single_direct)))
                        break
            else:
                previous = path_stack[-1][1]
                stuck_handle_type = f"小地图分析(房间{current_room},未finder,来自{previous})"
                random_direct = random.choice(list(filter(
                    lambda x1: x1 != get_opposite_direction(previous) and x1 != kbd_current_direction, kbu.single_direct)))
            
            # 通用上方卡住处理
            if hero_y < 420 and kbd_current_direction and "UP" in kbd_current_direction:
                if hero_x < 500:
                    return "上小卡处理-左侧", random.choice(["RIGHT", "RIGHT_DOWN"])
                else:
                    return "上小卡处理-右侧", random.choice(["LEFT", "LEFT_DOWN"])
    except Exception as e:
        logger.error(f"小地图分析异常: {e}")
    
    # ========== 3. 障碍物绕行 ==========
    if obstacle_xywh_list and kbd_current_direction:
        nearest_obs = None
        min_dist = float('inf')
        for obs in obstacle_xywh_list:
            dist = ((obs[0] - hero_x) ** 2 + (obs[1] - hero_y) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                nearest_obs = obs
        
        if nearest_obs and min_dist < 200:  # 只处理近距离障碍物
            obs_x, obs_y = nearest_obs[0], nearest_obs[1]
            obs_w = nearest_obs[2] if len(nearest_obs) > 2 else 60
            obs_h = nearest_obs[3] if len(nearest_obs) > 3 else 40
            
            if "RIGHT" in kbd_current_direction or "LEFT" in kbd_current_direction:
                base_dir = "RIGHT" if "RIGHT" in kbd_current_direction else "LEFT"
                if hero_y < 350:
                    return f"障碍物绕行(距离{min_dist:.0f})", f"{base_dir}_DOWN"
                elif hero_y > 420:
                    return f"障碍物绕行(距离{min_dist:.0f})", f"{base_dir}_UP"
                else:
                    dist_up = abs(hero_y - (obs_y - obs_h / 2))
                    dist_down = abs((obs_y + obs_h / 2) - hero_y)
                    if dist_up < dist_down:
                        return f"障碍物绕行(距离{min_dist:.0f})", f"{base_dir}_UP"
                    else:
                        return f"障碍物绕行(距离{min_dist:.0f})", f"{base_dir}_DOWN"
            
            elif "UP" in kbd_current_direction or "DOWN" in kbd_current_direction:
                base_dir = "UP" if "UP" in kbd_current_direction else "DOWN"
                if hero_x < 150:
                    return f"障碍物绕行(距离{min_dist:.0f})", f"RIGHT_{base_dir}"
                elif hero_x > 900:
                    return f"障碍物绕行(距离{min_dist:.0f})", f"LEFT_{base_dir}"
                else:
                    dist_left = abs(hero_x - (obs_x - obs_w / 2))
                    dist_right = abs((obs_x + obs_w / 2) - hero_x)
                    if dist_left < dist_right:
                        return f"障碍物绕行(距离{min_dist:.0f})", f"LEFT_{base_dir}"
                    else:
                        return f"障碍物绕行(距离{min_dist:.0f})", f"RIGHT_{base_dir}"
    
    # ========== 4. 边缘强制移动 ==========
    img_width = img0.shape[1] if img0 is not None else 1024
    img_height = img0.shape[0] if img0 is not None else 600
    
    if hero_y < 400 and hero_x > 850:
        return "边缘强制(右上角)", "LEFT"
    if hero_x > img_width * 3 // 4:
        return "边缘强制(右边)", "LEFT"
    if hero_y < 400 and hero_x < 200:
        return "边缘强制(左上角)", "RIGHT"
    if hero_x < img_width // 5:
        return "边缘强制(左边)", "RIGHT"
    
    # ========== 5. 站在门上处理 ==========
    all_doors = door_xywh_list + door_boss_xywh_list
    if all_doors and hero_xywh:
        near_door = exist_near(hero_xywh, all_doors, 100)
        if near_door:
            if hero_x < img_width // 5:
                if hero_y < img_height * 3 // 5:
                    return "站在门上", random.choice(['RIGHT', 'RIGHT_DOWN'])
                return "站在门上", "RIGHT"
            elif hero_x > img_width * 4 // 5:
                return "站在门上", "LEFT"
            elif hero_y > img_height * 3 // 5:
                return "站在门上", random.choice(["UP", "LEFT", "RIGHT"])
            else:
                return "站在门上", random.choice(["DOWN", "LEFT", "RIGHT"])
    
    # ========== 6. 返回默认 ==========
    return stuck_handle_type, random_direct


def analyse_det_result(results, hero_height, img):
    global show
    if results is not None and len(results):
        boss_xywh_list = []
        monster_xywh_list = []
        elite_monster_xywh_list = []

        loot_xywh_list = []
        gold_xywh_list = []
        door_xywh_list = []
        door_boss_xywh_list = []
        obstacle_xywh_list = []

        hero_conf = -1
        hero_xywh = None

        card_num = 0
        continue_exist = False
        shop_exist = False
        shop_mystery_exist = False
        menu_exist = False
        sss_exist = False

        result = results[0]
        for box in result.boxes:
            cls = int(box.cls)
            xywh = box.xywh[0].tolist()
            xyxy = box.xyxy[0].tolist()
            conf = box.conf[0]

            # 高度处理
            if names[cls] == "hero":
                xywh[1] += hero_height

                if conf > hero_conf:  # 找一个置信度最大的hero,记录索引
                    hero_conf = conf
                    hero_xywh = xywh

            if names[cls] == "boss":
                # xywh[1] += b_h
                xywh[1] = xyxy[3] - 20

                boss_xywh_list.append(xywh)

            if names[cls] == "monster":
                xywh[1] += monster_h

                monster_xywh_list.append(xywh)

            if names[cls] == "elite-monster":
                # xywh[1] += em_h
                xywh[1] = xyxy[3] - 20

                elite_monster_xywh_list.append(xywh)

            if names[cls] == "door":
                xywh[1] += door_h

                door_xywh_list.append(xywh)

            if names[cls] == "door-boss":
                xywh[1] += door_h

                door_boss_xywh_list.append(xywh)

            if names[cls] == "loot":
                xywh[1] += loot_h
                # 处理半拉子框的情况
                if xywh[2] > 111 and xywh[3] < 110:
                    if (xyxy[1] + 60) > xywh[1]:
                        xywh[1] = xyxy[1] + 60
                loot_xywh_list.append(xywh)

            if names[cls] == 'gold':
                xywh[1] += loot_h
                if xywh[2] > 111 and xywh[3] < 110:
                    if (xyxy[1] + 60) > xywh[1]:
                        xywh[1] = xyxy[1] + 60

                gold_xywh_list.append(xywh)

            if names[cls] == "continue":
                continue_exist = True

            if names[cls] == "card":
                card_num = card_num + 1

            if names[cls] == "shop":
                shop_exist = True

            if names[cls] == "shop-mystery":
                shop_mystery_exist = True

            if names[cls] == "menu":
                menu_exist = True

            if names[cls] == "sss":
                sss_exist = True

            if names[cls] == "obstacle":
                obstacle_xywh_list.append(xywh)

            # 在原图上画框
            if show and img is not None:
                label = '%s %.2f' % (names[int(cls)], conf)
                # plot_one_box(box.xyxy[0], img, label=label, color=colors[int(cls)], line_thickness=2)
                # plot_one_box(box.xyxy[0], img, label=label, color=hex_to_bgr(name_colors[int(cls)]['color']), line_thickness=2)
                plot_one_box(box.xyxy[0], img, label=label, color=name_colors[int(cls)], line_thickness=2)

        res = DetResult()
        res.monster_xywh_list = monster_xywh_list
        res.elite_monster_xywh_list = elite_monster_xywh_list
        res.boss_xywh_list = boss_xywh_list
        res.loot_xywh_list = loot_xywh_list
        res.gold_xywh_list = gold_xywh_list
        res.door_xywh_list = door_xywh_list
        res.door_boss_xywh_list = door_boss_xywh_list
        res.obstacle_xywh_list = obstacle_xywh_list

        res.hero_xywh = hero_xywh
        # res.hero_conf = hero_conf

        res.card_num = card_num
        res.continue_exist = continue_exist
        res.shop_exist = shop_exist
        res.shop_mystery_exist = shop_mystery_exist
        res.menu_exist = menu_exist
        res.sss_exist = sss_exist

        # 给角色绘制定位圆点,方便查看
        if show:
            if res.hero_xywh:
                # 处理后的中心
                cv2.circle(img, (int(hero_xywh[0]), int(hero_xywh[1])), 1, color_green, 2)
                # 推理后的中心
                cv2.circle(img, (int(hero_xywh[0]), int(hero_xywh[1] - hero_height)), 1, color_red, 2)

            for a in (res.loot_xywh_list + res.gold_xywh_list):
                # 掉落物
                cv2.circle(img, (int(a[0]), int(a[1])), 1, color_green, 2)
                cv2.circle(img, (int(a[0]), int(a[1] - loot_h)), 1, color_red, 2)

            for a in (res.door_xywh_list + res.door_boss_xywh_list):
                # 门口
                cv2.circle(img, (int(a[0]), int(a[1])), 1, color_green, 2)
                cv2.circle(img, (int(a[0]), int(a[1] - door_h)), 1, color_red, 2)

            for a in (res.monster_xywh_list):
                # 怪
                cv2.circle(img, (int(a[0]), int(a[1])), 1, color_green, 2)
                cv2.circle(img, (int(a[0]), int(a[1] - monster_h)), 1, color_red, 2)

        return res


def judge_is_target_door(current_room, door_box, hero_box, next_room_direction, allow_directions, path_stack, d, img0):
    """
    判断是否是目标门
    :param current_room:
    :param door_box:
    :param next_room_direction:
    :param allow_directions:
    :param path_stack:
    :param d:
    :param img0:
    :return:
    """
    if door_box is None:
        logger.debug("判断是否是目标门，空的，否")
        return False
    if len(allow_directions) == len(d.door_xywh_list + d.door_boss_xywh_list):
        # 一屏全部出现了，肯定是目标门
        logger.debug("判断是否是目标门，全部出现，是")
        return True
    else:

        previous = None
        if current_room in [item[0] for item in path_stack]:
            for ii in range(len(path_stack) - 1, 0, -1):
                if path_stack[ii][0] == current_room:
                    previous = path_stack[ii - 1][1]
                    break

        # last_room = get_last_room_info(current_room, path_history)
        # previous = None if not last_room else last_room.direction

        if len(allow_directions) == 2 and previous == 'RIGHT' and door_box[0] > img0.shape[1] * 3 // 4 and door_box[0] - \
                hero_box[0] > 170:
            logger.debug("判断是否是目标门，2门入口门在左，可能处于右，是")
            return True
        if len(allow_directions) == 2 and previous == 'LEFT' and door_box[0] < img0.shape[1] // 4 and hero_box[0] - \
                door_box[0] > 170:
            logger.debug("判断是否是目标门，2门入口门在右，可能处于左，是")
            return True

        if next_room_direction == 'RIGHT' and door_box[0] > img0.shape[1] * 3 // 4:
            logger.debug("判断是否是目标门，目标右，处于右，是")
            return True
        elif next_room_direction == 'LEFT' and door_box[0] < img0.shape[1] // 5:
            logger.debug("判断是否是目标门，目标左，处于左，是")
            return True
        else:
            # if previous == "RIGHT" and door_box[0] < img0.shape[1] // 6:
            if previous == "RIGHT" and door_box[0] < img0.shape[1] * 7 // 50:
                logger.debug("判断是否是目标门，太靠左了贴着入口，否")
                return False
            elif previous == "LEFT" and door_box[0] > img0.shape[1] * 5 // 6:
                logger.debug("判断是否是目标门，太靠右了贴着入口，否")
                return False
            else:
                if next_room_direction == 'DOWN' and door_box[1] > img0.shape[0] * 775 // 1000 and (
                        img0.shape[1] // 7 < door_box[0] < img0.shape[1] * 6 // 7):
                    logger.debug("判断是否是目标门，目标下，可能是")
                    return True
                if next_room_direction == 'UP' and door_box[1] < img0.shape[0] * 0.72 and (
                        img0.shape[1] // 7 < door_box[0] < img0.shape[1] * 6 // 7):
                    logger.debug("判断是否是目标门，目标上，可能是")
                    return True
    logger.warning("判断是否是目标门，无法判断，否")
    return False


def minimap_analyse(capturer):
    # 分析小地图
    cols, rows = 0, 0
    cur_row, cur_col = 0, 0
    map_crop = None
    boss_room = (-1, -1)
    current_room = (-1, -1)
    map_error_cnt = 0
    analyse_map_error = True
    while analyse_map_error:
        try:
            img0 = capturer.capture()

            # 分析小地图的行列
            cols = map_util.get_colum_count(img0)
            rows = map_util.get_row_count(img0)
            # logger.warning("分析小地图的行列{},{}", rows, cols)

            # 裁剪小地图区域
            map_crop = map_util.get_small_map_region_img(img0, rows, cols)

            # 获取boss房间位置，0基
            boss_room = map_util.get_boss_from_crop(map_crop, rows, cols)
            # logger.info('boss房间是 {}', boss_room)
            current_room = map_util.current_room_index_cropped(map_crop, rows, cols)  # 实际上没有用，只是打印看一下位置
            # logger.info('当前房间是 {}', current_room)
            cur_row, cur_col = current_room
        except Exception as e:
            logger.error(e)
            traceback.print_exc()

        analyse_map_error = boss_room is None or current_room is None or boss_room == (-1, -1) or current_room == (
        -1, -1)
        if analyse_map_error:
            map_error_cnt = map_error_cnt + 1
            # cv2.imwrite(f'errorDetectMap_init_{map_error_cnt}.jpg', img0)
            # logger.error(f"分析小地图的行列init，第 {map_error_cnt} 次出错,行列是 {rows} , {cols}")
            # logger.error("暂停2秒继续重试！！")
            time.sleep(0.2)
        else:
            map_error_cnt = 0

        if analyse_map_error and map_error_cnt > 20:
            logger.error("分析小地图的行列init多次出错了 废了！！！")
            return None
    return boss_room, (rows, cols), current_room


def adjust_stutter_alarm(start_time,role_name,role_no,fight_count,handle):
    import keyboard
    count = False
    paused_time = 0  # 记录暂停的总时间
    last_check_time = time.time()
    paused_logged = False  # 是否已输出暂停日志
    
    while not stop_signal[0] and not stop_be_pressed:
        time.sleep(1)
        
        # 再次检查停止标志，避免在sleep期间停止后继续执行
        if stop_be_pressed:
            logger.debug("超时检测线程：检测到停止信号，退出")
            return
        
        # 检查是否处于暂停状态
        if not pause_event.is_set():
            # 暂停中，累计暂停时间，不计入超时
            paused_time += time.time() - last_check_time
            last_check_time = time.time()
            if not paused_logged:
                logger.debug("超时检测线程：脚本已暂停，暂停计时")
                paused_logged = True
            continue
        
        # 恢复运行，重置暂停日志标志
        paused_logged = False
        
        last_check_time = time.time()
        # 计算实际运行时间（排除暂停时间）
        actual_elapsed = (time.time() - start_time) - paused_time
        
        if actual_elapsed > 60 and not count:
            logger.warning(f'第【{role_no}】个角色，【{role_name}】第【{fight_count}】次刷图,卡门【{actual_elapsed:.1f}】秒,尝试按键移动角色至上个门口~~~~~~')
            # 先释放所有按键，否则游戏可能不响应
            mover._release_all_keys()
            time.sleep(0.3)
            # 暂停主循环，防止按键被重新按下
            pause_event.clear()
            time.sleep(0.3)
            # 再次释放确保干净
            mover._release_all_keys()
            time.sleep(0.2)
            # 用pynput按键，和技能按键一样的方式
            kbu.do_press_with_time(dnf.Key_collect_role, 300, 200)
            logger.info(f'已按下 numpad_7 键，返回上一地图')
            time.sleep(1)
            # 恢复主循环
            pause_event.set()
            count = True
        elif actual_elapsed > 100:
            # 发送邮件前再次检查停止标志
            if stop_be_pressed:
                logger.debug("超时检测线程：检测到停止信号，跳过发送邮件")
                return
            capture_window_image(handle).save(os.path.join(os.getcwd(), "mail_imgs", "alarm_mali.png"))
            email_subject = "DNF妖气助手"
            email_content = f"""运行状态实时监控\n{datetime.now().strftime('%Y年%m月%d日 %H时%M分%S秒')}\n{'自己账号' if account_code == 1 else '五子账号'}第{role_no}个角色，{role_name}第{fight_count}次刷图,{actual_elapsed:.1f}秒内没通关地下城,请及时查看处理。"""
            email_receiver = mail_config.get("receiver")
            email_img = [os.path.join(os.getcwd(), "mail_imgs", "alarm_mali.png")]
            tool_executor.submit(lambda: (
                mail_sender.send_email_with_images(email_subject, email_content, email_receiver,email_img),
                logger.info(f"第{role_no}个角色{role_name}第{fight_count}次刷图,长时间卡门 已经发送邮件提醒了")))
            return




# <<<<<<<<<<<<<<<< 方法定义 <<<<<<<<<<<<<<<<

def main_script():
    global x, y, handle, show, game_mode, stop_signal, stop_be_pressed
    # ################### 主流程开始 ###############################
    start_time = datetime.now()
    logger.info("_____________________准备_____________________")
    logger.info(f"脚本参数: first_role_no={first_role_no}, last_role_no={last_role_no}, account_code={account_code}")
    time.sleep(1)

    try:
        _run_main_script()
    except StopIteration as e:
        logger.warning(f"脚本被用户停止: {e}")
    except Exception as e:
        logger.error(f"脚本执行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        end_time = datetime.now()
        logger.info(f'脚本开始: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        logger.info(f'脚本结束: {end_time.strftime("%Y-%m-%d %H:%M:%S")}')
        time_delta = end_time - start_time
        logger.info(f'总计耗时: {(time_delta.total_seconds() / 60):.1f} 分钟')
        logger.info("脚本执行结束")
        mover._release_all_keys()
        
        # 停止展示线程
        if show:
            stop_display_thread()
        
        # 脚本正常执行完,不是被组合键中断的,并且配置了退出游戏
        if not stop_be_pressed and quit_game_after_finish:
            logger.info("正在退出游戏...")
            try:
                clik_to_quit_game(handle, x, y)
                time.sleep(5)
            except Exception as e:
                logger.error(f"退出游戏失败: {e}")
        
        # 关机
        if not stop_be_pressed and quit_game_after_finish and shutdown_pc_after_finish:
            logger.info("一分钟之后关机...")
            os.system("shutdown /s /t 60")


def _run_main_script():
    global x, y, handle, show, game_mode, stop_signal, stop_be_pressed, display_thread
    
    # 加载模型（延迟加载，首次调用时才真正加载）
    model, device = get_model()
    
    # 启动展示线程（如果show=True）
    if show:
        start_display_thread()
    
    # 获取游戏窗口的位置，和大小
    handle = window_utils.get_window_handle(dnf.window_title)
    x, y, width, height = window_utils.get_window_rect(handle)
    logger.info("获取游戏窗口位置和大小...{},{},{},{}", x, y, width, height)
    window_utils.resize_window(handle)
    logger.warning("矫正窗口大小:1067*600")
    capturer = WindowCapture(handle)

    # 获取角色配置列表
    role_list = get_role_config_list(account_code, use_json=use_json_config)
    logger.info(f"读取角色配置列表(来源:{'JSON文件' if use_json_config else 'role_list.py'})...")
    logger.info(f"共有{len(role_list)}个角色，将从第{first_role_no}个执行到第{last_role_no}个")

    pause_event.wait()  # 暂停
    # 遍历角色, 循环刷图
    for i in range(len(role_list)):
        # 检查停止标志
        check_stop()
            
        pause_event.wait()  # 暂停
        role = role_list[i]
        role_no = i + 1  # 角色编号从1开始
        
        # 判断,从指定的角色开始,其余的跳过
        if (first_role_no != -1 and role_no < first_role_no) or (
                role_no in break_role_no and break_role and game_mode in (1, 3, 6)):
            if role_no < first_role_no:
                logger.warning(f'[跳过]-【{role_no}】[{role.name}]...')
                continue
            logger.warning(f'第{role.no}个角色{role.name}不执行模式【{game_mode}】,切换到下一个角色...')
            safe_sleep(4)
            # 检查停止标志
            if stop_be_pressed:
                logger.warning("检测到停止信号，退出...")
                break
            # esc打开菜单
            safe_sleep(0.5)
            # kbu.do_press(Key.esc)
            mu.do_smooth_move_to(x + 832, y + 576)  # 通过点击菜单按钮打开菜单
            safe_sleep(0.5)
            mu.do_click(Button.left)
            safe_sleep(0.5)
            pause_event.wait()  # 暂停
            if stop_be_pressed:
                logger.warning("检测到停止信号，退出...")
                break
            # 鼠标移动到选择角色，点击 偏移量（1038,914）
            # mu.do_smooth_move_to(x + 607, y + 576)
            mu.do_smooth_move_to(x + 506, y + 504)
            safe_sleep(0.5)
            mu.do_click(Button.left)
            # 等待加载角色选择页面
            safe_sleep(5)

            # 默认停留在刚才的角色上，直接按一次右键，空格
            kbu.do_press(Key.right)
            safe_sleep(0.2)
            kbu.do_press(Key.space)
            # 等待进入游戏
            safe_sleep(3)
            # 多次检测弹窗
            for _ in range(3):
                if close_new_day_dialog(handle, x, y, capturer):
                    safe_sleep(0.3)
                    break
                safe_sleep(0.3)
            continue
        
        # 检查是否超过结束角色
        if last_role_no != -1 and role_no > last_role_no:
            logger.warning(f'已到达结束角色【{last_role_no}】，退出循环')
            break
        
        # 检查并关闭0点弹窗（多次检测，因为弹窗可能延迟出现）
        try:
            for _ in range(3):
                if close_new_day_dialog(handle, x, y, capturer):
                    safe_sleep(0.5)  # 关闭弹窗后等待一下
                    break
                safe_sleep(0.5)
        except Exception as e:
            logger.warning(f"检测0点弹窗失败: {e}")
            
        logger.warning(f'第【{role_no}】个角色，【{role.name}】 开始了')
        oen_role_start_time = datetime.now()

        if role_no > 20 and game_mode == 2:
            logger.warning(f'前20个每日1+1已经结束了')
            break

        # 检查停止标志
        if stop_be_pressed:
            logger.warning("检测到停止信号，退出角色循环...")
            break

        # 读取角色配置
        hero_height = role.height  # 高度
        # 读取疲劳值配置
        if enable_uniform_pl:
            role.fatigue_reserved = uniform_default_fatigue_reserved
        skill_images = {}

        # 等待加载角色完成
        safe_sleep(4)

        # # 确保展示右下角的图标
        # show_right_bottom_icon(capturer.capture(), x, y)

        logger.info(f'设置的拥有疲劳值: {role.fatigue_all}')

        # ocr_fatigue = do_ocr_fatigue_retry(handle, x, y, reader, 5)
        ocr_fatigue = do_recognize_fatigue(capturer.capture())
        logger.info(f'识别的拥有疲劳值: {ocr_fatigue}')
        if ocr_fatigue is not None:
            if role.fatigue_all != ocr_fatigue:
                logger.warning(f'更新疲劳值--->(计算): {role.fatigue_all},(识别): {ocr_fatigue}')
            role.fatigue_all = ocr_fatigue

        # 角色当前疲劳值
        current_fatigue = role.fatigue_all
        fatigue_cost = 16  # 一把消耗的疲劳值
        if game_mode == 3 or game_mode == 4:
            fatigue_cost = 8

        logger.info(f'{role.name},拥有疲劳值:{role.fatigue_all},预留疲劳值:{role.fatigue_reserved}')

        # 如果需要刷图,这选择副本,进入副本
        need_fight = current_fatigue - fatigue_cost >= role.fatigue_reserved if role.fatigue_reserved > 0 else current_fatigue > 0

        # 判断1+1是否能点
        if need_fight and game_mode == 2:
            mu.do_move_and_click(x + 767, y + 542)
            time.sleep(0.1)
            daily_1and1_clickable = detect_daily_1and1_clickable(capturer.capture())
            time.sleep(0.1)
            kbu.do_press(Key.esc)
            if not daily_1and1_clickable:
                logger.warning("1+1点不了,跳过...")
            need_fight = daily_1and1_clickable

        if need_fight:
            pause_event.wait()  # 暂停
            # todo 奶爸刷图,切换输出加点
            # if '奶爸' in role.name:
            #     logger.info("是奶爸,准备切换加点...")
            #     crusader_to_battle(x, y)

            pause_event.wait()  # 暂停
            # 默认是站在赛丽亚房间

            # 获取技能栏截图
            skill_images = get_skill_initial_images(capturer.capture())

            if game_mode != 2:
                # N 点第一个
                logger.info("传送到风暴门口,选地图...")
                # 传送到风暴门口
                from_sailiya_to_abyss(x, y)
                logger.info("先向上移，保持顶到最上位置。。")
                kbu.do_press_with_time(Key.up, 800, 50)
                # # 让角色走到最左面，进图选择页面
                # logger.info("再向左走，进入选择地图页面。。")
                # kbu.do_press_with_time(Key.left, 2500, 300)

                # 先向右移动一点，以防一传过来的就离得很近
                logger.info("向右移一点，以防一传过来的就离得很近。。")
                kbu.do_press_with_time(Key.right, 1000, 50)
                logger.info("向左走向左走，进入选择地图页面。。")
                kbu.do_press_with_time(Key.left, 2500, 50)
                kbu.do_press_with_time(Key.down, 1500, 50)
                time.sleep(0.5)
                time.sleep(1.5)  # 先等自己移动到深渊图

            if game_mode == 2:
                goto_daily_1and1(x, y)
            elif game_mode == 1:
                goto_white_map_level(x, y, role.white_map_level)
            elif game_mode == 3:
                goto_zhuizong(x, y)
            elif game_mode == 4:
                goto_jianmie(x, y)

            pause_event.wait()  # 暂停

            # 检查是否成功进入地图
            img0 = capturer.capture()
            enter_map_success = not detect_return_town_button_when_choose_map(img0)
            # 进不去
            if not enter_map_success:
                logger.error(f'第【{i + 1}】【{role.name}】，进不去地图,结束当前角色')
                time.sleep(0.2)
                # esc 关闭地图选择界面
                kbu.do_press(Key.esc)
                time.sleep(0.2)
                need_fight = False

        # 刷图流程开始>>>>>>>>>>
        logger.warning(f'第【{i + 1}】个角色【{role.name}】已经进入地图,刷图打怪循环开始...')

        # # 隐藏掉右下角的图标
        # if need_fight:
        #     hide_right_bottom_icon(capturer.capture(), x, y)

        # ##############################
        # 记录一下刷图次数
        fight_count = 0
        # 角色刷完结束
        finished = False

        # todo 循环进图开始>>>>>>>>>>>>>>>>>>>>>>>>
        # 一直循环
        pause_event.wait()  # 暂停
        while not finished and need_fight and not stop_be_pressed:  # 循环进图
            # 检查停止标志
            if stop_be_pressed:
                logger.warning("检测到停止信号，退出刷图循环...")
                break
            # 先要等待地图加载 todo 改动态识别
            # time.sleep(4.5)
            pause_event.wait()  # 暂停
            try:
                t1 = time.time()
                time.sleep(0.2)
                load_map_task = tool_executor.submit(minimap_analyse, capturer)
                load_map_success = load_map_task.result(timeout=5)
                if load_map_success:
                    logger.info(f"地图加载完成！{(time.time() - t1):.2f}s")
            except Exception as e:
                logger.error("地图加载任务异常")
                logger.error(e)
                traceback.print_exc()

            # 不管了,全部释放掉
            mover._release_all_keys()

            pause_event.wait()  # 暂停

            fight_count += 1
            logger.info(f'【{role.name}】 刷图,第 {fight_count} 次，开始...')
            one_game_start = time.time()
            # # 记录疲劳值
            # current_fatigue_ocr = do_ocr_fatigue_retry(handle, x, y, reader, 5)  # 识别疲劳值
            current_fatigue_ocr = do_recognize_fatigue(capturer.capture())  # 识别疲劳值
            logger.info(f'当前还有疲劳值(识别): {current_fatigue_ocr}')

            global continue_pressed
            if continue_pressed:
                # exception_count = 0  # 主动唤醒过,重置异常次数
                continue_pressed = False

            pause_event.wait()  # 暂停

            # 上Buff
            logger.info(f'准备上Buff..')
            if role.buff_effective:
                for buff in role.buffs:
                    kbu.do_buff(buff)
            else:
                logger.info(f'不需要上Buff..')

            # 分析小地图
            cols, rows = 0, 0
            cur_row, cur_col = 0, 0
            map_crop = None
            boss_room = (-1, -1)
            current_room = (-1, -1)

            map_error_cnt = 0
            analyse_map_error = True
            while analyse_map_error:
                try:
                    img0 = capturer.capture()

                    # 分析小地图的行列
                    cols = map_util.get_colum_count(img0)
                    rows = map_util.get_row_count(img0)
                    logger.warning("分析小地图的行列{},{}", rows, cols)

                    # 裁剪小地图区域
                    map_crop = map_util.get_small_map_region_img(img0, rows, cols)

                    # 获取boss房间位置，0基
                    boss_room = map_util.get_boss_from_crop(map_crop, rows, cols)
                    logger.info('boss房间是 {}', boss_room)
                    current_room = map_util.current_room_index_cropped(map_crop, rows, cols)  # 实际上没有用，只是打印看一下位置
                    logger.info('当前房间是 {}', current_room)
                    cur_row, cur_col = current_room
                except Exception as e:
                    logger.error(e)
                    traceback.print_exc()

                analyse_map_error = boss_room is None or current_room is None or boss_room == (
                -1, -1) or current_room == (-1, -1)
                if analyse_map_error:
                    map_error_cnt = map_error_cnt + 1
                    # cv2.imwrite(f'errorDetectMap_init_{map_error_cnt}.jpg', img0)
                    logger.error(f"分析小地图的行列init，第 {map_error_cnt} 次出错,行列是 {rows} , {cols}")
                    logger.error("暂停2秒继续重试！！")
                    safe_sleep(1)
                    if stop_be_pressed:
                        break
                else:
                    map_error_cnt = 0

                if analyse_map_error and map_error_cnt > 20:
                    logger.error("分析小地图的行列init多次出错了 废了！！！")
                    # cv2.imwrite(f'errorDetectMap_init_{map_error_cnt}.jpg', capturer.capture())
                    break

            allow_directions = map_util.get_allow_directions(map_crop, cur_row, cur_col)

            # 初始化
            finder = PathFinder(rows, cols, boss_room)
            stop_signal[0] = False  # 重置超时检测标志
            threading.Thread(target=adjust_stutter_alarm, args=(one_game_start,role.name,role.no,fight_count,handle)).start()
            logger.info(f'准备打怪..')

            # todo 循环打怪过图 循环开始////////////////////////////////
            fq = FixedLengthQueue(max_length=30)
            room_idx_list = FixedLengthQueue(max_length=100)
            stuck_room_idx = None
            hero_pos_is_stable = False

            collect_loot_pressed = False  # 按过移动物品了
            collect_loot_pressed_time = 0
            boss_appeared = False  # 遭遇boss了
            sss_appeared = False  # 已经结算了
            door_absence_time = 0  # 什么也没识别到的时间(没识别到门)
            boss_door_appeared = False
            path_stack = []  # ((x,y),direction) 房间，去下一个房间的方向
            card_esc_time = 0
            card_appear_time = 0
            hero_stuck_pos = {}  # 卡住的位置 ((r,c),[(x,y),(x,y)])
            die_time = 0
            in_boss_room = False

            frame_time = time.time()
            frame_interval = 1.0 / max_fps if max_fps else 0
            while True:  # 循环打怪过图
                # 检查停止标志
                if stop_be_pressed:
                    logger.warning("检测到停止信号，退出打怪循环...")
                    break
                
                # 限制处理速率 - 精确等待到下一帧时间
                if frame_interval:
                    elapsed = time.time() - frame_time
                    if elapsed < frame_interval:
                        # 直接sleep剩余时间，避免频繁轮询
                        time.sleep(frame_interval - elapsed)
                    frame_time = time.time()

                pause_event.wait()  # 暂停

                # 截图
                img0 = capturer.capture()


                # 识别
                cv_det_task = None
                if boss_appeared or in_boss_room or boss_door_appeared or game_mode == 2:
                    cv_det_task = img_executor.submit(object_detection_cv, img0)
                # 只在需要展示时复制图像，减少CPU开销
                img4show = img0.copy() if show else img0
                # 执行推理
                results = model.predict(
                    source=img0,
                    device=device,
                    imgsz=640,
                    conf=0.7,
                    iou=0.2,
                    verbose=False
                )
                
                # 障碍物模型推理并合并结果
                if model_obstacle is not None:
                    results_obstacle = model_obstacle.predict(
                        source=img0,
                        device=device,
                        imgsz=640,
                        conf=0.5,
                        iou=0.2,
                        verbose=False
                    )
                    if results_obstacle and len(results_obstacle) > 0 and len(results_obstacle[0].boxes) > 0:
                        obstacle_boxes = results_obstacle[0].boxes
                        # 获取原模型识别的door位置，用于去重
                        main_door_boxes = []
                        if results and len(results) > 0:
                            for j, main_cls in enumerate(results[0].boxes.cls):
                                if int(main_cls) == 3:  # door
                                    main_door_boxes.append(results[0].boxes.xyxy[j].tolist())
                        
                        for i, cls in enumerate(obstacle_boxes.cls):
                            cls_id = int(cls)
                            new_box = obstacle_boxes.data[i]
                            
                            # obstacle类别(14)直接合并
                            if cls_id == 14:
                                if results and len(results) > 0:
                                    results[0].boxes.data = torch.cat([results[0].boxes.data, new_box.unsqueeze(0)], dim=0)
                            
                            # door类别(3)需要去重：检查是否和原模型的door重叠
                            elif cls_id == 3:
                                new_xyxy = obstacle_boxes.xyxy[i].tolist()
                                is_duplicate = False
                                for main_box in main_door_boxes:
                                    # 计算IoU判断是否重叠
                                    x1 = max(new_xyxy[0], main_box[0])
                                    y1 = max(new_xyxy[1], main_box[1])
                                    x2 = min(new_xyxy[2], main_box[2])
                                    y2 = min(new_xyxy[3], main_box[3])
                                    inter = max(0, x2 - x1) * max(0, y2 - y1)
                                    area1 = (new_xyxy[2] - new_xyxy[0]) * (new_xyxy[3] - new_xyxy[1])
                                    area2 = (main_box[2] - main_box[0]) * (main_box[3] - main_box[1])
                                    iou = inter / (area1 + area2 - inter + 1e-6)
                                    if iou > 0.3:  # IoU > 0.3 认为是同一个门
                                        is_duplicate = True
                                        break
                                
                                # 不重复的门才合并
                                if not is_duplicate and results and len(results) > 0:
                                    results[0].boxes.data = torch.cat([results[0].boxes.data, new_box.unsqueeze(0)], dim=0)
                                    logger.debug(f"新模型补充识别到门，位置: {new_xyxy}")

                if results is None or len(results) == 0 or len(results[0].boxes) == 0:
                    # logger.info('模型没有识别到物体')
                    if not sss_appeared:
                        mover.move(target_direction=random.choice(kbu.single_direct))
                    continue

                # # todo
                # if show:
                #     annotated_frame = results[0].plot()
                #     # 将结果放入队列，供展示线程使用
                #     result_queue.put(annotated_frame)

                # print('results[0].boxes', results[0].boxes)
                # 分析推理结果,组装类别数据
                det = analyse_det_result(results, hero_height, img4show)
                # logger.debug(f'det_res是什么 {det}')
                # logger.debug(f'doors:{det.door_xywh_list}')

                hero_xywh = det.hero_xywh
                monster_xywh_list = det.monster_xywh_list
                elite_monster_xywh_list = det.elite_monster_xywh_list
                boss_xywh_list = det.boss_xywh_list
                loot_xywh_list = det.loot_xywh_list
                gold_xywh_list = det.gold_xywh_list
                door_xywh_list = det.door_xywh_list
                door_boss_xywh_list = det.door_boss_xywh_list
                obstacle_xywh_list = det.obstacle_xywh_list
                
                # 检测到障碍物时输出日志
                if obstacle_xywh_list:
                    logger.info(f"识别到{len(obstacle_xywh_list)}个障碍物")

                card_num = det.card_num
                continue_exist = det.continue_exist
                shop_exist = det.shop_exist
                shop_mystery_exist = det.shop_mystery_exist
                menu_exist = det.menu_exist
                sss_exist = det.sss_exist

                if stuck_room_idx is not None:
                    logger.debug("材料卡住了,loot_xywh_list置空")
                    loot_xywh_list = []
                    gold_xywh_list = []

                if sss_exist or continue_exist or shop_exist or shop_mystery_exist:
                    # logger.debug(f"出现翻牌{sss_exist}，再次挑战了{continue_exist}")
                    if not sss_appeared:
                        sss_appeared = True
                        logger.warning(
                            f'【{role.name}】 刷图,第 {fight_count} 次，打怪结束，耗时...{(time.time() - one_game_start):.1f}秒')
                        stop_signal = [True]
                if door_boss_xywh_list:
                    if not boss_door_appeared:
                        logger.info(f"出现boss门了")
                        boss_door_appeared = True
                if boss_xywh_list:
                    if not boss_appeared:
                        logger.info(f"出现boss了")
                        boss_appeared = True
                        in_boss_room = True

                if cv_det_task:
                    cv_det = cv_det_task.result()
                    if cv_det and cv_det["death"]:

                        logger.warning(f"角色死了")

                        if time.time() - die_time > 11:
                            die_time = time.time()
                            logger.warning(f"死亡提醒!!")
                            # 声音提醒 不要
                            # 邮件提醒
                            mode_name = (
                                "白图" if game_mode == 1 else
                                "每日1+1" if game_mode == 2 else
                                "妖气追踪" if game_mode == 3 else
                                "妖怪歼灭" if game_mode == 4 else
                                "未知模式"
                            )
                            email_subject = f"{mode_name} {role.name}阵亡通知书"
                            email_content = f"鏖战{mode_name}，角色【{role.name}】不幸阵亡，及时查看处理。"
                            mail_receiver = mail_config.get("receiver")
                            if mail_receiver:
                                tool_executor.submit(lambda: (
                                    mail_sender.send_email(email_subject, email_content, mail_receiver),
                                    logger.info("角色死亡 已经发送邮件提醒了")
                                ))
                            else:
                                logger.warning("角色死亡 邮件提醒没有配置,跳过")

                        logger.warning(f"检测到死了，准备复活")
                        safe_sleep(8)  # 拖慢点复活
                        if stop_be_pressed:
                            break
                        kbu.do_press('x')
                        time.sleep(0.1)
                        kbu.do_press('x')
                        time.sleep(0.1)

                if hero_xywh:
                    fq.enqueue((hero_xywh[0], hero_xywh[1]))
                    hero_pos_is_stable = fq.coords_is_stable(threshold=10, window_size=10)
                    if hero_pos_is_stable and not sss_appeared and stuck_room_idx is None:
                        kbd_current_direction = mover.get_current_direction()
                        hero_x, hero_y = hero_xywh[0], hero_xywh[1]
                        
                        # 调用小卡处理函数
                        stuck_handle_type, random_direct = self_handle_stuck(
                            hero_x, hero_y, kbd_current_direction, 
                            door_xywh_list, door_boss_xywh_list, obstacle_xywh_list,
                            hero_xywh, img0, rows, cols, path_stack
                        )
                        
                        # 执行移动
                        fq.clear()
                        room_idx_list.clear()
                        stuck_room_idx = None
                        logger.warning(f'小卡处理【{stuck_handle_type}】，位置({hero_x:.0f},{hero_y:.0f})，绕行方向-->{random_direct}')
                        mover.move(target_direction=random_direct)
                        time.sleep(round(random.uniform(0.2, 0.6), 1))
                        continue
                else:  # todo 没有识别到角色
                    if not sss_appeared:
                        random_direct = random.choice(kbu.single_direct)
                        logger.warning('未检测到角色,随机跑个方向看看{}', random_direct)
                        # mover._release_all_keys()
                        mover.move(target_direction=random_direct)
                    else:
                        logger.info('未检测到角色,已经结算了')
                        if not collect_loot_pressed and (
                                sss_exist or continue_exist or shop_exist or shop_mystery_exist):
                            # kbu.do_press_with_time(Key.left, 3000, 100)
                            mover.move(target_direction="LEFT")
                            time.sleep(0.1)
                    # continue

                # ############################### 判断-准备打怪 ######################################
                wait_for_attack = hero_xywh and (
                            monster_xywh_list or boss_xywh_list or elite_monster_xywh_list) and not sss_appeared
                monster_box = None
                monster_in_range = False
                role_attack_center = None
                best_attack_point = None
                if wait_for_attack:

                    if stuck_room_idx:
                        stuck_room_idx = None
                        room_idx_list.clear()

                    role_attack_center = (hero_xywh[0], hero_xywh[1])
                    if mover.get_current_direction() is None or "RIGHT" in mover.get_current_direction():
                        role_attack_center = (hero_xywh[0] + role.attack_center_x, hero_xywh[1])
                    else:
                        role_attack_center = (hero_xywh[0] - role.attack_center_x, hero_xywh[1])

                    # 距离最近的怪 todo 改成最近的堆
                    # monster_box, _ = get_closest_obj(itertools.chain(monster_xywh_list, boss_xywh_list), role_attack_center)
                    monster_box = find_densest_monster_cluster(
                        monster_xywh_list + boss_xywh_list + elite_monster_xywh_list, role_attack_center)

                    if show:
                        # 怪(堆中心) 蓝色
                        cv2.circle(img4show, (int(monster_box[0]), int(monster_box[1])), 5, color_blue, 4)
                    # 怪处于攻击范围内
                    # monster_in_range = abs(hero_xywh[0] - monster_box[0]) < attx and abs(hero_xywh[1] - monster_box[1]) < atty

                    if role.attack_center_x:
                        if mover.get_current_direction() is None or "RIGHT" in mover.get_current_direction():
                            monster_in_range = (monster_box[0] > role_attack_center[0]
                                                and abs(role_attack_center[0] - monster_box[0]) < attack_x
                                                and abs(role_attack_center[1] - monster_box[1]) < attack_y
                                                ) or (
                                                       monster_box[0] < role_attack_center[0]
                                                       and abs(role_attack_center[0] - monster_box[0]) < (
                                                                   role.attack_center_x * 0.65)
                                                       and abs(role_attack_center[1] - monster_box[1]) < attack_y
                                               )
                        else:
                            monster_in_range = (monster_box[0] < role_attack_center[0]
                                                and abs(role_attack_center[0] - monster_box[0]) < attack_x
                                                and abs(role_attack_center[1] - monster_box[1]) < attack_y
                                                ) or (
                                                   (monster_box[0] > role_attack_center[0]
                                                    and abs(role_attack_center[0] - monster_box[0]) < (
                                                                role.attack_center_x * 0.65)
                                                    and abs(role_attack_center[1] - monster_box[1]) < attack_y
                                                    )
                                               )
                    else:
                        if mover.get_current_direction() is None or "RIGHT" in mover.get_current_direction():
                            monster_in_range = (monster_box[0] > role_attack_center[0]
                                                and abs(role_attack_center[0] - monster_box[0]) < attack_x
                                                and abs(role_attack_center[1] - monster_box[1]) < attack_y
                                                )
                        else:
                            monster_in_range = (monster_box[0] < role_attack_center[0]
                                                and abs(role_attack_center[0] - monster_box[0]) < attack_x
                                                and abs(role_attack_center[1] - monster_box[1]) < attack_y
                                                )

                    # if fought_boss:
                    #     monster_in_range = abs(hero_xywh[0] - monster_box[0]) < 300 and abs(hero_xywh[1] - monster_box[1]) < 200
                    if show and monster_in_range:
                        # 怪处于攻击范围内,给角色一个标记
                        cv2.circle(img4show, (int(hero_xywh[0]), int(hero_xywh[1])), 10, color_yellow, 2)

                # # todo 待考虑
                # if not wait_for_attack and not sss_appeared:
                #     cur_row, cur_col = map_util.current_room_index_cropped(map_crop, rows, cols)
                #     current_room = (cur_row, cur_col)
                #     map_crop = map_util.get_small_map_region_img(img0, rows, cols)

                # ############################ 判断-准备进入下一个房间 ####################################
                # todo 门开了 = map_util.门开了()
                wait_for_next_room = (hero_xywh
                                      and ((
                                                       door_xywh_list or door_boss_xywh_list) and not monster_xywh_list and not elite_monster_xywh_list and not boss_xywh_list and not loot_xywh_list and not gold_xywh_list)
                                      and not sss_appeared)
                next_room_direction = None
                door_box = None
                door_in_range = False
                if wait_for_next_room:

                    door_absence_time = 0
                    # 根据小地图分析 下一个房间所在的方向(上校左右)
                    try:
                        map_door_error_cnt = 0
                        analyse_map_door_error = True
                        while analyse_map_door_error:
                            allow_directions = []
                            in_boss_room = False
                            try:
                                img00 = capturer.capture()

                                # 裁剪小地图区域
                                map_crop = map_util.get_small_map_region_img(img00, rows, cols)
                                # 当前房间位置
                                current_room = map_util.current_room_index_cropped(map_crop, rows, cols)
                                logger.info('当前房间是 {}', current_room)
                                cur_row, cur_col = current_room

                                if current_room == boss_room or (boss_door_appeared and current_room == (-1, -1)):
                                    in_boss_room = True

                                allow_directions = map_util.get_allow_directions(map_crop, cur_row, cur_col)
                                logger.debug(f"allow_directions:{allow_directions}")
                            except Exception as e:
                                logger.error(e)
                                traceback.print_exc()

                            analyse_map_door_error = not allow_directions
                            if analyse_map_door_error:
                                if in_boss_room:
                                    logger.info("在boss房间分析出错，无视")
                                    break
                                map_door_error_cnt = map_door_error_cnt + 1
                                # cv2.imwrite(f'errorDetectMap_door_{map_door_error_cnt}.jpg', map_crop)
                                logger.error(
                                    f"分析小地图的行列door，第 {map_door_error_cnt} 次出错,行列是 {rows} , {cols}")
                                logger.error("暂停2秒继续重试！！")
                                safe_sleep(2)
                                if stop_be_pressed:
                                    break
                            else:
                                map_door_error_cnt = 0
                                next_room_direction = finder.get_next_direction((cur_row, cur_col), allow_directions)
                                logger.debug(f"next_room_direction:{next_room_direction}")

                                if path_stack and path_stack[-1][0] == current_room:
                                    pass
                                else:
                                    if next_room_direction:
                                        logger.debug(
                                            f"加入path, 当前房间是 {current_room}, 模板方向是 {next_room_direction}")
                                        path_stack.append((current_room, next_room_direction))

                            if analyse_map_door_error and map_door_error_cnt > 5:
                                logger.error("分析小地图的行列door多次出错了 废了！！！")
                                break

                        if next_room_direction is None or current_room is None:
                            # 没正确的分析出小地图信息,跳过
                            logger.warning('没正确的分析出小地图信息,跳过')
                            continue
                    except Exception as e:
                        logger.warning(f'小地图分析异常报错,跳过.{e}')
                        traceback.print_exc()
                        # boss_room = map_util.get_boss_room(window_utils.capture_window_BGRX(handle))
                        # logger.info('boss房间是 {}', boss_room)
                        continue

                    if stuck_room_idx is not None and stuck_room_idx == current_room:  # 已经被卡住了，且还位于被卡房间（材料置空--无意义--能进这个逻辑，材料list肯定已经是空的）
                        logger.debug("已经被材料时有时无卡住了,忽略材料")
                        loot_xywh_list = []
                        gold_xywh_list = []
                        wait_for_next_room = hero_xywh and (
                                (
                                            door_xywh_list or door_boss_xywh_list) and not monster_xywh_list and not elite_monster_xywh_list and not boss_xywh_list and not loot_xywh_list and not gold_xywh_list)
                    elif stuck_room_idx is not None and stuck_room_idx != current_room:  # 已经被卡住了，且不在被卡房间，（出去了，置空）
                        stuck_room_idx = None
                        room_idx_list.enqueue(current_room)  # 记录识别的房间位置
                    else:  # 还没有被卡住
                        room_idx_list.enqueue(current_room)  # 记录识别的房间位置
                        room_is_same = room_idx_list.room_is_same(min_size=80)
                        if room_is_same and not hero_pos_is_stable:  # 之前没卡住，刚刚计算得到卡住
                            logger.warning(f"可能可能可能可能被材料时有时无 卡住了 当前房间{current_room}")
                            stuck_room_idx = current_room
                            room_idx_list.clear()
                        else:  # 之前没卡住，现在也没卡住
                            stuck_room_idx = None

                    # 找这个方向上最远的门
                    door_box = find_door_by_position(door_xywh_list + door_boss_xywh_list, next_room_direction)

                    door_in_range = abs(door_box[1] - hero_xywh[1]) < door_hit_y * 2 and abs(
                        door_box[0] - hero_xywh[0]) < door_hit_x  # todo 门的范围问题
                    if show and door_box:
                        # 给目标门口画一个点
                        cv2.circle(img4show, (int(door_box[0]), int(door_box[1])), 1, color_blue, 3)

                # ####################### 判断-准备拾取材料 #############################################
                # wait_for_pickup = hero_xywh and (not monster_xywh_list and hero_xywh and (loot_xywh_list or gold_xywh_list) and not continue_exist)
                wait_for_pickup = hero_xywh and (loot_xywh_list or gold_xywh_list) and (
                        not monster_xywh_list and not elite_monster_xywh_list and not boss_xywh_list)
                material_box = None
                loot_in_range = False
                material_min_distance = float("inf")
                material_is_gold = False
                if wait_for_pickup:
                    # 距离最近的掉落物
                    material_box, material_min_distance = get_closest_obj(
                        itertools.chain(loot_xywh_list, gold_xywh_list), det.hero_xywh)
                    if material_box in gold_xywh_list:
                        material_is_gold = True
                    if show and material_box:
                        # 给目标掉落物画一个点
                        cv2.circle(img4show, (int(material_box[0]), int(material_box[1])), 2, color_blue, 3)
                    # 材料处于拾取范围
                    loot_in_range = abs(material_box[1] - hero_xywh[1]) < pick_up_y and abs(
                        material_box[0] - hero_xywh[0]) < pick_up_x
                    if show and loot_in_range:
                        # 材料处于拾取范围,给角色一个标记
                        cv2.circle(img4show, (int(hero_xywh[0]), int(hero_xywh[1])), 10, color_yellow, 2)

                # 截图展示前的处理完毕,放入队列由独立线程显示
                if show:
                    # 非阻塞放入，队列满则丢弃（保证主循环不卡）
                    try:
                        result_queue.put_nowait(img4show)
                    except queue.Full:
                        pass  # 队列满了就跳过这帧
                # ######################### 判断完毕,进行逻辑处理 ########################################################

                # 逻辑处理-找门进入下个房间>>>>>>>>>>>>>>>>>>>>>>>>>>
                if wait_for_next_room:

                    pause_event.wait()  # 暂停

                    is_target_door = judge_is_target_door(current_room, door_box, hero_xywh, next_room_direction,
                                                          allow_directions, path_stack, det, img0)
                    logger.info(f"判断目标门：{is_target_door}")

                    # todo 门还要处理，做追踪？
                    # if len(allow_directions) > len(door_xywh_list + door_boss_xywh_list):
                    if not is_target_door:
                        # 尚未出现目标门,需要继续移动寻找
                        if next_room_direction == 'RIGHT' and (
                                not door_box or door_box[0] < img0.shape[1] * 4 // 5):
                            logger.debug("目标房间在右边---->右侧四分之一还没有门出现,继续往右")
                            mover.move(target_direction="RIGHT")
                            continue
                        if next_room_direction == 'LEFT' and (
                                not door_box or door_box[0] > img0.shape[1] // 5):
                            logger.debug("目标房间在左边---->左侧四分之一还没有门出现,继续往左")
                            mover.move(target_direction="LEFT")
                            continue
                        if next_room_direction == 'DOWN' and (
                                not door_box or door_box[1] <= img0.shape[0] * 775 // 1000 or (door_box and (
                                door_box[0] < img0.shape[1] // 7 or door_box[0] > img0.shape[1] * 6 // 7))):
                            logger.debug("目标房间在下边---->下侧四分之一还没有门出现,继续往下")
                            mover.move(target_direction="DOWN")
                            continue
                        if next_room_direction == 'UP' and (not door_box or door_box[1] > img0.shape[0] * 0.72 or (
                                door_box and (
                                door_box[0] < img0.shape[1] // 7 or door_box[0] > img0.shape[1] * 6 // 7))):
                            logger.debug("目标房间在上边---->上侧二分之一还没有门出现,继续往上")
                            mover.move(target_direction="UP")
                            continue

                    # 门在命中范围内,等待过图即可
                    if door_in_range:
                        # 上下门需要持续按住方向键才能过门，不能停下来
                        if next_room_direction in ('UP', 'DOWN'):
                            logger.info(f"门在命中范围内,继续往{next_room_direction}走过门")
                            mover.move(target_direction=next_room_direction)
                        else:
                            # 左右门可以释放按键等待过图
                            mover._release_all_keys()
                            logger.info("门在命中范围内,等待过图")
                        time.sleep(0.1)
                        if stuck_room_idx is not None:
                            # todo 除歼灭不存在 跳过材料时无卡住的逻辑
                            logger.debug("等三秒直接跳过材料")
                            time.sleep(1)
                            # 可能没过去，继续朝目标方向走两步
                            if next_room_direction == 'RIGHT':
                                logger.debug("继续向右走两步")
                                mover.move(target_direction="RIGHT")
                                time.sleep(0.5)
                            if next_room_direction == 'LEFT':
                                logger.debug("继续向左走两步")
                                mover.move(target_direction="LEFT")
                                time.sleep(0.5)
                            if next_room_direction == 'UP':
                                logger.debug("继续向上走两步")
                                mover.move(target_direction="UP")
                                time.sleep(0.5)
                            if next_room_direction == 'DOWN':
                                logger.debug("继续向下走两步")
                                mover.move(target_direction="DOWN")
                                time.sleep(0.5)
                            # stuck_room_idx = None
                            # room_idx_list.clear()
                        continue

                    # 已经确定目标门,移动到目标位置
                    # 计算与门的距离差
                    dx = door_box[0] - hero_xywh[0]  # 正数表示门在右边
                    dy = door_box[1] - hero_xywh[1]  # 正数表示门在下边
                    abs_dx = abs(dx)
                    abs_dy = abs(dy)
                    
                    # 使用更大的阈值判断是否需要调整方向，避免来回蹭
                    y_threshold = door_hit_y * 1.5  # Y方向阈值放宽
                    
                    # 确定移动方向
                    target_dir = None
                    
                    # 向下过门时，需要多走一点才能触发过门
                    if next_room_direction == 'DOWN':
                        if abs_dx < door_hit_x:
                            # X方向已对齐，继续往下走
                            target_dir = "DOWN"
                        elif dx > 0:
                            target_dir = "RIGHT_DOWN"
                        else:
                            target_dir = "LEFT_DOWN"
                    # 向上过门
                    elif next_room_direction == 'UP':
                        if abs_dx < door_hit_x:
                            target_dir = "UP"
                        elif dx > 0:
                            target_dir = "RIGHT_UP"
                        else:
                            target_dir = "LEFT_UP"
                    # 向左右过门，Y方向已经对齐，只需要水平移动
                    elif abs_dy < y_threshold:
                        target_dir = "RIGHT" if dx > 0 else "LEFT"
                    # X方向距离更远，优先斜向移动
                    elif abs_dx > abs_dy:
                        if dx > 0 and dy < 0:
                            target_dir = "RIGHT_UP"
                        elif dx > 0 and dy > 0:
                            target_dir = "RIGHT_DOWN"
                        elif dx < 0 and dy < 0:
                            target_dir = "LEFT_UP"
                        else:
                            target_dir = "LEFT_DOWN"
                    # Y方向距离更远，优先垂直移动
                    else:
                        if dy < 0:
                            target_dir = "UP"
                        else:
                            target_dir = "DOWN"
                    
                    if target_dir:
                        # 障碍物绕行：检测障碍物是否在角色前进路径上
                        if obstacle_xywh_list and hero_xywh and door_box:
                            hero_x, hero_y = hero_xywh[0], hero_xywh[1]
                            door_x, door_y = door_box[0], door_box[1]
                            
                            for obs in obstacle_xywh_list:
                                obs_x, obs_y = obs[0], obs[1]
                                obs_w, obs_h = obs[2] if len(obs) > 2 else 60, obs[3] if len(obs) > 3 else 40
                                
                                # 计算距离
                                dist_to_hero = ((obs_x - hero_x) ** 2 + (obs_y - hero_y) ** 2) ** 0.5
                                
                                # 检测距离放宽到200像素，提前绕行
                                if dist_to_hero > 200:
                                    logger.debug(f"障碍物太远，位置({obs_x:.0f},{obs_y:.0f})，距离{dist_to_hero:.0f}")
                                    continue
                                
                                # 判断障碍物是否在前进方向上
                                in_path = False
                                if "RIGHT" in target_dir and obs_x > hero_x:
                                    # 向右走，障碍物在右边，且Y轴接近
                                    if abs(obs_y - hero_y) < obs_h + 50:
                                        in_path = True
                                elif "LEFT" in target_dir and obs_x < hero_x:
                                    # 向左走，障碍物在左边，且Y轴接近
                                    if abs(obs_y - hero_y) < obs_h + 50:
                                        in_path = True
                                elif target_dir == "UP" and obs_y < hero_y:
                                    if abs(obs_x - hero_x) < obs_w + 50:
                                        in_path = True
                                elif target_dir == "DOWN" and obs_y > hero_y:
                                    if abs(obs_x - hero_x) < obs_w + 50:
                                        in_path = True
                                
                                if in_path:
                                    # 根据障碍物坐标和屏幕边界选择最短绕行路径
                                    if "RIGHT" in target_dir or "LEFT" in target_dir:
                                        # 水平移动时，计算上下绕行距离
                                        # 障碍物上边缘到角色的距离（向上绕）
                                        dist_up = hero_y - (obs_y - obs_h / 2)
                                        # 障碍物下边缘到角色的距离（向下绕）
                                        dist_down = (obs_y + obs_h / 2) - hero_y
                                        
                                        # 选择绕行方向：优先考虑屏幕边界
                                        # 游戏区域Y轴范围约300-480，角色Y>420认为在底部，Y<350认为在顶部
                                        base_dir = "RIGHT" if "RIGHT" in target_dir else "LEFT"
                                        if hero_y < 350:
                                            # 角色在顶部，向下绕
                                            target_dir = f"{base_dir}_DOWN"
                                        elif hero_y > 420:
                                            # 角色在底部，向上绕
                                            target_dir = f"{base_dir}_UP"
                                        elif dist_up < dist_down:
                                            # 向上绕距离更短
                                            target_dir = f"{base_dir}_UP"
                                        else:
                                            # 向下绕距离更短
                                            target_dir = f"{base_dir}_DOWN"
                                    else:
                                        # 垂直移动时，计算左右绕行距离
                                        dist_left = hero_x - (obs_x - obs_w / 2)
                                        dist_right = (obs_x + obs_w / 2) - hero_x
                                        
                                        # 游戏区域X轴范围约50-1000，角色X<150认为在左边，X>900认为在右边
                                        base_dir = "UP" if "UP" in target_dir else "DOWN"
                                        if hero_x < 150:
                                            target_dir = f"RIGHT_{base_dir}"
                                        elif hero_x > 900:
                                            target_dir = f"LEFT_{base_dir}"
                                        elif dist_left < dist_right:
                                            target_dir = f"LEFT_{base_dir}"
                                        else:
                                            target_dir = f"RIGHT_{base_dir}"
                                    
                                    logger.warning(f"执行障碍物绕行！位置({obs_x:.0f},{obs_y:.0f})，距离{dist_to_hero:.0f}，绕行方向{target_dir}")
                                    break
                        
                        mover.move(target_direction=target_dir)

                    continue
                # 逻辑处理-找门进入下个房间<<<<<<<<<<<<<<<<<<<<<<<<<

                # 逻辑处理-有怪要打怪>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                if wait_for_attack:
                    # 处于攻击范围
                    if monster_in_range and mover.get_current_direction() is not None:

                        # 不管了,全部释放掉
                        mover._release_all_keys()

                        # 调整方向,面对怪
                        if hero_xywh[0] - monster_box[0] > 100:
                            logger.debug('面对怪,朝左，再放技能')
                            kbu.do_press(Key.left)
                        elif monster_box[0] > hero_xywh[0] > 100:
                            logger.debug('面对怪,朝右，再放技能')
                            kbu.do_press(Key.right)
                        time.sleep(0.05)

                        skill_name = None
                        if role.powerful_skills and (boss_xywh_list):
                            # skill_name = skill_util.suggest_skill_powerful(role, img0)
                            skill_name = skill_util.get_available_skill_from_list_by_match(skills=role.powerful_skills,
                                                                                           img0=img0,
                                                                                           skill_images=skill_images)
                        if skill_name is None:
                            # 推荐技能
                            # skill_name = skill_util.suggest_skill(role, img0)
                            skill_name = skill_util.suggest_skill_by_img_match(role, img0, skill_images)
                        skill_util.cast_skill(skill_name)
                        # 小等一下 比如等怪死
                        if skill_name == 'x':
                            ...
                        else:
                            time.sleep(0.1)
                        continue

                    pause_event.wait()  # 暂停
                    # 使用统一的移动逻辑
                    move_to_target(
                        mover,
                        hero_pos=(role_attack_center[0], role_attack_center[1]),
                        target_pos=(monster_box[0], monster_box[1]),
                        y_threshold=attack_y
                    )
                    continue
                # 逻辑处理-有怪要打怪<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

                # 逻辑处理-出现菜单>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                if menu_exist:
                    kbu.do_press(Key.esc)
                    logger.info("关闭菜单")
                    time.sleep(0.1)
                    continue
                # 逻辑处理-出现菜单<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

                # 逻辑处理-捡材料>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                if wait_for_pickup:
                    if gold_xywh_list:
                        # logger.error(f"有金币金币金币!  {gold_xywh_list}")
                        pass
                    if sss_appeared and not collect_loot_pressed:
                        logger.info("预先移动物品到脚下")
                        # 不管了,全部释放掉
                        mover._release_all_keys()

                        collect_loot_pressed = True
                        collect_loot_pressed_time = time.time()

                        executor.submit(lambda: (
                            logger.info("预先移动物品到脚下"),
                            time.sleep(2.1),
                            kbu.do_press(dnf.Key_collect_loot),
                            time.sleep(0.1),
                            kbu.do_press_with_time('x', 4000 if game_mode == 4 else 2000, 50),
                            logger.info("预先长按x 按完x了"),
                        ))

                        continue
                    elif sss_appeared and collect_loot_pressed and time.time() - collect_loot_pressed_time < 7:
                        tt = time.time()
                        if 0.1 < tt - int(tt) < 0.2:  # 0.6 < tt - int(tt) < 0.75
                            logger.info(
                                f"已经预先按下移动物品了，10s内忽略拾取...{int(7 - (time.time() - collect_loot_pressed_time))}")
                        continue

                    # 掉落物在范围内,直接拾取
                    if loot_in_range:
                        # 不管了,全部释放掉
                        mover._release_all_keys()
                        # 金币自动拾取，不需要按x；只有材料才需要按x
                        if not material_is_gold:
                            time.sleep(0.1)
                            kbu.do_press("x")
                            logger.debug("捡材料按完x了")
                        else:
                            logger.debug("金币自动拾取，无需按x")
                        continue

                    # # 如果被材料卡在当前房间了,忽略材料
                    # if stuck_room_idx:
                    #     logger.error("捡东西---》被材料卡在当前房间了,忽略材料")
                    #     continue

                    # 掉落物不在范围内,需要移动
                    byWalk = False
                    if material_min_distance < 150:
                        byWalk = True
                    # slow_pickup = not material_is_gold or material_min_distance < 100
                    slow_pickup = material_min_distance < 100

                    # todo 靠近门口的的,小碎步去捡
                    # door_is_near = exist_near(material_box, door_xywh_list, threshold=200)
                    door_is_near = False
                    near_door_list = get_objs_in_range(material_box, door_xywh_list + door_boss_xywh_list,
                                                       threshold=200)

                    if near_door_list:
                        logger.warning("存在距离材料很近的门！")
                        for door in near_door_list:
                            # 如果材料位于门和角色之间
                            if (
                                    (door[0] <= material_box[0] <= hero_xywh[0] or door[0] >= material_box[0] >=
                                     hero_xywh[0])
                                    and (
                                    door[1] <= material_box[1] <= hero_xywh[1]
                                    or door[1] >= material_box[1] >= hero_xywh[1]
                                    or (abs(door[1] - material_box[1]) < 100 and abs(
                                door[1] - hero_xywh[1]) < 100 and abs(material_box[1] - hero_xywh[1]) < 100)
                            )
                            ):
                                # logger.error(f"门:{door}, 材料：{material_box}， 角色：{hero_xywh}")
                                door_is_near = True
                            elif (
                                    (door[1] <= material_box[1] <= hero_xywh[1] or door[1] >= material_box[1] >=
                                     hero_xywh[1])
                                    and (
                                            door[0] <= material_box[0] <= hero_xywh[0]
                                            or door[0] >= material_box[0] >= hero_xywh[0]
                                            or (abs(door[0] - material_box[0]) < 100 and abs(
                                        door[0] - hero_xywh[0]) < 100 and abs(material_box[0] - hero_xywh[0]) < 100)
                                    )
                            ):
                                # logger.error(f"门:{door}, 材料：{material_box}， 角色：{hero_xywh}")
                                door_is_near = True

                        if door_is_near:
                            logger.info("材料离门口太近了!!")
                            if gold_xywh_list:
                                logger.info(f"是金币离门口太近了!!!  {gold_xywh_list}")
                            byWalk = True
                            if not slow_pickup:
                                slow_pickup = True
                        else:
                            logger.info("但是材料角色门口 不影响")

                    pause_event.wait()  # 暂停
                    move_mode = 'walking' if byWalk else 'running'
                    # 使用统一的移动逻辑
                    direction = calculate_move_direction(
                        hero_pos=(hero_xywh[0], hero_xywh[1]),
                        target_pos=(material_box[0], material_box[1]),
                        y_threshold=pick_up_y
                    )
                    if direction:
                        mover.move_stop_immediately(target_direction=direction, move_mode=move_mode, stop=slow_pickup)
                    continue
                # 逻辑处理-捡材料<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

                # 逻辑处理-出现再次挑战>>>>>>>>>>>>>>>>>>>>>>>>>>>
                if continue_exist:
                    # 不管了,全部释放掉
                    mover._release_all_keys()

                    # 如果商店开着,需要esc关闭
                    if shop_mystery_exist or shop_exist:
                        if shop_mystery_exist:
                            # cv2.imwrite(f'./shop_imgs/mystery_Shop_{datetime.fromtimestamp(time.time()).strftime("%Y%m%d_%H%M%S")}.jpg', img0)
                            time.sleep(1.5)
                            process_mystery_shop(capturer.capture(), x, y, buy_tank_type, buy_bell_ticket,
                                                 buy_shanshanming, buy_catalyst)  # 重新截图，防止前面截的帧有干扰不清晰
                            logger.info("神秘商店处理完毕")
                        kbu.do_press(Key.esc)
                        logger.info("商店开着,需要esc关闭")
                        time.sleep(0.1)
                        continue

                    # 不存在掉落物了,就再次挑战
                    if not loot_xywh_list and not gold_xywh_list:
                        logger.warning("出现再次挑战,并且没有掉落物了,终止")
                        # time.sleep(3)  # 等待加载地图

                        break  # 终止掉当前刷一次图的循环

                    # 聚集物品,按x
                    if (loot_xywh_list or gold_xywh_list) and not collect_loot_pressed:
                        if not collect_loot_pressed:
                            logger.info("中间移动物品到脚下")
                            kbu.do_press(dnf.Key_collect_loot)
                            collect_loot_pressed = True
                            collect_loot_pressed_time = time.time()
                            time.sleep(0.1)
                            kbu.do_press_with_time('x', 4000 if game_mode == 4 else 2000, 50)
                            logger.info("中间长按x 按完x了")
                        continue
                    continue
                # 逻辑处理-出现再次挑战<<<<<<<<<<<<<<<<<<<<<<<<<<<

                # 逻辑处理-出现翻牌>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                if card_num >= 3:
                    if not card_appear_time:
                        card_appear_time = time.time()

                        # 如果商店开着,需要esc关闭
                    if shop_mystery_exist:
                        # cv2.imwrite(f'./shop_imgs/mystery_Shop_{datetime.fromtimestamp(time.time()).strftime("%Y%m%d_%H%M%S")}.jpg', img0)
                        time.sleep(0.5)
                        process_mystery_shop(capturer.capture(), x, y, buy_tank_type, buy_bell_ticket,
                                             buy_shanshanming, buy_catalyst)  # 重新截图，防止前面截的帧有干扰不清晰

                    logger.info("翻牌时有神秘商店，处理完毕")

                    if time.time() - card_appear_time > 0.5:
                        if not card_esc_time:
                            card_esc_time = time.time()
                            # 按下esc跳过翻牌
                            kbu.do_press(Key.esc)
                            logger.debug(f"关闭翻牌,shop_mystery_exist:{shop_mystery_exist},shop_exist:{shop_exist}")
                        elif time.time() - card_esc_time >= 1.5:
                            # 按下esc跳过翻牌
                            kbu.do_press(Key.esc)
                            logger.debug(
                                f"再次关闭翻牌,shop_mystery_exist:{shop_mystery_exist},shop_exist:{shop_exist}")
                        else:
                            logger.debug("翻牌已经esc过，先等等1.5s再关闭")
                    else:
                        logger.debug("翻牌刚刚出现，先等等再关闭")

                    # 不管了,全部释放掉
                    mover._release_all_keys()
                    time.sleep(0.1)  # todo 翻牌睡两秒可行?

                    continue
                # 逻辑处理-出现翻牌<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

                # 逻辑处理-什么都没有>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                if (
                        not gold_xywh_list and not loot_xywh_list and not monster_xywh_list and not elite_monster_xywh_list and not boss_xywh_list
                        and not door_xywh_list and not door_boss_xywh_list and card_num < 3 and not continue_exist) and not sss_appeared:  # todo boss
                    pause_event.wait()  # 暂停
                    # 情况1:漏怪了,并且视野内看不到怪了,随机久了肯定能看到怪 todo 还是得做？匹配
                    # 情况2:翻牌附近
                    # 情况3:打完当前房间了,当前视野内没有门
                    if not door_absence_time:
                        door_absence_time = time.time()
                    if hero_xywh is not None:
                        logger.warning("除了角色什么也没识别到")
                        direct = random.choice(random.choice([kbu.single_direct, kbu.double_direct]))
                        try:
                            map_crop = map_util.get_small_map_region_img(img0, rows, cols)
                            cur_row, cur_col = map_util.current_room_index_cropped(map_crop, rows, cols)
                            allow_directions = map_util.get_allow_directions(map_crop, cur_row, cur_col)
                            logger.debug(f"未识别到尝试allow_directions:{allow_directions}")
                            if not allow_directions:
                                # cv2.imwrite("no_allow_directions_full1.jpg", img0)
                                # cv2.imwrite("no_allow_directions_crop1.jpg", map_crop)
                                logger.debug(f'小地图没找到对应的图{(rows, cols)},{(cur_row, cur_col)}！！！！')
                                time.sleep(1)
                                img00 = capturer.capture()
                                map_crop = map_util.get_small_map_region_img(img00, rows, cols)
                                cur_row, cur_col = map_util.current_room_index_cropped(map_crop, rows, cols)
                                allow_directions = map_util.get_allow_directions(map_crop, cur_row, cur_col)
                                current_room = (cur_row, cur_col)

                            next_room_direction = finder.get_next_direction((cur_row, cur_col), allow_directions)
                            logger.debug("计算方向2", next_room_direction)
                            logger.info(
                                f"除了角色什么也没识别到,当前房间: {cur_row},{cur_col},允许方向: {allow_directions}, 下个方向: {next_room_direction}")

                            # previous = None
                            # if current_room in [item[0] for item in path_stack]:
                            #     for ii in range(len(path_stack) - 1, 0, -1):
                            #         if path_stack[ii][0] == current_room:
                            #             previous = path_stack[ii - 1][1]
                            #             break
                            #
                            # if hero_xywh[1] < 360 and mover.get_current_direction() == "UP":
                            #     if previous == "RIGHT" and hero_xywh[0] < img0.shape[1] * 3 // 5:
                            #         direct = "RIGHT"
                            #     elif previous == "LEFT" and hero_xywh[0] > img0.shape[1] * 2 // 5:
                            #         direct = "LEFT"

                            if next_room_direction:
                                direct = next_room_direction
                        except Exception as e:
                            logger.warning(f"捕获到异常: {e}")
                            traceback.print_exc()
                            logger.warning('小地图分析异常报错,跳过2')
                            direct = random.choice(random.choice([kbu.single_direct, kbu.double_direct]))

                        if door_absence_time and time.time() - door_absence_time > 180:
                            logger.warning('什么都没检测到(没有门)已经3分钟了,随机方向')
                            direct = random.choice(random.choice([kbu.single_direct, kbu.double_direct]))

                        logger.info(f"尝试方向--->{direct}")
                        # mover._release_all_keys()
                        mover.move(target_direction=direct)

                        pass
                    else:
                        random_direct = random.choice(random.choice([kbu.single_direct, kbu.double_direct]))
                        logger.warning('角色也没识别到,什么都没识别到,随机跑个方向看看-->{}', random_direct)
                        # mover._release_all_keys()
                        mover.move(target_direction=random_direct)
                    continue
                # 逻辑处理-什么都没有<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
            # todo 循环打怪过图 循环结束////////////////////////////////
            logger.warning("循环打怪过图 循环结束////////////////////////////////")

            pause_event.wait()  # 暂停
            need_wait_collect_finish = False
            if not collect_loot_pressed:
                executor.submit(lambda: (
                    logger.info("最后移动物品到脚下"),
                    mover._release_all_keys(),
                    time.sleep(0.1),
                    kbu.do_press(dnf.Key_collect_loot),
                    time.sleep(0.1),
                    kbu.do_press_with_time('x', 4000 if game_mode == 4 else 2000, 0),
                    logger.info("最后长按x 按完x了")
                ))
                need_wait_collect_finish = True

            pause_event.wait()  # 暂停
            # 疲劳值判断
            # current_fatigue = do_ocr_fatigue_retry(handle, x, y, reader, 5)
            current_fatigue = do_recognize_fatigue(capturer.capture())
            if role.fatigue_reserved > 0 and (current_fatigue - fatigue_cost) < role.fatigue_reserved:
                # 再打一把就疲劳值就不够预留的了
                logger.info(f'再打一把就疲劳值就不够预留的{role.fatigue_reserved}了')
                logger.info(f'刷完{fight_count}次了，结束...')
                if need_wait_collect_finish:
                    safe_sleep(1.6)
                # 返回城镇
                kbu.do_press(dnf.key_return_to_town)
                safe_sleep(3)
                finished = True
                # break

            if current_fatigue <= 0:
                # 再打一把就疲劳值就不够预留的了
                logger.info(f'没有疲劳值了')
                logger.info(f'刷完{fight_count}次了，结束...')
                if need_wait_collect_finish:
                    safe_sleep(1.6)
                # 返回城镇
                kbu.do_press(dnf.key_return_to_town)
                safe_sleep(3)
                finished = True
                # break

            pause_event.wait()  # 暂停
            # 识别"再次挑战"按钮是否存在,是否可以点击
            # btn_exist, text_exist, btn_clickable = detect_try_again_button(capturer.capture())
            btn_exist, text_exist, btn_clickable = detect_try_again_button(
                capturer.capture()) if game_mode != 2 else detect_1and1_next_map_button(capturer.capture())
            # 没的刷了,不能再次挑战了
            if (game_mode != 2 and text_exist and not btn_clickable) or (game_mode == 2 and not btn_exist):
                pause_event.wait()  # 暂停
                logger.info(f'刷了{fight_count}次了,再次挑战禁用状态,不能再次挑战了...')
                if need_wait_collect_finish:
                    safe_sleep(1.6)
                # 返回城镇
                kbu.do_press(dnf.key_return_to_town)
                safe_sleep(3)
                finished = True
            else:
                # 按下再次挑战
                if game_mode == 2:
                    kbu.do_press(Key.space)
                    time.sleep(2)
                    logger.warning('等两秒 再按空格继续下一个每日的图')
                    time.sleep(2)
                    kbu.do_press(Key.space)
                    time.sleep(2)
                    kbu.do_press(Key.space)
                    time.sleep(2)
                else:
                    kbu.do_press(dnf.key_try_again)
                    logger.warning("按下再次挑战了")

        # todo 循环进图结束<<<<<<<<<<<<<<<<<<<<<<<
        
        # 停止超时检测线程
        stop_signal[0] = True

        # # 瞬移到赛丽亚房间
        # teleport_to_sailiya()
        # time.sleep(0.5)

        time_diff = datetime.now() - oen_role_start_time
        logger.warning(
            f'第【{i + 1}】个角色【{role.name}】刷图打怪循环结束...总计耗时: {(time_diff.total_seconds() / 60):.1f} 分钟')

        # 刷图流程结束<<<<<<<<<<
        # # 展示掉右下角的图标
        # show_right_bottom_icon(capturer.capture(), x, y)

        pause_event.wait()  # 暂停
        # 如果刷图了,则完成每日任务,整理背包（强制停止时跳过）
        if fight_count > 0 and not stop_be_pressed:
            logger.info('刷了图之后,进行整理....')
            pause_event.wait()  # 暂停
            if stop_be_pressed:
                logger.warning("检测到停止信号，跳过整理...")
            else:
                # 瞬移到赛丽亚房间
                teleport_to_sailiya(x, y)

                pause_event.wait()  # 暂停
                # 完成每日任务
                if game_mode == 2 and not stop_be_pressed:
                    finish_daily_challenge_by_all(x, y, game_mode == 2)

                # pause_event.wait()  # 暂停
                # # 一键出售装备,给赛丽亚
                # sale_equipment_to_sailiya()

                pause_event.wait()  # 暂停
                if not stop_be_pressed:
                    receive_mail(capturer.capture(),x, y)
                    time.sleep(0.5)
                    # 转移材料到账号金库
                    transfer_materials_to_account_vault(x, y)
                # 垃圾直播活动
                # activity_live(x, y)

        pause_event.wait()  # 暂停
        # 准备重新选择角色（当前角色编号小于最后角色编号时才选择下一个）
        if role_no < last_role_no:
            # 检查停止标志
            if stop_be_pressed:
                logger.warning("检测到停止信号，退出角色循环...")
                break
            logger.warning("准备重新选择角色")
            # esc打开菜单
            safe_sleep(0.5)
            # kbu.do_press(Key.esc)
            mu.do_smooth_move_to(x + 832, y + 576)  # 通过点击菜单按钮打开菜单
            safe_sleep(0.2)
            mu.do_click(Button.left)
            safe_sleep(0.5)

            pause_event.wait()  # 暂停
            # 检查停止标志
            if stop_be_pressed:
                logger.warning("检测到停止信号，退出角色循环...")
                break
            # 鼠标移动到选择角色，点击 偏移量（1038,914）
            # mu.do_smooth_move_to(x + 607, y + 576)
            mu.do_smooth_move_to(x + 506, y + 504)
            safe_sleep(0.2)
            mu.do_click(Button.left)
            # 等待加载角色选择页面
            safe_sleep(5)

            # 默认停留在刚才的角色上，直接按一次右键，空格
            kbu.do_press(Key.right)
            safe_sleep(0.2)
            kbu.do_press(Key.space)
            # 等待进入游戏
            safe_sleep(3)
            # 多次检测弹窗
            for _ in range(3):
                if close_new_day_dialog(handle, x, y, capturer):
                    safe_sleep(0.3)
                    break
                safe_sleep(0.3)
        else:
            logger.warning("已经刷完最后一个角色了，结束脚本")
            mode_name = (
                "白图" if game_mode == 1 else
                "每日1+1" if game_mode == 2 else
                "妖气追踪" if game_mode == 3 else
                "妖怪歼灭" if game_mode == 4 else
                "未知模式"
            )
            email_subject = f"{mode_name} 任务执行结束"
            email_content = f"{'自己账号' if account_code == 1 else '五子账号'} {email_subject}"
            mail_receiver = mail_config.get("receiver")
            capture_window_image(handle).save(os.path.join(os.getcwd(), "mail_imgs", "end_mali.png"))
            email_img = [os.path.join(os.getcwd(), "mail_imgs", "end_mali.png")]
            if mail_receiver:
                tool_executor.submit(lambda: (
                    mail_sender.send_email_with_images(email_subject, email_content, mail_receiver,email_img),
                    logger.info(f"{'自己账号' if account_code == 1 else '五子账号'}任务执行结束")
                ))
            break


# 只有直接运行此脚本时才执行以下代码，被import时不执行
if __name__ == "__main__":
    # 等待按键,启动
    logger.info(".....python主线程 启动..........")
    logger.warning(f".....请按下 {dnf.key_start_script} 组合键开始脚本...")
    kboard.wait(dnf.key_start_script)  # 等待按下组合键
    winsound.PlaySound(config_.sound1, winsound.SND_FILENAME)
    # winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
    logger.warning(f".....{dnf.key_start_script} ok....触发开始了........")

    # 创建并启动脚本线程
    script_task_thread = threading.Thread(target=main_script)
    script_task_thread.daemon = True
    script_task_thread.start()
    start_time = datetime.now()
    logger.info('')
    logger.info(f'脚本开始: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')

    # 创建并启动监听中断按键线程
    listener_thread = threading.Thread(target=start_keyboard_listener)
    listener_thread.daemon = True
    listener_thread.start()

    # 等待脚本线程结束或检测到中断信号
    while script_task_thread.is_alive():
        if stop_be_pressed:
            mover._release_all_keys()
            logger.warning(f"监听到组合键被按下,[stop_be_pressed=={stop_be_pressed}],不再阻塞,继续执行主线程代码直至退出")
            break
        time.sleep(1)

    # 运行时间已在main_script的finally中输出，这里不再重复
    logger.info("python主线程已停止.....")
