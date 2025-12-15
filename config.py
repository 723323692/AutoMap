# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'


import os

# 项目根路径
# project_base_path = 'D:/dev/workspace/PyCharmProjects/baby-bus'
# project_base_path = os.getcwd()
project_base_path = os.path.dirname(os.path.abspath(__file__))

# 启动提示音
sound1 = os.path.normpath(f'{project_base_path}/assets/audio/sound1.wav')
# 终止提示音
sound2 = os.path.normpath(f'{project_base_path}/assets/audio/sound2.wav')
# 暂停提示音
sound3 = os.path.normpath(f'{project_base_path}/assets/audio/sound3.wav')
