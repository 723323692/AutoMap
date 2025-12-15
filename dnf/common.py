# -*- coding:utf-8 -*-
"""
DNF脚本公共模块 - 包含abyss和stronger共用的代码
"""

__author__ = "723323692"
__version__ = '1.0'

import queue
import random
import threading
import time
from typing import List, Tuple, Optional, Any

import cv2
import numpy as np
import winsound
from pynput import keyboard
from pynput.mouse import Button

import config as config_
import dnf.dnf_config as dnf
from utils import mouse_utils as mu
from utils import window_utils as window_utils
from utils.keyboard_move_controller import MovementController
from utils.utilities import plot_one_box

# 颜色常量
COLOR_RED = (0, 0, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (255, 0, 0)
COLOR_YELLOW = (0, 255, 255)
COLOR_PURPLE = (255, 0, 255)

# 检测参数常量
BOSS_HEIGHT = 120
MONSTER_HEIGHT = 57
ELITE_MONSTER_HEIGHT = 100
DOOR_HEIGHT = 32
LOOT_HEIGHT = 0


class KeyboardController:
    """键盘监听控制器"""
    
    def __init__(self, mover: MovementController, logger):
        self.logger = logger
        self.mover = mover
        self.pause_event = threading.Event()
        self.pause_event.set()  # 初始设置为未暂停状态
        self.current_keys_control = set()
        self.stop_be_pressed = False
        self.continue_pressed = False
        self.handle = -1
        self.x = 0
        self.y = 0
    
    def set_window_info(self, handle: int, x: int, y: int):
        """设置窗口信息"""
        self.handle = handle
        self.x = x
        self.y = y
    
    def on_press(self, key) -> Optional[bool]:
        """按键按下回调"""
        if key in dnf.key_stop_script or key in dnf.key_pause_script:
            self.current_keys_control.add(key)
            
            if all(k in self.current_keys_control for k in dnf.key_stop_script):
                formatted_keys = ', '.join(item.name for item in dnf.key_stop_script)
                self.logger.warning(f"监听到组合键 [{formatted_keys}]，停止脚本...")
                threading.Thread(
                    target=lambda: winsound.PlaySound(config_.sound2, winsound.SND_FILENAME)
                ).start()
                self.stop_be_pressed = True
                return False  # 停止监听

            if all(k in self.current_keys_control for k in dnf.key_pause_script):
                formatted_keys = ', '.join(item.name for item in dnf.key_pause_script)
                self.logger.warning(f"监听到组合键 [{formatted_keys}]，暂停or继续?")
                threading.Thread(
                    target=lambda: winsound.PlaySound(config_.sound3, winsound.SND_FILENAME)
                ).start()
                
                if self.pause_event.is_set():
                    self.logger.warning(f"按下 [{formatted_keys}]键，暂停运行...")
                    self.pause_event.clear()
                    self.mover._release_all_keys()
                    time.sleep(0.2)
                    self.mover._release_all_keys()
                else:
                    self.logger.warning(f"按下 [{formatted_keys}] 键，唤醒运行...")
                    self.x, self.y, _, _ = window_utils.get_window_rect(self.handle)
                    mu.do_move_to(self.x + 250, self.y + 150)
                    time.sleep(0.1)
                    mu.do_click(Button.left)
                    self.continue_pressed = True
                    self.pause_event.set()
                time.sleep(0.5)
        return None

    def on_release(self, key):
        """按键释放回调"""
        try:
            if key in self.current_keys_control:
                self.current_keys_control.remove(key)
        except KeyError:
            pass

    def start_listener(self):
        """启动键盘监听"""
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()


class DisplayThread:
    """检测结果展示线程"""
    
    def __init__(self, logger):
        self.logger = logger
        self.result_queue = queue.Queue()
        self._running = False
        self._thread = None
    
    def start(self):
        """启动展示线程"""
        self._running = True
        self._thread = threading.Thread(target=self._display_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """停止展示线程"""
        self._running = False
        self.result_queue.put(None)
    
    def put_frame(self, frame: np.ndarray):
        """放入待展示的帧"""
        self.result_queue.put(frame)
    
    def _display_loop(self):
        """展示循环"""
        while self._running:
            try:
                frame = self.result_queue.get()
                if frame is None:
                    break
                cv2.imshow("Game Capture", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception as e:
                self.logger.error(f"展示显示报错: {e}")
        cv2.destroyAllWindows()


def analyse_det_result_common(
    results,
    hero_height: int,
    img: Optional[np.ndarray],
    names: List[str],
    colors: List[Tuple[int, int, int]],
    show: bool = False,
    extra_classes: Optional[List[str]] = None
) -> dict:
    """
    分析YOLO检测结果的公共函数
    
    Args:
        results: YOLO检测结果
        hero_height: 角色高度偏移
        img: 用于绘制的图像（可选）
        names: 类别名称列表
        colors: 类别颜色列表
        show: 是否绘制检测框
        extra_classes: 额外需要处理的类别（如forward, ball, hole）
    
    Returns:
        包含检测结果的字典
    """
    if results is None or len(results) == 0:
        return {}
    
    result_dict = {
        'boss_xywh_list': [],
        'monster_xywh_list': [],
        'elite_monster_xywh_list': [],
        'loot_xywh_list': [],
        'gold_xywh_list': [],
        'door_xywh_list': [],
        'door_boss_xywh_list': [],
        'hero_xywh': None,
        'hero_conf': -1,
        'card_num': 0,
        'continue_exist': False,
        'shop_exist': False,
        'shop_mystery_exist': False,
        'menu_exist': False,
        'sss_exist': False,
    }
    
    # 处理额外类别
    if extra_classes:
        for cls_name in extra_classes:
            if cls_name in ['forward']:
                result_dict['forward_exists'] = False
            elif cls_name in ['ball', 'hole']:
                result_dict[f'{cls_name}_xywh_list'] = []
    
    result = results[0]
    for box in result.boxes:
        cls = int(box.cls)
        xywh = box.xywh[0].tolist()
        xyxy = box.xyxy[0].tolist()
        conf = float(box.conf[0])
        
        cls_name = names[cls] if cls < len(names) else 'unknown'
        
        # 高度处理
        if cls_name == "hero":
            xywh[1] += hero_height
            if conf > result_dict['hero_conf']:
                result_dict['hero_conf'] = conf
                result_dict['hero_xywh'] = xywh

        elif cls_name == "boss":
            xywh[1] = xyxy[3] - 20
            result_dict['boss_xywh_list'].append(xywh)

        elif cls_name == "monster":
            xywh[1] += MONSTER_HEIGHT
            result_dict['monster_xywh_list'].append(xywh)

        elif cls_name == "elite-monster":
            xywh[1] = xyxy[3] - 20
            result_dict['elite_monster_xywh_list'].append(xywh)

        elif cls_name == "door":
            xywh[1] += DOOR_HEIGHT
            result_dict['door_xywh_list'].append(xywh)

        elif cls_name == "door-boss":
            xywh[1] += DOOR_HEIGHT
            result_dict['door_boss_xywh_list'].append(xywh)

        elif cls_name == "loot":
            xywh[1] += LOOT_HEIGHT
            if xywh[2] > 111 and xywh[3] < 110:
                if (xyxy[1] + 60) > xywh[1]:
                    xywh[1] = xyxy[1] + 60
            result_dict['loot_xywh_list'].append(xywh)

        elif cls_name == 'gold':
            xywh[1] += LOOT_HEIGHT
            if xywh[2] > 111 and xywh[3] < 110:
                if (xyxy[1] + 60) > xywh[1]:
                    xywh[1] = xyxy[1] + 60
            result_dict['gold_xywh_list'].append(xywh)

        elif cls_name == "continue":
            result_dict['continue_exist'] = True

        elif cls_name == "card":
            result_dict['card_num'] += 1

        elif cls_name == "shop":
            result_dict['shop_exist'] = True

        elif cls_name == "shop-mystery":
            result_dict['shop_mystery_exist'] = True

        elif cls_name == "menu":
            result_dict['menu_exist'] = True

        elif cls_name == "sss":
            result_dict['sss_exist'] = True

        elif cls_name == "forward" and extra_classes and 'forward' in extra_classes:
            result_dict['forward_exists'] = True

        elif cls_name == "ball" and extra_classes and 'ball' in extra_classes:
            xywh[1] = xyxy[3] + 50
            result_dict['ball_xywh_list'].append(xywh)

        elif cls_name == "hole" and extra_classes and 'hole' in extra_classes:
            xywh[1] += DOOR_HEIGHT
            result_dict['hole_xywh_list'].append(xywh)

        # 绘制检测框
        if show and img is not None:
            label = f'{cls_name} {conf:.2f}'
            color = colors[cls] if cls < len(colors) else (255, 255, 255)
            plot_one_box(box.xyxy[0], img, label=label, color=color, line_thickness=2)
    
    return result_dict


def draw_debug_points(
    img: np.ndarray,
    result_dict: dict,
    hero_height: int
):
    """绘制调试用的定位点"""
    hero_xywh = result_dict.get('hero_xywh')
    
    if hero_xywh:
        # 推理后的中心
        cv2.circle(img, (int(hero_xywh[0]), int(hero_xywh[1] - hero_height)), 1, COLOR_RED, 2)
        # 处理后的中心
        cv2.circle(img, (int(hero_xywh[0]), int(hero_xywh[1])), 1, COLOR_GREEN, 2)

    # 掉落物
    for a in result_dict.get('loot_xywh_list', []) + result_dict.get('gold_xywh_list', []):
        cv2.circle(img, (int(a[0]), int(a[1] - LOOT_HEIGHT)), 1, COLOR_RED, 2)
        cv2.circle(img, (int(a[0]), int(a[1])), 1, COLOR_GREEN, 2)

    # 怪物
    for a in result_dict.get('monster_xywh_list', []):
        cv2.circle(img, (int(a[0]), int(a[1])), 1, COLOR_GREEN, 2)
        cv2.circle(img, (int(a[0]), int(a[1] - MONSTER_HEIGHT)), 1, COLOR_RED, 2)

    # Boss
    for a in result_dict.get('boss_xywh_list', []):
        cv2.circle(img, (int(a[0]), int(a[1])), 1, COLOR_GREEN, 2)
        cv2.circle(img, (int(a[0]), int(a[1] - BOSS_HEIGHT)), 1, COLOR_RED, 2)

    # 球（如果有）
    for a in result_dict.get('ball_xywh_list', []):
        cv2.circle(img, (int(a[0]), int(a[1] - a[3])), 1, COLOR_RED, 2)
        cv2.circle(img, (int(a[0]), int(a[1])), 1, COLOR_GREEN, 2)

    # 门
    for a in result_dict.get('door_xywh_list', []) + result_dict.get('door_boss_xywh_list', []):
        cv2.circle(img, (int(a[0]), int(a[1])), 1, COLOR_GREEN, 2)
        cv2.circle(img, (int(a[0]), int(a[1] - DOOR_HEIGHT)), 1, COLOR_RED, 2)


def generate_random_colors(num_classes: int) -> List[Tuple[int, int, int]]:
    """生成随机颜色列表"""
    return [[random.randint(0, 255) for _ in range(3)] for _ in range(num_classes)]
