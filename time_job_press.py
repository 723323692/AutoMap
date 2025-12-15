# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'

import os
import time

import cv2
import schedule
import win32gui
from pynput.keyboard import Key
import keyboard as kboard

import config as config_
import dnf.dnf_config as dnf
import utils.window_utils as wu
from dnf.stronger.player import match_and_click
from utils import keyboard_utils as kbu


def prepare_start():
    '''
    先简单处理 自动运行脚本，定时按键触发运行
    wegame启动
        前提脚本运行起来，但是不要按键触发运行。
        登录wegame，并把wegame窗口置于最上层，游戏分辨率设置好，确保登录游戏后是脚本可正常运行的状态
    '''
    print("准备启动...")

    # wegame启动
    hwnd_desktop = win32gui.GetDesktopWindow()
    full_img = wu.capture_window_BGRX(hwnd_desktop)
    icon = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/wegame_dnf_icon.png'), cv2.IMREAD_GRAYSCALE)
    button = cv2.imread(os.path.normpath(f'{config_.project_base_path}/assets/img/wegame_start_btn.png'), cv2.IMREAD_GRAYSCALE)

    print("点击dnf图标")
    time.sleep(1)
    match_and_click(full_img, 0, 0, icon, (506, 504))
    time.sleep(5)

    full_img = wu.capture_window_BGRX(hwnd_desktop)
    print("点击启动按钮")
    match_and_click(full_img, 0, 0, button, (506, 504), 0.8)
    time.sleep(1)
    print("等待游戏启动")
    time.sleep(120)
    print("游戏启动完毕")

    for i in range(6):
        kbu.do_press(Key.up)
        time.sleep(0.2)

    for i in range(6):
        kbu.do_press(Key.left)
        time.sleep(0.2)

    kbu.do_press(Key.space)
    time.sleep(10)

    # 按下脚本启动组合键
    # kbu.do_press('=')
    kboard.press_and_release(dnf.key_start_script)

    print(f"已按下 {dnf.key_start_script} 键")

    # abyss_mian(1,20,'买')
    # stronger_mian(1,20,'每日','买')
    # stronger_mian(1,42,'妖气','买')


start_at = "02:03"  # 设定执行时间
schedule.every().day.at(start_at).do(prepare_start)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(20)  # 每20秒检查一次


# 启动定时任务
if __name__ == "__main__":
    print(f"定时任务已启动，将在 {start_at} 按下 {dnf.key_start_script} 键...")
    run_scheduler()
