# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'


from pynput import keyboard
from pynput.keyboard import Key, KeyCode

window_title = "地下城与勇士：创新世纪"

# 定义小键盘数字1的KeyCode
numpad_0 = KeyCode.from_vk(96)
# 定义小键盘数字2的KeyCode
numpad_2 = KeyCode.from_vk(98)
# 定义小键盘数字7的KeyCode
numpad_7 = KeyCode.from_vk(103)
# 定义上下左右方向键
direct_dic = {"UP": Key.up, "DOWN": Key.down, "LEFT": Key.left, "RIGHT": Key.right}

# 游戏按键定义 再次挑战
key_try_again = numpad_0
# 游戏按键定义 返回城镇
key_return_to_town = Key.f12
# 游戏按键定义 移动物品
Key_collect_loot = Key.ctrl_r
# 游戏按键定义 移动角色
Key_collect_role = numpad_7

# 定义脚本暂停组合键
key_pause_script = {keyboard.Key.delete}
# 定义终止脚本组合键
key_stop_script = {keyboard.Key.end}
# 定义任务开始组合键
key_start_script = 'f10'

# 截图日志
enable_picture_log = True

