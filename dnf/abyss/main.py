# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'

import itertools
import os
import pathlib
import queue
import random
import re
import threading
import time
from datetime import datetime
import concurrent.futures

import cv2
import keyboard as kboard
import torch
import winsound
from pynput import keyboard
from pynput.keyboard import Key
from pynput.mouse import Button
from ultralytics import YOLO

import config as config_
import dnf.dnf_config as dnf
from dnf.stronger import skill_util as skill_util
from dnf.abyss.det_result import DetResult
from dnf.stronger.method import (
    detect_try_again_button,
    find_densest_monster_cluster,
    get_closest_obj
)
from dnf.stronger.player import (
    transfer_materials_to_account_vault,
    finish_daily_challenge,
    teleport_to_sailiya,
    clik_to_quit_game,
    do_ocr_fatigue_retry,
    detect_return_town_button_when_choose_map,
    from_sailiya_to_abyss,
    crusader_to_battle,
    hide_right_bottom_icon,
    show_right_bottom_icon,
    buy_from_mystery_shop,
    goto_abyss,
    buy_tank_from_mystery_shop,
    buy_bell_from_mystery_shop,
    buy_shanshanming_from_mystery_shop,
    process_mystery_shop,
    activity_live,
    do_recognize_fatigue,
    receive_mail, match_and_click,
    close_new_day_dialog,
    detect_aolakou,
)
from dnf.stronger.skill_util import get_skill_initial_images
from logger_config import logger
from dnf.stronger.role_config_manager import get_role_config_list_from_json as get_role_config_list
from utils import keyboard_utils as kbu
from utils import mouse_utils as mu
from utils import window_utils as window_utils
from utils.custom_thread_pool_executor import SingleTaskThreadPool
from utils.keyboard_move_controller import MovementController
from utils.utilities import plot_one_box
from utils.window_utils import WindowCapture, capture_window_image
from utils.utilities import match_template_by_roi
from utils.mail_sender import EmailSender
from dnf.mail_config import config as mail_config
from dnf.stronger.object_detect import object_detection_cv

temp = pathlib.PosixPath
pathlib.PosixPath = pathlib.WindowsPath

#  >>>>>>>>>>>>>>>> 运行时相关的参数 >>>>>>>>>>>>>>>>

show = False  # 查看检测结果

# 脚本执行完之后,结束游戏
quit_game_after_finish = False
# 睡觉去了,让脚本执行完之后,自己关机
shutdown_pc_after_finish = False

# 账号类型: 1=自己账号, 2=五子账号
account_code = 1
account_name = ""  # 账号显示名称（由GUI传入）

# 执行脚本的第一个角色_编号
first_role_no = 1
last_role_no = 16

# 跳过角色
break_role = False  # 是否启用跳过角色
break_role_no = []  # 要跳过的角色编号列表

# 买罐子
buy_tank_type = 0  # buy_type: 0不买，1买传说，2买史诗，3买史诗+传说
# 买铃铛
buy_bell_ticket = 2  # buy_type: 0，不买，1买粉罐子，2买传说罐子，3买粉+传说罐子
# 买闪闪明
buy_shanshanming = 2  # buy_type: 0，不买，1买粉罐子，2买传说罐子，3买粉+传说罐子
# 买催化剂
buy_catalyst = 7  # buy_type: 0不买，1传说，2史诗，3太初，4传说+史诗，5史诗+太初，6传说+太初，7全部

# 使用此处统一配置预留的疲劳值
enable_uniform_pl = False
uniform_default_fatigue_reserved = 17

weights = os.path.join(config_.project_base_path, 'weights/abyss.pt')  # 模型存放的位置
# <<<<<<<<<<<<<<<< 运行时相关的参数 <<<<<<<<<<<<<<<<

#  >>>>>>>>>>>>>>>> 脚本所需要的变量 >>>>>>>>>>>>>>>>
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
device = None
stop_signal = [False]

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
    global model, device
    if model is None:
        import time as _time
        t0 = _time.time()
        
        # 先选择设备
        device, device_name = _select_best_gpu()
        logger.info(f"选择计算设备: {device} ({device_name})")
        
        # 加载主模型并移动到指定设备
        logger.info("正在加载深渊推理模型...")
        model = YOLO(weights)
        model.to(device)
        
        # 模型预热，让首次推理更快
        logger.info("模型预热中...")
        import numpy as np
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        model.predict(source=dummy_img, device=device, verbose=False)
        logger.info(f"模型加载完成，使用设备: {device} ({device_name})，耗时: {_time.time()-t0:.1f}秒")
    return model, device
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
    'forward',
    'ball',
    'hole'
]
colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]
# ----------------------------------------------------------
boss_h = 120  # boss高度处理
monster_h = 57  # 普通怪高度处理
em_h = 100  # 精英怪高度处理
door_h = 32  # 门高度处理
loot_h = 0  # 掉落物高度处理

attack_x = 200  # 打怪命中范围，x轴距离
attack_y = 80  # 打怪命中范围，y轴距离

door_hit_y = 45  # 过门命中范围，y轴距离（增大避免来回蹭，向下过门需要更大范围）
pick_up_x = 25  # 捡材料命中范围，x轴距离
pick_up_y = 15  # 捡材料命中范围，y轴距离

# <<<<<<<<<<<<<<<< 脚本所需要的变量 <<<<<<<<<<<<<<<<
mover = MovementController()
executor = SingleTaskThreadPool()
img_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
tool_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
mail_sender = EmailSender(mail_config)  # 初始化邮件发送器


def adjust_stutter_alarm(start_time, role_name, role_no, fight_count, handle):
    """刷图异常检测和提醒（与白图一致）"""
    count = False
    paused_time = 0  # 记录暂停的总时间
    last_check_time = time.time()
    paused_logged = False  # 是否已输出暂停日志
    
    while not stop_signal[0] and not stop_be_pressed:
        time.sleep(1)
        
        # 再次检查停止标志，避免在sleep期间停止后继续执行
        if stop_be_pressed or stop_signal[0]:
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
            if stop_be_pressed or stop_signal[0]:
                logger.debug("超时检测线程：检测到停止信号，跳过发送邮件")
                return
            # 创建邮件图片目录
            mail_img_dir = os.path.join(os.getcwd(), "mail_imgs")
            os.makedirs(mail_img_dir, exist_ok=True)
            img_path = os.path.join(mail_img_dir, "alarm_abyss.png")
            capture_window_image(handle).save(img_path)
            email_subject = "DNF深渊助手"
            # 使用账号显示名称，如果没有则使用默认名称
            display_name = account_name if account_name else '未知账号'
            email_content = f"""运行状态实时监控\n{datetime.now().strftime('%Y年%m月%d日 %H时%M分%S秒')}\n{display_name}第{role_no}个角色，{role_name}第{fight_count}次刷图,{actual_elapsed:.1f}秒内没通关地下城,请及时查看处理。"""
            email_receiver = mail_config.get("receiver")
            email_img = [img_path]
            tool_executor.submit(lambda: (
                mail_sender.send_email_with_images(email_subject, email_content, email_receiver, email_img),
                logger.info(f"第{role_no}个角色{role_name}第{fight_count}次刷图,长时间卡门 已经发送邮件提醒了")))
            return


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
    stop_signal[0] = True
    # 立即释放所有按键
    mover._release_all_keys()


def on_stop_hotkey():
    """停止脚本的热键回调 - 立即响应，耗时操作放到线程"""
    global stop_be_pressed, stop_signal
    logger.warning("监听到停止热键，停止脚本...")
    stop_be_pressed = True  # 立即设置标志
    stop_signal[0] = True
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
    
    # 防抖动
    last_stop_time = 0
    last_pause_time = 0
    debounce_interval = 0.3
    
    while not stop_be_pressed and _hotkey_listener_running:
        current_time = time.time()
        
        # 检查停止键 (GetAsyncKeyState返回最高位为1表示按下)
        if stop_vk and user32.GetAsyncKeyState(stop_vk) & 0x8000:
            if current_time - last_stop_time >= debounce_interval:
                last_stop_time = current_time
                on_stop_hotkey()
        
        # 检查暂停键
        if pause_vk and user32.GetAsyncKeyState(pause_vk) & 0x8000:
            if current_time - last_pause_time >= debounce_interval:
                last_pause_time = current_time
                on_pause_hotkey()
        
        time.sleep(0.05)  # 50ms轮询间隔


def analyse_det_result(results, hero_height, img) -> DetResult:
    global show
    if results is not None and len(results):
        boss_xywh_list = []
        monster_xywh_list = []
        elite_monster_xywh_list = []

        loot_xywh_list = []
        gold_xywh_list = []
        door_xywh_list = []
        door_boss_xywh_list = []

        hero_conf = -1
        hero_xywh = None

        card_num = 0
        continue_exist = False
        shop_exist = False
        shop_mystery_exist = False
        menu_exist = False
        sss_exist = False

        forward_exists = False
        ball_xywh_list = []
        hole_xywh_list = []

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

            if names[cls] == "forward":
                forward_exists = True

            if names[cls] == "ball":
                xywh[1] = xyxy[3] + 50
                ball_xywh_list.append(xywh)

            if names[cls] == "hole":
                xywh[1] += door_h
                hole_xywh_list.append(xywh)

            # 在原图上画框
            if show and img is not None:
                label = '%s %.2f' % (names[int(cls)], conf)
                plot_one_box(box.xyxy[0], img, label=label, color=colors[int(cls)], line_thickness=2)

        res = DetResult()
        res.monster_xywh_list = monster_xywh_list
        res.elite_monster_xywh_list = elite_monster_xywh_list
        res.boss_xywh_list = boss_xywh_list
        res.loot_xywh_list = loot_xywh_list
        res.gold_xywh_list = gold_xywh_list
        res.door_xywh_list = door_xywh_list
        res.door_boss_xywh_list = door_boss_xywh_list

        res.hero_xywh = hero_xywh
        # res.hero_conf = hero_conf

        res.card_num = card_num
        res.continue_exist = continue_exist
        res.shop_exist = shop_exist
        res.shop_mystery_exist = shop_mystery_exist
        res.menu_exist = menu_exist
        res.sss_exist = sss_exist

        res.forward_exists = forward_exists
        res.ball_xywh_list = ball_xywh_list
        res.hole_xywh_list = hole_xywh_list

        # 给角色绘制定位圆点,方便查看
        if show:
            if res.hero_xywh:
                # 推理后的中心
                cv2.circle(img, (int(hero_xywh[0]), int(hero_xywh[1] - hero_height)), 1, color_red, 2)
                # 处理后的中心
                cv2.circle(img, (int(hero_xywh[0]), int(hero_xywh[1])), 1, color_green, 2)

            for a in (res.loot_xywh_list + res.gold_xywh_list):
                # 掉落物
                cv2.circle(img, (int(a[0]), int(a[1] - loot_h)), 1, color_red, 2)
                cv2.circle(img, (int(a[0]), int(a[1])), 1, color_green, 2)

            for a in res.ball_xywh_list:
                # 球
                cv2.circle(img, (int(a[0]), int(a[1] - a[3])), 1, color_red, 2)
                cv2.circle(img, (int(a[0]), int(a[1])), 1, color_green, 2)

            for a in res.monster_xywh_list:
                # 怪
                cv2.circle(img, (int(a[0]), int(a[1])), 1, color_green, 2)
                cv2.circle(img, (int(a[0]), int(a[1] - monster_h)), 1, color_red, 2)

            for a in res.boss_xywh_list:
                # boss
                cv2.circle(img, (int(a[0]), int(a[1])), 1, color_green, 2)
                cv2.circle(img, (int(a[0]), int(a[1] - boss_h)), 1, color_red, 2)

        return res


# <<<<<<<<<<<<<<<< 方法定义 <<<<<<<<<<<<<<<<


def main_script():
    global x, y, handle, show, stop_be_pressed
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


def _run_main_script():
    global x, y, handle, show, stop_be_pressed
    
    # 获取游戏窗口的位置，和大小
    handle = window_utils.get_window_handle(dnf.window_title)
    x, y, width, height = window_utils.get_window_rect(handle)
    logger.info("获取游戏窗口位置和大小...{},{},{},{}", x, y, width, height)
    window_utils.resize_window(handle)
    logger.warning("矫正窗口大小:1067*600")
    capturer = WindowCapture(handle)

    # 获取角色配置列表
    role_list = get_role_config_list(account_code)
    logger.info(f"读取角色配置列表(账号类型:{account_code})...")
    logger.info(f"共有{len(role_list)}个角色，将从第{first_role_no}个执行到第{last_role_no}个")

    pause_event.wait()
    # 检查每日弹窗
    close_new_day_dialog(handle, x, y, capturer)

    pause_event.wait()  # 暂停
    # 遍历角色, 循环刷图
    for i in range(len(role_list)):
        # 检查停止标志
        check_stop()
            
        pause_event.wait()  # 暂停

        role = role_list[i]
        role_no = i + 1  # 角色编号从1开始
        
        # 判断,从指定的角色开始,其余的跳过
        if first_role_no != -1 and role_no < first_role_no:
            logger.info(f'[跳过]-【{role_no}】[{role.name}]...')
            continue
        # 判断,到指定的角色结束
        if last_role_no != -1 and role_no > last_role_no:
            logger.info(f'[结束]-已到达最后角色【{last_role_no}】')
            break
        # 判断是否跳过指定角色
        if break_role and role_no in break_role_no:
            logger.info(f'[跳过指定角色]-【{role_no}】[{role.name}]...')
            continue
        logger.warning(f'第【{role_no}】个角色，【{role.name}】 开始了')
        oen_role_start_time = datetime.now()

        # 读取角色配置
        h_h = role.height  # 高度
        # 读取疲劳值配置
        if enable_uniform_pl:
            role.fatigue_reserved = uniform_default_fatigue_reserved
        skill_images = {}

        # 等待加载角色完成
        safe_sleep(4)

        # # 确保展示右下角的图标
        # show_right_bottom_icon(capturer.capture(), x, y)

        # 检查每日弹窗
        if datetime.now().hour == 0:
            close_new_day_dialog(handle, x, y, capturer)

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
        fatigue_cost = 8  # 一把消耗的疲劳值

        logger.info(f'{role.name},拥有疲劳值:{role.fatigue_all},预留疲劳值:{role.fatigue_reserved}')

        # 如果需要刷图,这选择副本,进入副本
        need_fight = current_fatigue - fatigue_cost >= role.fatigue_reserved if role.fatigue_reserved > 0 else current_fatigue > 0

        if need_fight:
            pause_event.wait()  # 暂停
            # 奶爸刷图,切换输出加点
            if '奶爸' in role.name:
                logger.info("是奶爸,准备切换锤子护石...")
                # crusader_to_battle(x, y)

            pause_event.wait()  # 暂停
            # 默认是站在赛丽亚房间

            # 获取技能栏截图
            skill_images = get_skill_initial_images(capturer.capture())

            # N 点第一个
            logger.info("传送到风暴门口,选地图...")
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

            goto_abyss(x, y)  # 去深渊

            pause_event.wait()  # 暂停

        # 刷图流程开始>>>>>>>>>>
        logger.info(f'第【{i + 1}】个角色【{role.name}】已经进入地图,刷图打怪循环开始...')

        # # 隐藏掉右下角的图标
        # if need_fight:
        #     hide_right_bottom_icon(capturer.capture(), x, y)

        # 一直循环
        pause_event.wait()  # 暂停

        # 记录一下刷图次数
        fight_count = 0

        # 角色刷完结束
        finished = False
        buff_finished = False

        # todo 循环进图开始>>>>>>>>>>>>>>>>>>>>>>>>
        while not finished and need_fight and not stop_be_pressed:  # 循环进图，再次挑战
            # 检查停止标志
            if stop_be_pressed:
                logger.warning("检测到停止信号，退出循环...")
                break
            
            # 重置超时检测标志，停止上一次的超时检测线程
            stop_signal[0] = False
            
            # 记录本次刷图开始时间
            one_game_start = time.time()
            # 启动异常检测线程
            threading.Thread(target=adjust_stutter_alarm, args=(one_game_start, role.name, role_no, fight_count + 1, handle), daemon=True).start()

            # 先要等待地图加载
            time.sleep(1)

            # 不管了,全部释放掉
            mover._release_all_keys()

            pause_event.wait()  # 暂停
            img0 = capturer.capture()

            # 检查是否成功进入地图
            enter_map_success = not detect_return_town_button_when_choose_map(img0)

            # 进不去
            if not enter_map_success:
                logger.warning(f'【{role.name}】，进不去地图,结束当前角色')
                time.sleep(0.2)
                # esc 关闭地图选择界面
                kbu.do_press(Key.esc)
                time.sleep(0.2)
                break

            pause_event.wait()  # 暂停

            fight_count += 1
            logger.info(f'{role.name} 刷图,第 {fight_count} 次，开始...')
            mu.do_move_to(x + width / 4, y + height / 4)  # 重置鼠标位置

            # 记录疲劳值
            # current_fatigue_ocr = do_ocr_fatigue_retry(handle, x, y, reader, 5)  # 识别疲劳值
            current_fatigue_ocr = do_recognize_fatigue(img0)  # 识别疲劳值
            logger.info(f'当前还有疲劳值(识别): {current_fatigue_ocr}')

            global continue_pressed
            if continue_pressed:
                continue_pressed = False

            pause_event.wait()  # 暂停

            if not buff_finished:
                # 上Buff
                logger.info(f'准备上Buff..')
                if role.buff_effective:
                    for buff in role.buffs:
                        kbu.do_buff(buff)
                else:
                    logger.info(f'不需要上Buff..')
                buff_finished = True

            logger.info(f'准备打怪..')

            # todo 循环打怪过图，过房间 循环开始////////////////////////////////

            collect_loot_pressed = False  # 按过移动物品了
            collect_loot_pressed_time = 0
            ball_appeared = False  # 遇到球了
            fight_victory = False  # 已经结算了
            door_absence_time = 0  # 什么也没识别到的时间(没识别到门)
            hole_appeared = False
            hole_try_count = 0  # hole进入尝试次数
            boss_appeared = False
            die_time = 0
            delay_break = 0

            # frame = 0
            while True:  # 循环打怪过图，过房间
                # 检查停止标志
                if stop_be_pressed:
                    logger.warning("检测到停止信号，退出打怪循环...")
                    break
                
                pause_event.wait()  # 暂停

                # 截图
                img0 = capturer.capture()
                # 识别
                cv_det_task = None
                if boss_appeared or hole_appeared or ball_appeared:
                    cv_det_task = img_executor.submit(object_detection_cv, img0)
                img4show = img0.copy()
                # frame = frame + 1
                # print('截图ing，，，', frame)
                # 执行推理（使用延迟加载的模型）
                _model, _device = get_model()
                results = _model.predict(
                    source=img0,
                    device=_device,
                    imgsz=640,
                    conf=0.7,
                    iou=0.2,
                    verbose=False
                )

                if results is None or len(results) == 0 or len(results[0].boxes) == 0:
                    # logger.info('模型没有识别到物体')
                    continue

                # # todo
                # if show:
                #     annotated_frame = results[0].plot()
                #     # 将结果放入队列，供展示线程使用
                #     result_queue.put(annotated_frame)

                # print('results[0].boxes', results[0].boxes)
                # 分析推理结果,组装类别数据
                det = analyse_det_result(results, h_h, img4show)
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

                card_num = det.card_num
                continue_exist = det.continue_exist
                shop_exist = det.shop_exist
                shop_mystery_exist = det.shop_mystery_exist
                menu_exist = det.menu_exist
                sss_exist = det.sss_exist

                forward_exists = det.forward_exists
                ball_xywh_list = det.ball_xywh_list
                hole_xywh_list = det.hole_xywh_list

                aolakou = False
                if continue_exist or shop_exist:
                    logger.debug(f"出现商店{shop_exist}，再次挑战了{continue_exist}")
                    fight_victory = True
                    aolakou = detect_aolakou(results[0].orig_img)

                if ball_xywh_list:
                    logger.info(f"发现球了")
                    ball_appeared = True
                if hole_xywh_list:
                    logger.info(f"出现大坑了")
                    hole_appeared = True
                if boss_xywh_list:
                    if not boss_appeared:
                        boss_appeared = True
                    logger.info(f"出现boss了")
                    
                if cv_det_task:
                    cv_det = cv_det_task.result()
                    if cv_det and cv_det["death"]:
                        logger.warning(f"角色死了")
                        if time.time() - die_time > 11:
                            die_time = time.time()
                            logger.warning(f"死亡提醒!!")

                            # 声音提醒
                            tool_executor.submit(lambda: (
                                winsound.Beep(800, 300), time.sleep(0.05),
                                winsound.Beep(800, 300), time.sleep(0.05),
                                winsound.Beep(800, 300), time.sleep(0.05),
                                winsound.Beep(800, 1200)
                            ))

                            # 邮件提醒
                            email_subject = f"深渊 {role.name}阵亡通知书"
                            email_content = f"鏖战深渊，角色【{role.name}】不幸阵亡，及时查看处理。"
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
                        kbu.do_press('x')
                        time.sleep(0.1)

                if hero_xywh:
                    pass
                else:  # todo 没有识别到角色
                    if not fight_victory or (monster_xywh_list or boss_xywh_list or ball_xywh_list):
                        random_direct = random.choice(['LEFT', 'DOWN', 'LEFT_DOWN'])
                        logger.warning('未检测到角色,随机跑个方向看看{}', random_direct)
                        mover.move(target_direction=random_direct)
                    else:
                        logger.warning('未检测到角色,已经结算了')
                        if not collect_loot_pressed and (sss_exist or continue_exist or shop_exist or shop_mystery_exist):
                            mover.move(target_direction="LEFT")
                            # time.sleep(0.1)
                    if not aolakou:
                        continue

                # ############################### 判断-准备打怪 ######################################
                wait_for_attack = ((hero_xywh and (monster_xywh_list or boss_xywh_list or ball_xywh_list) and not fight_victory)
                                   or (hero_xywh and not continue_exist and not forward_exists and (monster_xywh_list or boss_xywh_list or ball_xywh_list))
                                   )
                monster_box = None
                monster_in_range = False
                role_attack_center = None
                best_attack_point = None
                if wait_for_attack:
                    role_attack_center = (hero_xywh[0], hero_xywh[1])
                    if mover.get_current_direction() is None or "RIGHT" in mover.get_current_direction():
                        role_attack_center = (hero_xywh[0] + role.attack_center_x, hero_xywh[1])
                    else:
                        role_attack_center = (hero_xywh[0] - role.attack_center_x, hero_xywh[1])

                    # 如果有boss，优先打boss
                    if boss_xywh_list is not None and len(boss_xywh_list) > 0:
                        monster_box = boss_xywh_list[0]
                    else:
                        monster_box = find_densest_monster_cluster(monster_xywh_list + ball_xywh_list, role_attack_center)

                    if show:
                        # 怪(堆中心) 蓝色
                        cv2.circle(img4show, (int(monster_box[0]), int(monster_box[1])), 5, color_blue, 4)

                    # 怪处于攻击范围内
                    if role.attack_center_x:
                        if mover.get_current_direction() is None or "RIGHT" in mover.get_current_direction():
                            monster_in_range = (monster_box[0] > role_attack_center[0]
                                                and abs(role_attack_center[0] - monster_box[0]) < attack_x
                                                and abs(role_attack_center[1] - monster_box[1]) < attack_y
                                                ) or (
                                                       monster_box[0] < role_attack_center[0]
                                                       and abs(role_attack_center[0] - monster_box[0]) < (role.attack_center_x * 0.65)
                                                       and abs(role_attack_center[1] - monster_box[1]) < attack_y
                                               )
                        else:
                            monster_in_range = (monster_box[0] < role_attack_center[0]
                                                and abs(role_attack_center[0] - monster_box[0]) < attack_x
                                                and abs(role_attack_center[1] - monster_box[1]) < attack_y
                                                ) or (
                                                   (monster_box[0] > role_attack_center[0]
                                                    and abs(role_attack_center[0] - monster_box[0]) < (role.attack_center_x * 0.65)
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

                # ############################ 判断-准备进入下一个房间 ####################################
                wait_for_next_room = (((forward_exists or hole_xywh_list)
                                       and not ball_xywh_list and not monster_xywh_list and not boss_xywh_list
                                       and not fight_victory)
                                      or (not continue_exist and not hole_xywh_list and not ball_xywh_list and not monster_xywh_list and not boss_xywh_list))
                next_room_direction = 'RIGHT'

                # ####################### 判断-准备拾取材料 #############################################
                wait_for_pickup = hero_xywh and (loot_xywh_list or gold_xywh_list) and (ball_appeared or fight_victory)  # fight_victory
                material_box = None
                loot_in_range = False
                material_min_distance = float("inf")
                material_is_gold = False
                if wait_for_pickup:
                    # 距离最近的掉落物
                    material_box, material_min_distance = get_closest_obj(itertools.chain(loot_xywh_list, gold_xywh_list), det.hero_xywh)
                    if material_box in gold_xywh_list:
                        material_is_gold = True
                    if show and material_box:
                        # 给目标掉落物画一个点
                        cv2.circle(img4show, (int(material_box[0]), int(material_box[1])), 2, color_blue, 3)
                    # 材料处于拾取范围
                    loot_in_range = abs(material_box[1] - hero_xywh[1]) < pick_up_y and abs(material_box[0] - hero_xywh[0]) < pick_up_x
                    if show and loot_in_range:
                        # 材料处于拾取范围,给角色一个标记
                        cv2.circle(img4show, (int(hero_xywh[0]), int(hero_xywh[1])), 10, color_yellow, 2)

                # 截图展示前的处理完毕,放入队列由独立线程显示
                if show:
                    # 清空旧帧，只保留最新的
                    while not result_queue.empty():
                        try:
                            result_queue.get_nowait()
                        except queue.Empty:
                            break
                    result_queue.put(img4show.copy())
                # ######################### 判断完毕,进行逻辑处理 ########################################################

                # 逻辑处理-找门进入下个房间>>>>>>>>>>>>>>>>>>>>>>>>>>
                if wait_for_next_room:

                    # 要进洞
                    if hole_xywh_list:
                        door_box = hole_xywh_list[0]
                        hole_try_count += 1
                        
                        # 多次尝试进入hole失败，强制向上移动
                        if hole_try_count > 5:
                            logger.warning(f"hole进入尝试{hole_try_count}次，强制向上移动")
                            mover._release_all_keys()
                            kbu.do_press_with_time(Key.up, 500, 50)
                            hole_try_count = 0
                            continue
                        
                        door_box[1] += random.choice([0, 10, -10])  # 随机修改一下y,有时候一直进不去

                        # 已经确定目标门,移动到目标位置
                        # 目标在角色的右上方
                        if door_box[1] - hero_xywh[1] < 0 and door_box[0] - hero_xywh[0] > 0:
                            # y方向上处于范围内,只需要x方向移动
                            if abs(door_box[1] - hero_xywh[1]) < door_hit_y:
                                # print("y方向上处于范围内,只需要x方向移动")
                                mover.move(target_direction="RIGHT")
                            # x轴上的距离比较远,斜方向移动
                            elif abs(hero_xywh[1] - door_box[1]) < abs(door_box[0] - hero_xywh[0]):
                                # print("x轴上的距离比较远,斜方向移动")
                                mover.move(target_direction="RIGHT_UP")
                            # y轴上的距离也比较远,只进行y轴上的移动
                            elif abs(hero_xywh[1] - door_box[1]) >= abs(door_box[0] - hero_xywh[0]):
                                mover.move(target_direction="UP")
                        # 目标在角色的左上方
                        elif door_box[1] - hero_xywh[1] < 0 and door_box[0] - hero_xywh[0] < 0:
                            # y方向上处于范围内,只需要x方向移动
                            if abs(door_box[1] - hero_xywh[1]) < door_hit_y:
                                mover.move(target_direction="LEFT")
                            # x轴上的距离比较远,斜方向移动
                            elif abs(hero_xywh[1] - door_box[1]) < abs(hero_xywh[0] - door_box[0]):
                                mover.move(target_direction="LEFT_UP")
                            # y轴上的距离也比较远,只进行y轴上的移动
                            elif abs(hero_xywh[1] - door_box[1]) >= abs(hero_xywh[0] - door_box[0]):
                                mover.move(target_direction="UP")
                        # 目标在角色的左下方
                        elif door_box[1] - hero_xywh[1] > 0 and door_box[0] - hero_xywh[0] < 0:
                            # y方向上处于范围内,只需要x方向移动
                            if abs(door_box[1] - hero_xywh[1]) < door_hit_y:
                                mover.move(target_direction="LEFT")
                            # x轴上的距离比较远,斜方向移动
                            elif abs(door_box[1] - hero_xywh[1]) < abs(hero_xywh[0] - door_box[0]):
                                mover.move(target_direction="LEFT_DOWN")
                            # y轴上的距离也比较远,只进行y轴上的移动
                            elif abs(door_box[1] - hero_xywh[1]) >= abs(hero_xywh[0] - door_box[0]):
                                mover.move(target_direction="DOWN")
                        # 目标在角色的右下方
                        elif door_box[1] - hero_xywh[1] > 0 and door_box[0] - hero_xywh[0] > 0:
                            # y方向上处于范围内,只需要x方向移动
                            if abs(door_box[1] - hero_xywh[1]) < door_hit_y:
                                mover.move(target_direction="RIGHT")
                            # x轴上的距离比较远,斜方向移动
                            elif abs(door_box[1] - hero_xywh[1]) < abs(door_box[0] - hero_xywh[0]):
                                mover.move(target_direction="RIGHT_DOWN")
                            # y轴上的距离也比较远,只进行y轴上的移动
                            elif abs(door_box[1] - hero_xywh[1]) >= abs(door_box[0] - hero_xywh[0]):
                                mover.move(target_direction="DOWN")
                        continue

                    else:  # 都是往右走
                        pause_event.wait()  # 暂停
                        mover.move(target_direction="RIGHT")
                        continue
                # 逻辑处理-找门进入下个房间<<<<<<<<<<<<<<<<<<<<<<<<<

                # 逻辑处理-有怪要打怪>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                if wait_for_attack:  # todo 要打球
                    # 处于攻击范围
                    if monster_in_range:

                        if mover.get_current_direction() is not None:
                            # 不管了,全部释放掉
                            mover._release_all_keys()

                        # 调整方向,面对怪
                        if hero_xywh[0] - monster_box[0] > 100:
                            logger.debug('面对怪,朝左，再放技能')
                            kbu.do_press(Key.left)
                        elif monster_box[0] > hero_xywh[0] > 100:
                            logger.debug('面对怪,朝右，再放技能')
                            kbu.do_press(Key.right)
                        time.sleep(0.02)

                        skill_name = None
                        if role.powerful_skills and boss_xywh_list:
                            # skill_name = skill_util.suggest_skill_powerful(role, img0)
                            skill_name = skill_util.get_available_skill_from_list_by_match(skills=role.powerful_skills, img0=img0, skill_images=skill_images)
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
                    # 目标在角色右上方
                    if monster_box[1] - role_attack_center[1] < 0 and monster_box[0] - role_attack_center[0] > 0:
                        # y方向已经处于攻击范围,只需要x方向移动
                        if abs(monster_box[1] - role_attack_center[1]) < attack_y:
                            mover.move(target_direction="RIGHT")
                        # x轴上的距离比较远,斜方向移动
                        elif abs(role_attack_center[1] - monster_box[1]) < abs(monster_box[0] - role_attack_center[0]):
                            mover.move(target_direction="RIGHT_UP")
                        # y轴上的距离也比较远,只进行y轴上的移动
                        elif abs(role_attack_center[1] - monster_box[1]) >= abs(monster_box[0] - role_attack_center[0]):
                            mover.move(target_direction="UP")

                    # 目标在角色左上方
                    elif monster_box[1] - role_attack_center[1] < 0 and monster_box[0] - role_attack_center[0] < 0:
                        # y方向已经处于攻击范围,只需要x方向移动
                        if abs(monster_box[1] - role_attack_center[1]) < attack_y:
                            mover.move(target_direction="LEFT")
                        # x轴上的距离比较远,斜方向移动
                        elif role_attack_center[1] - monster_box[1] < role_attack_center[0] - monster_box[0]:
                            mover.move(target_direction="LEFT_UP")
                        # y轴上的距离也比较远,只进行y轴上的移动
                        elif role_attack_center[1] - monster_box[1] >= role_attack_center[0] - monster_box[0]:
                            mover.move(target_direction="UP")

                    # 目标在角色左下方
                    elif monster_box[1] - role_attack_center[1] > 0 and monster_box[0] - role_attack_center[0] < 0:
                        # y方向已经处于攻击范围,只需要x方向移动
                        if abs(monster_box[1] - role_attack_center[1]) < attack_y:
                            mover.move(target_direction="LEFT")
                        # x轴上的距离比较远,斜方向移动
                        elif monster_box[1] - role_attack_center[1] < role_attack_center[0] - monster_box[0]:
                            mover.move(target_direction="LEFT_DOWN")
                        # y轴上的距离也比较远,只进行y轴上的移动
                        elif monster_box[1] - role_attack_center[1] >= role_attack_center[0] - monster_box[0]:
                            mover.move(target_direction="DOWN")

                    # 目标在角色右下方
                    elif monster_box[1] - role_attack_center[1] > 0 and monster_box[0] - role_attack_center[0] > 0:
                        # y方向已经处于攻击范围,只需要x方向移动
                        if abs(monster_box[1] - role_attack_center[1]) < attack_y:
                            mover.move(target_direction="RIGHT")
                        # x轴上的距离比较远,斜方向移动
                        elif monster_box[1] - role_attack_center[1] < monster_box[0] - role_attack_center[0]:
                            mover.move(target_direction="RIGHT_DOWN")
                        # y轴上的距离也比较远,只进行y轴上的移动
                        elif monster_box[1] - role_attack_center[1] >= monster_box[0] - role_attack_center[0]:
                            mover.move(target_direction="DOWN")

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
                if wait_for_pickup:  # todo 前边都不捡
                    if not collect_loot_pressed:
                        if hero_xywh[0] > img0.shape[1] * 4 // 5:
                            logger.debug('太靠右了，先调整一下')
                            mover.move(target_direction="LEFT")
                            time.sleep(0.3)
                        logger.warning("预先移动物品到脚下")
                        # 不管了,全部释放掉
                        mover._release_all_keys()

                        time.sleep(0.3)
                        logger.warning("预先移动物品到脚下")
                        kbu.do_press(dnf.Key_collect_loot)
                        collect_loot_pressed = True
                        collect_loot_pressed_time = time.time()
                        time.sleep(0.1)
                        kbu.do_press(Key.left)
                        time.sleep(0.1)
                        kbu.do_press_with_time('x', 3000 if hole_appeared else 3000, 50),
                        logger.warning("预先长按x 按完x了")

                        continue
                    elif collect_loot_pressed and time.time() - collect_loot_pressed_time < 5:
                        tt = time.time()
                        if 0.1 < tt - int(tt) < 0.2:  # 0.6 < tt - int(tt) < 0.75:
                            logger.info(f"已经预先按下移动物品了，5s内忽略拾取...{int(5 - (time.time() - collect_loot_pressed_time))}")
                        continue
                    elif collect_loot_pressed and time.time() - collect_loot_pressed_time >= 5:
                        # 5秒后如果还有掉落物，继续按x捡
                        if loot_xywh_list or gold_xywh_list:
                            logger.warning(f"5秒后仍有掉落物，继续按x捡取")
                            mover._release_all_keys()
                            time.sleep(0.1)
                            kbu.do_press_with_time('x', 2000, 50)
                            collect_loot_pressed_time = time.time()  # 重置时间
                            continue
                        # 掉落物在范围内,直接拾取
                        if loot_in_range:
                            # 不管了,全部释放掉
                            mover._release_all_keys()
                            time.sleep(0.1)
                            kbu.do_press("x")
                            logger.info("捡东西按完x了")
                            continue

                    # 掉落物不在范围内,需要移动
                    byWalk = False
                    if material_min_distance < 200:
                        byWalk = True
                    slow_pickup = not material_is_gold or material_min_distance < 100

                    pause_event.wait()  # 暂停
                    move_mode = 'walking' if byWalk else 'running'
                    # todo 抽取方法, 根据距离判断做直线还是斜线, 根据距离判断走还是跑
                    # 目标在角色的上右方
                    if material_box[1] - hero_xywh[1] < 0 and material_box[0] - hero_xywh[0] > 0:
                        # y方向已经处于攻击范围, 只需要x方向移动
                        if abs(material_box[1] - hero_xywh[1]) < pick_up_y:
                            mover.move_stop_immediately(target_direction="RIGHT", move_mode=move_mode, stop=slow_pickup)
                        # x轴上的距离比较远,斜方向移动
                        elif hero_xywh[1] - material_box[1] < material_box[0] - hero_xywh[0]:
                            mover.move_stop_immediately(target_direction="RIGHT_UP", move_mode=move_mode, stop=slow_pickup)
                        # y轴上的距离也比较远,只进行y轴上的移动
                        elif hero_xywh[1] - material_box[1] >= material_box[0] - hero_xywh[0]:
                            mover.move_stop_immediately(target_direction="UP", move_mode=move_mode, stop=slow_pickup)
                            # break
                    # 目标在角色的左上方
                    elif material_box[1] - hero_xywh[1] < 0 and material_box[0] - hero_xywh[0] < 0:
                        # y方向已经处于攻击范围, 只需要x方向移动
                        if abs(material_box[1] - hero_xywh[1]) < pick_up_y:
                            mover.move_stop_immediately(target_direction="LEFT", move_mode=move_mode, stop=slow_pickup)
                        # x轴上的距离比较远,斜方向移动
                        elif hero_xywh[1] - material_box[1] < hero_xywh[0] - material_box[0]:
                            mover.move_stop_immediately(target_direction="LEFT_UP", move_mode=move_mode, stop=slow_pickup)
                        # y轴上的距离也比较远,只进行y轴上的移动
                        elif hero_xywh[1] - material_box[1] >= hero_xywh[0] - material_box[0]:
                            mover.move_stop_immediately(target_direction="UP", move_mode=move_mode, stop=slow_pickup)
                            # break
                    # 目标在角色的左下方
                    elif material_box[1] - hero_xywh[1] > 0 and material_box[0] - hero_xywh[0] < 0:
                        # y方向已经处于攻击范围, 只需要x方向移动
                        if abs(material_box[1] - hero_xywh[1]) < pick_up_y:
                            mover.move_stop_immediately(target_direction="LEFT", move_mode=move_mode, stop=slow_pickup)
                        # x轴上的距离比较远,斜方向移动
                        elif material_box[1] - hero_xywh[1] < hero_xywh[0] - material_box[0]:
                            mover.move_stop_immediately(target_direction="LEFT_DOWN", move_mode=move_mode, stop=slow_pickup)
                        # y轴上的距离也比较远,只进行y轴上的移动
                        elif material_box[1] - hero_xywh[1] >= hero_xywh[0] - material_box[0]:
                            mover.move_stop_immediately(target_direction="DOWN", move_mode=move_mode, stop=slow_pickup)
                    # 目标在角色的右下方
                    elif material_box[1] - hero_xywh[1] > 0 and material_box[0] - hero_xywh[0] > 0:
                        # y方向已经处于攻击范围, 只需要x方向移动
                        if abs(material_box[1] - hero_xywh[1]) < pick_up_y:
                            mover.move_stop_immediately(target_direction="RIGHT", move_mode=move_mode, stop=slow_pickup)
                        # x轴上的距离比较远,斜方向移动
                        elif material_box[1] - hero_xywh[1] < material_box[0] - hero_xywh[0]:
                            mover.move_stop_immediately(target_direction="RIGHT_DOWN", move_mode=move_mode, stop=slow_pickup)
                        # y轴上的距离也比较远,只进行y轴上的移动
                        elif material_box[1] - hero_xywh[1] >= material_box[0] - hero_xywh[0]:
                            mover.move_stop_immediately(target_direction="DOWN", move_mode=move_mode, stop=slow_pickup)

                    continue
                # 逻辑处理-捡材料<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

                # 逻辑处理-出现再次挑战>>>>>>>>>>>>>>>>>>>>>>>>>>>
                if continue_exist:
                    # 不管了,全部释放掉
                    mover._release_all_keys()

                    pause_event.wait()
                    # todo 前多少角色买奥拉扣
                    if aolakou and role.no <= 0:
                        mu.do_move_to(x + 123, y + 209)
                        time.sleep(0.2)
                        mu.do_click(Button.left)
                        time.sleep(0.2)
                        mu.do_click(Button.left)
                        time.sleep(0.2)

                    # 神秘商店
                    if shop_mystery_exist:
                        # cv2.imwrite(f'./shop_imgs/mystery_Shop_{datetime.fromtimestamp(time.time()).strftime("%Y%m%d_%H%M%S")}.jpg', img0)
                        time.sleep(0.5)
                        process_mystery_shop(capturer.capture(), x, y, buy_tank_type, buy_bell_ticket, buy_shanshanming, buy_catalyst)  # 重新截图，防止前面截的帧有干扰不清晰

                        pause_event.wait()
                        kbu.do_press(Key.esc)
                        logger.warning("神秘商店开着,需要esc关闭")
                        time.sleep(0.1)
                        continue

                    # 如果商店开着,需要esc关闭
                    if shop_exist or aolakou:
                        kbu.do_press(Key.esc)
                        logger.warning("普通商店开着,需要esc关闭")
                        time.sleep(0.1)
                        continue

                    # 不存在掉落物了,就再次挑战
                    if not loot_xywh_list and not gold_xywh_list:
                        logger.warning("出现再次挑战,并且没有掉落物了,终止")
                        # time.sleep(3)  # 等待加载地图
                        if delay_break < 3:
                            # 延迟break，终止掉当前刷一次图的循环，多花0.3秒再次进行检测，处理商店和掉落物
                            delay_break = delay_break + 1
                            time.sleep(0.1)
                            continue

                        # 停止超时检测线程
                        stop_signal[0] = True
                        break  # 终止掉当前刷一次图的循环

                    # 聚集物品,按x
                    if (loot_xywh_list or gold_xywh_list) and not collect_loot_pressed:
                        if not collect_loot_pressed:
                            if hero_xywh[0] > img0.shape[1] * 4 // 5:
                                logger.debug('太靠右了，先调整一下')
                                mover.move(target_direction="LEFT")
                                time.sleep(0.3)

                            time.sleep(0.3)
                            logger.warning("中间移动物品到脚下")
                            kbu.do_press(dnf.Key_collect_loot)
                            collect_loot_pressed = True
                            collect_loot_pressed_time = time.time()
                            time.sleep(0.1)
                            kbu.do_press(Key.left)
                            time.sleep(0.1)
                            kbu.do_press_with_time('x', 5000, 50)
                            logger.warning("中间长按x 按完x了")
                        continue
                    continue
                # 逻辑处理-出现再次挑战<<<<<<<<<<<<<<<<<<<<<<<<<<<

                # 逻辑处理-什么都没有>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                if (not gold_xywh_list and not loot_xywh_list and not monster_xywh_list and not ball_xywh_list and not boss_xywh_list and not forward_exists and not continue_exist) and not ball_appeared:  # todo boss
                    pause_event.wait()  # 暂停
                    # 情况1:漏怪了,并且视野内看不到怪了,随机久了肯定能看到怪
                    if not door_absence_time:
                        door_absence_time = time.time()
                    if hero_xywh is not None:
                        logger.warning("除了角色什么也没识别到")
                        direct = "RIGHT"

                        if door_absence_time and time.time() - door_absence_time > 60:
                            logger.warning('什么都没检测到(没有门)已经3分钟了,随机方向')
                            direct = random.choice(random.choice([kbu.single_direct, kbu.double_direct]))

                        logger.warning(f"尝试方向--->{direct}")
                        mover.move(target_direction=direct)

                        pass
                    else:
                        random_direct = random.choice(['DOWN', "LEFT"])
                        logger.warning('角色也没识别到,什么都没识别到,随机跑个方向看看-->{}', random_direct)
                        mover.move(target_direction=random_direct)
                    continue
                # 逻辑处理-什么都没有<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
            # todo 循环打怪过图 循环结束////////////////////////////////
            logger.warning("循环打怪过图 循环结束////////////////////////////////")

            pause_event.wait()  # 暂停
            if not collect_loot_pressed:
                # 向左，防止太靠右
                mover.move(target_direction="LEFT")
                time.sleep(0.3)

                logger.warning("最后移动物品到脚下")
                mover._release_all_keys()
                time.sleep(0.2)
                kbu.do_press(dnf.Key_collect_loot)
                time.sleep(0.1)
                kbu.do_press(Key.left)
                time.sleep(0.1)
                kbu.do_press_with_time('x', 5000 if hole_appeared else 2000, 50),
                logger.warning("最后长按x 按完x了")

            pause_event.wait()  # 暂停
            # 疲劳值判断
            # current_fatigue = do_ocr_fatigue_retry(handle, x, y, reader, 5)
            current_fatigue = do_recognize_fatigue(img0)
            if role.fatigue_reserved > 0 and (current_fatigue - fatigue_cost) < role.fatigue_reserved:
                # 再打一把就疲劳值就不够预留的了
                logger.info(f'再打一把就疲劳值就不够预留的{role.fatigue_reserved}了')
                logger.info(f'刷完{fight_count}次了，结束...')
                # 返回城镇
                kbu.do_press(dnf.key_return_to_town)
                safe_sleep(5)
                finished = True
                # break

            if current_fatigue <= 0:
                # 再打一把就疲劳值就不够预留的了
                logger.info(f'没有疲劳值了')
                logger.info(f'刷完{fight_count}次了，结束...')
                # 返回城镇
                kbu.do_press(dnf.key_return_to_town)
                safe_sleep(5)
                finished = True
                # break

            pause_event.wait()  # 暂停
            # 识别"再次挑战"按钮是否存在,是否可以点击
            btn_exist, text_exist, btn_clickable = detect_try_again_button(capturer.capture())
            logger.debug(f"识别再次挑战，{btn_exist}，{text_exist}，{btn_clickable}")
            # 没的刷了,不能再次挑战了
            if btn_exist and not btn_clickable:
                pause_event.wait()  # 暂停
                logger.info(f'刷了{fight_count}次了,再次挑战禁用状态,不能再次挑战了...')
                # 返回城镇
                kbu.do_press(dnf.key_return_to_town)
                safe_sleep(5)
                finished = True
            else:
                # logger.warning("即将按下再次挑战")
                # time.sleep(1)
                # logger.warning("即将按下再次挑战")
                # time.sleep(1)
                # logger.warning("即将按下再次挑战")
                # time.sleep(1)
                # logger.warning("即将按下再次挑战")
                # time.sleep(1)
                # logger.warning("即将按下再次挑战")
                # time.sleep(1)
                # logger.warning("即将按下再次挑战")

                kbu.do_press(dnf.key_try_again)
                logger.warning("按下再次挑战了")

        # todo 循环进图结束<<<<<<<<<<<<<<<<<<<<<<<

        time_diff = datetime.now() - oen_role_start_time
        logger.warning(f'第【{i + 1}】个角色【{role.name}】刷图打怪循环结束...总计耗时: {(time_diff.total_seconds() / 60):.1f} 分钟')
        if exception_mail_notify_timer:
            exception_mail_notify_timer.cancel()
        # 刷图流程结束<<<<<<<<<<
        # # 展示掉右下角的图标
        # show_right_bottom_icon(capturer.capture(), x, y)

        pause_event.wait()  # 暂停
        # 如果刷图了,则完成每日任务,整理背包
        if fight_count > 0:
            logger.info('刷了图之后,进行整理....')
            # 检查每日弹窗
            if datetime.now().hour == 0:
                close_new_day_dialog(handle, x, y, capturer)

            pause_event.wait()  # 暂停
            # 瞬移到赛丽亚房间
            teleport_to_sailiya(x, y)

            pause_event.wait()  # 暂停
            # # 完成每日任务
            # finish_daily_challenge(x, y)

            pause_event.wait()  # 暂停
            # 收邮件
            receive_mail(capturer.capture(), x, y)
            time.sleep(0.5)
            # 转移材料到账号金库
            transfer_materials_to_account_vault(x, y)

        pause_event.wait()  # 暂停
        # 准备重新选择角色
        if i < last_role_no - 1:
            logger.warning("准备重新选择角色")
            # esc打开菜单
            time.sleep(0.5)
            # kbu.do_press(Key.esc)
            mu.do_smooth_move_to(x + 832, y + 576)  # 通过点击菜单按钮打开菜单
            time.sleep(0.2)
            mu.do_click(Button.left)
            time.sleep(0.5)

            pause_event.wait()  # 暂停
            # 鼠标移动到选择角色，点击 偏移量（1038,914）
            img_menu = capturer.capture()
            template_choose_role = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/choose_role.png'), cv2.IMREAD_GRAYSCALE)
            match_and_click(img_menu, x, y, template_choose_role, (506, 504))
            # 等待加载角色选择页面
            time.sleep(2)

            # 默认停留在刚才的角色上，直接按一次右键，空格
            kbu.do_press(Key.right)
            time.sleep(0.2)
            kbu.do_press(Key.space)
            time.sleep(0.2)
        else:
            logger.warning("已经刷完最后一个角色了，结束脚本")
            # 使用账号显示名称，如果没有则使用默认名称
            display_name = account_name if account_name else '未知账号'
            email_subject = f"深渊 任务执行结束"
            email_content = f"{display_name} {email_subject}"
            mail_receiver = mail_config.get("receiver")
            if mail_receiver:
                tool_executor.submit(lambda: (
                    mail_sender.send_email(email_subject, email_content, mail_receiver),
                    logger.info(f"{display_name}任务执行结束")
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

    end_time = datetime.now()
    logger.info(f'脚本开始: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
    logger.info(f'脚本结束: {end_time.strftime("%Y-%m-%d %H:%M:%S")}')
    time_delta = end_time - start_time
    logger.info(f'总计耗时: {(time_delta.total_seconds() / 60):.1f} 分钟')

    # 脚本正常执行完,不是被组合键中断的,并且配置了退出游戏
    if not stop_be_pressed and quit_game_after_finish:
        logger.info("正在退出游戏...")
        clik_to_quit_game(handle, x, y)
        time.sleep(5)

    logger.info("python主线程已停止.....")

    if not stop_be_pressed and quit_game_after_finish and shutdown_pc_after_finish:
        logger.info("一分钟之后关机...")
        # os.system("shutdown /r /t 60")  # 60后秒重启
        os.system("shutdown /s /t 60")  # 60后秒关机
