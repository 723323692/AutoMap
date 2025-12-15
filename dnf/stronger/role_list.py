# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'

from pprint import pprint
from typing import List

from pynput.keyboard import Key

from dnf.stronger.role_config import RoleConfig as R, RoleConfig
from dnf.stronger.role_config import Skill as S


def get_role_config_list(account_code):
    # 总疲劳值
    default_fatigue_all = 188
    # 保留的疲劳值
    # default_fatigue_reserved = 30
    default_fatigue_reserved = 0

    role_configs = []
    role_configs1 = []

    role_configs1.append(R(name='花花', no=len(role_configs1) + 1,
                           buffs=[[Key.up, Key.up, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               's',
                               'e',
                               'a',
                               'w',
                               'g',
                               'f',
                               'h',
                               'q'
                           ],
                           height=141,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved
                           ))

    role_configs1.append(R(name='剑魂', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               S(name='拔刀', command=['q', 'q'], hot_key='q', hotkey_cd_command_cast=True),
                               'g',
                               'e',
                               'f',
                               'r',
                               'd',
                               'w'
                           ],
                           height=155,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'd',
                               'g',
                           ]
                           ))

    role_configs1.append(R(name='奶妈', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           custom_priority_skills=[
                               'a',
                               S(name='勇气颂歌', command=['s', 'x', 'x', 'x', 'c'], hot_key='s',
                                 hotkey_cd_command_cast=True),
                               'e',
                               'r',
                               'd',
                               'q'
                           ],
                           height=151,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'f',
                           ]
                           ))

    role_configs1.append(R(name='暗枪', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           custom_priority_skills=[
                               't',
                               'd',
                               'g',
                               'f',
                               's',
                               'e'
                           ],
                           height=167,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'r',
                           ]
                           ))

    role_configs1.append(R(name='黑五', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               S(name='w', command=['w'], hot_key='w', hotkey_cd_command_cast=False, cd=7.5),
                               S(name='大上挑', command=['a'], hot_key='a', hotkey_cd_command_cast=False, cd=10.5),
                               S(name='e', command=['e'], hot_key='e', hotkey_cd_command_cast=False, cd=25.5),
                               S(name='q', command=['q'], hot_key='q', hotkey_cd_command_cast=False, cd=30.5),
                               S(name='r', command=['r'], hot_key='r', hotkey_cd_command_cast=False, cd=33),

                           ],
                           height=155,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           ))

    role_configs1.append(R(name='刃影', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           height=149,
                           custom_priority_skills=[
                               'q',
                               'e',
                               'w',
                               'g',
                               'r',
                               's',
                               'd'
                           ],
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved
                           ))

    role_configs1.append(R(name='男弹药', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'd',
                               's',
                               'q',
                               'w',
                               'r',
                               'g',
                               'a',
                               'h'
                           ],
                           height=170,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               Key.ctrl_l
                           ]
                           ))

    role_configs1.append(R(name='奶弓', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           custom_priority_skills=[
                               S(name='加速', command=['w', 'a'], cd=2),
                               S(name='净化', command=['q', 's'], cd=2),
                               's',
                               'r',
                               'f',
                               'g',
                               'd'
                           ],
                           height=138,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved
                           ))

    role_configs1.append(R(name='鬼泣', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           height=155,
                           custom_priority_skills=[
                               'q',
                               'e',
                               'g',
                               'r',
                               's',
                               'd',
                               'f',
                               'h',
                           ],
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved
                           ))

    role_configs1.append(R(name='瞎子', no=len(role_configs1) + 1,
                           buffs=[[Key.ctrl_l]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           custom_priority_skills=[
                               'q',
                               'e',
                               'r',
                               'g',
                               's',
                               Key.ctrl_l
                           ],
                           height=155,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved
                           ))

    role_configs1.append(R(name='剑宗', no=len(role_configs1) + 1,
                           buffs=[[Key.left, Key.down, Key.right, Key.space, Key.up]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           custom_priority_skills=[
                               'q',
                               'd',
                               'w',
                               't',
                               'e',
                               'f',
                               Key.ctrl_l
                           ],
                           height=149,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved
                           ))

    role_configs1.append(R(name='红眼', no=len(role_configs1) + 1,
                           buffs=[[Key.up, Key.down, Key.space], [Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'w',
                               'q',
                               'e',
                               'r',
                               'h',
                               'g'
                           ],
                           height=155,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               Key.ctrl_l]
                           ))

    role_configs1.append(R(name='奶爸', no=len(role_configs1) + 1,
                           buffs=[[Key.left, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           height=169,
                           custom_priority_skills=[
                               'w',
                               'e',
                               'r',
                               't',
                               'a',
                               'd',
                               'f',
                               'g'
                           ],
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'r',
                               'g',
                           ]
                           ))

    role_configs1.append(R(name='奶萝', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           height=138,
                           custom_priority_skills=[
                               'q',
                               's',
                               't',
                               'd',
                               'h',
                           ],
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'd',
                           ]
                           ))

    role_configs1.append(R(name='剑帝', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           height=149,
                           custom_priority_skills=[
                               'q',
                               'e',
                               'w',
                               'g',
                               'r',
                               's',
                               'd',
                               'f',
                               'h'
                           ],
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               Key.ctrl_l,
                               'h'
                           ]
                           ))

    role_configs1.append(R(name='赵云', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           custom_priority_skills=[
                               's',
                               'e',
                               'r',
                               'h',
                               'q',
                               'g'
                           ],
                           height=167,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               Key.ctrl_l
                           ]
                           ))

    role_configs1.append(R(name='妖护士', no=len(role_configs1) + 1,
                           buffs=[[Key.left, Key.left, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'w',
                               'e',
                               'r',
                               's',
                               'f',
                               'q'
                           ],
                           height=138,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'g'
                           ]
                           ))

    role_configs1.append(R(name='暗帝', no=len(role_configs1) + 1,
                           buffs=[[Key.left, Key.left, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'a',
                               'e',
                               'w',
                               't',
                               'f',
                               'g',
                               'q'
                           ],
                           height=138,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'h'
                           ]
                           ))

    role_configs1.append(R(name='奶枪1', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           custom_priority_skills=[
                               'q',
                               'e',
                               'f',
                               't',
                               Key.ctrl_l,
                               'e',
                               'd',
                               's',
                               'r',
                           ],
                           height=158,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'w'
                           ]
                           ))

    role_configs1.append(R(name='奇美拉', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'e',
                               'a',
                               S(name='毒液喷洒', command=['s', '', '', '', '', 's'], hot_key='s',
                                 hotkey_cd_command_cast=True, animation_time=0.2),
                               'd',
                               S(name='95', command=['q', '', '', '', 'q'], hot_key='q',
                                 hotkey_cd_command_cast=True),
                               'w',
                               'g',
                               'f',
                           ],
                           height=138,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'r'
                           ]
                           ))

    role_configs1.append(R(name='次元', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'd',
                               S(name='毒液喷洒', command=['s', '', '', '', '', 's'], hot_key='s',
                                 hotkey_cd_command_cast=True, animation_time=0.2),
                               'q',
                               'r',
                               'e',
                               'g',
                               'f',
                           ],
                           height=152,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'g'
                           ]
                           ))

    role_configs1.append(R(name='复仇', no=len(role_configs1) + 1,
                           buffs=[[Key.ctrl_l]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           custom_priority_skills=[
                               'w',
                               'g',
                               'e',
                               'd',
                               'a',
                               't'
                           ],
                           height=164,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'r'
                           ]
                           ))

    role_configs1.append(R(name='蓝拳', no=len(role_configs1) + 1,
                           buffs=[[Key.ctrl_l], [Key.up, Key.up, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'q',
                               'e',
                               'd',
                               'a',
                               'g',
                               'f',
                               's',
                               'r'
                           ],
                           height=164,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               Key.ctrl_l,
                               Key.alt_l
                           ]
                           ))

    role_configs1.append(R(name='剑魔', no=len(role_configs1) + 1,
                           buffs=[[Key.ctrl_l], [Key.up, Key.up, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'f',
                               'g',
                               'e',
                               'h',
                               't',
                               'r'
                           ],
                           height=149,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'w'
                           ]
                           ))

    role_configs1.append(R(name='合金', no=len(role_configs1) + 1,
                           buffs=[[Key.ctrl_l]],
                           buff_effective=True,
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'w',
                               'f',
                               's',
                               'd',
                               'r',
                               'g'
                           ],
                           height=170,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               't'
                           ]
                           ))

    role_configs1.append(R(name='风法', no=len(role_configs1) + 1,
                           buffs=[[Key.ctrl_l]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'a',
                               'f',
                               'd',
                               'g',
                               'w',
                               'r',
                               's'
                           ],
                           height=150,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               't'
                           ]
                           ))

    role_configs1.append(R(name='元素爆破', no=len(role_configs1) + 1,
                           buffs=[[Key.ctrl_l]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'f',
                               'g',
                               'h',
                               'w',
                               'd',
                               'r',
                               't'
                           ],
                           height=150,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               Key.ctrl_l
                           ]
                           ))

    role_configs1.append(R(name='空姐', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space, Key.right],
                                  [Key.left, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'w',
                               S(name='切利', command=['e', 'd', '', '', '', '', 'e'], hot_key='e',
                                 hotkey_cd_command_cast=True),
                               'g',
                               's',
                               'a',
                               'd',
                               'f'
                           ],
                           height=158,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'q'
                           ]
                           ))

    role_configs1.append(R(name='魔灵', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'q',
                               'e',
                               'd',
                               's',
                               'f',
                               'r',
                               Key.ctrl_l
                           ],
                           height=138,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'r',
                               'g'
                           ]
                           ))

    role_configs1.append(R(name='忍者', no=len(role_configs1) + 1,
                           buffs=[],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'a',
                               'd',
                               's',
                               'e',
                               'q',
                               'r',
                               'w',
                               'f',
                               'g'
                           ],
                           height=151,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved
                           ))

    role_configs1.append(R(name='旅人', no=len(role_configs1) + 1,
                           buffs=[[Key.ctrl_l]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'd',
                               'r',
                               's',
                               'f',
                               'w',
                               'a',
                               'g'
                           ],
                           height=138,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               Key.ctrl_l
                           ]
                           ))

    role_configs1.append(R(name='帕拉丁', no=len(role_configs1) + 1,
                           buffs=[[Key.ctrl_l]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'd',
                               'e',
                               'a',
                               'w',
                               'r',
                               'f',
                               'g'
                           ],
                           height=138,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'f',
                               'd'
                           ]
                           ))

    role_configs1.append(R(name='刺客', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           custom_priority_skills=[
                               'r',
                               'd',
                               'f',
                               'q',
                               'w',
                               'e',
                               'g',
                               't'
                           ],
                           height=151,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               Key.alt_l
                           ]
                           ))

    role_configs1.append(R(name='机械', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'e',
                               'g',
                               S(name='小自爆', command=['s', 'a', '', '', '', '', 'q'], hot_key='s',
                                 hotkey_cd_command_cast=True),
                               S(name='95', command=[Key.ctrl_l, 'a', 's', '', '', '', Key.ctrl_l], animation_time=1.2,
                                 hot_key=Key.ctrl_l, hotkey_cd_command_cast=True),
                               S(name='自爆陷阱', command=['f', '', '', '', '', '', 'q'], hot_key='f',
                                 hotkey_cd_command_cast=True),
                               S(name='大自爆', command=['d', '', '', '', '', '', 'q'], hot_key='d',
                                 hotkey_cd_command_cast=True)

                           ],
                           height=170,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'r',
                               'h'
                           ]
                           ))

    #
    #
    # role_configs1.append(R(name='四姨', no=len(role_configs1) + 1,
    #                        buffs=[[Key.down, Key.down, Key.space]],
    #                        # buff_effective=True,
    #                        candidate_hotkeys=['x'],
    #                        custom_priority_skills=[
    #                            'e',
    #                            'w',
    #                            'r',
    #                            'g',
    #                            S(name='毒液喷洒', command=['f', '', '', '', '', 'f'], hot_key='f',
    #                              hotkey_cd_command_cast=True, animation_time=0.2),
    #                            'd',
    #                            's'
    #                        ],
    #                        height=151,
    #                        fatigue_all=default_fatigue_all,
    #                        fatigue_reserved=default_fatigue_reserved,
    #                        powerful_skills=[
    #                            't'
    #                        ]
    #                        ))
    #
    # role_configs1.append(R(name='女漫游', no=len(role_configs1) + 1,
    #                        buffs=[[Key.down, Key.down, Key.space]],
    #                        # buff_effective=True,
    #                        candidate_hotkeys=['x'],
    #                        custom_priority_skills=[
    #                            'd',
    #                            't',
    #                            S(name='毒液喷洒', command=['h', '', '', '', '', 'a'], hot_key='h',
    #                              hotkey_cd_command_cast=True, animation_time=0.2),
    #                            Key.ctrl_l,
    #                            'f',
    #                            'g'
    #                        ],
    #                        height=158,
    #                        fatigue_all=default_fatigue_all,
    #                        fatigue_reserved=default_fatigue_reserved,
    #                        powerful_skills=[
    #                            Key.alt_l
    #                        ]
    #                        ))
    #
    # role_configs1.append(R(name='冰洁', no=len(role_configs1) + 1,
    #                        buffs=[[Key.down, Key.down, Key.space]],
    #                        # buff_effective=True,
    #                        candidate_hotkeys=['x'],
    #                        custom_priority_skills=[
    #                            'g',
    #                            'f',
    #                            'w',
    #                            'r',
    #                            'd',
    #                            't',
    #                            'e'
    #                        ],
    #                        height=150,
    #                        fatigue_all=default_fatigue_all,
    #                        fatigue_reserved=default_fatigue_reserved,
    #                        powerful_skills=[
    #                            Key.ctrl_l
    #
    #                        ]
    #                        ))
    #
    # role_configs1.append(R(name='放火奶', no=len(role_configs1) + 1,
    #                        buffs=[['f']],
    #                        buff_effective=True,
    #                        candidate_hotkeys=['x'],
    #                        custom_priority_skills=[
    #                            'g',
    #                            'h',
    #                            't',
    #                            'r',
    #                            'w',
    #                            'q',
    #                            'a'
    #                        ],
    #                        height=151,
    #                        fatigue_all=default_fatigue_all,
    #                        fatigue_reserved=default_fatigue_reserved,
    #                        powerful_skills=[
    #                            Key.ctrl_l
    #                        ]
    #                        ))
    #
    # role_configs1.append(R(name='泥鳅奶', no=len(role_configs1) + 1,
    #                        buffs=[['f']],
    #                        # buff_effective=True,
    #                        candidate_hotkeys=['x'],
    #                        custom_priority_skills=[
    #                            'd',
    #                            'w',
    #                            'f',
    #                            'g',
    #                            Key.ctrl_l,
    #                            'a',
    #                            't'
    #                        ],
    #                        height=151,
    #                        fatigue_all=default_fatigue_all,
    #                        fatigue_reserved=default_fatigue_reserved,
    #                        powerful_skills=[
    #                            'r'
    #                        ]
    #                        ))
    #
    # role_configs1.append(R(name='母鸡', no=len(role_configs1) + 1,
    #                        buffs=[['q']],
    #                        buff_effective=True,
    #                        candidate_hotkeys=['x'],
    #                        custom_priority_skills=[
    #                            'a',
    #                            'a',
    #                            's',
    #                            'f',
    #                            Key.ctrl_l
    #                        ],
    #                        height=151,
    #                        fatigue_all=default_fatigue_all,
    #                        fatigue_reserved=default_fatigue_reserved,
    #                        powerful_skills=[
    #                            'w',
    #                            'e'
    #                        ]
    #                        ))

    role_configs1.append(R(name='女大枪', no=len(role_configs1) + 1,
                           buffs=[['q']],
                           # buff_effective=True,
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'a',
                               'e',
                               'd',
                               'q',
                               'g',
                               'f',
                               Key.ctrl_l
                           ],
                           height=151,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               't',
                           ]
                           ))

    role_configs1.append(R(name='奶枪2', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           buff_effective=True,
                           custom_priority_skills=[
                               'q',
                               'e',
                               'f',
                               't',
                               Key.ctrl_l,
                               'e',
                               'd',
                               's',
                               'r',
                           ],
                           height=158,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               'w'
                           ]
                           ))


    role_configs1.append(R(name='龙神', no=len(role_configs1) + 1,
                           buffs=[[Key.right, Key.right, Key.space]],
                           candidate_hotkeys=['x'],
                           custom_priority_skills=[
                               'f',
                               'g',
                               'h',
                               'q',
                               'd',
                               'r',
                               't'
                           ],
                           height=138,
                           fatigue_all=default_fatigue_all,
                           fatigue_reserved=default_fatigue_reserved,
                           powerful_skills=[
                               't',
                               Key.ctrl_l,

                           ]
                           ))

    # -----------------------------------------------------------------------------------------------------------------
    # -----------------------------------------------------------------------------------------------------------------
    # -----------------------------------------------------------------------------------------------------------------
    # -----------------------------------------------------------------------------------------------------------------

    role_configs.append(R(name='瞎子', no=len(role_configs) + 1,
                          buffs=[[Key.ctrl_l]],
                          candidate_hotkeys=['x'],
                          buff_effective=True,
                          custom_priority_skills=[
                              'q',
                              'e',
                              'r',
                              'g',
                              's',
                              Key.ctrl_l
                          ],
                          height=155,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved
                          ))

    role_configs.append(R(name='花花', no=len(role_configs) + 1,
                          buffs=[[Key.up, Key.up, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'q',
                              'w',
                              'e',
                              'r',
                              't',
                              Key.ctrl_l,
                              's',
                              'd',
                              'f'
                          ],
                          height=141,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved
                          ))

    role_configs.append(R(name='红眼', no=len(role_configs) + 1,
                          buffs=[[Key.up, Key.down, Key.space], [Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'w',
                              'q',
                              'e',
                              'r',
                              'h',
                              't'
                          ],
                          height=155,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved
                          ))

    role_configs.append(R(name='旅人', no=len(role_configs) + 1,
                          buffs=[[Key.up, Key.down, Key.space], [Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'w',
                              's',
                              'f',
                              'e',
                              'r',
                              'f'
                          ],
                          height=138,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved
                          ))

    role_configs.append(R(name='剑魂1', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              S(name='拔刀', command=['q', 'q'], hot_key='q', hotkey_cd_command_cast=True),
                              'g',
                              'e',
                              'f',
                              'r',
                              'd',
                              't'
                          ],
                          height=155,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              't',
                              'g',
                          ]
                          ))

    role_configs.append(R(name='奶爸', no=len(role_configs) + 1,
                          buffs=[['e']],
                          candidate_hotkeys=['x'],
                          buff_effective=True,
                          custom_priority_skills=[
                              'w',
                              'r',
                              'd',
                              'a',
                              'g',
                              't'
                          ],
                          height=164,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              Key.alt_l,
                              't'
                          ]
                          ))

    role_configs.append(R(name='妖护士1', no=len(role_configs) + 1,
                          buffs=[[Key.left, Key.left, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'w',
                              'e',
                              'r',
                              's',
                              'f',
                              'g',
                              'q'
                          ],
                          height=138,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'r',
                              'g',
                          ]
                          ))

    role_configs.append(R(name='刃影', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          height=149,
                          custom_priority_skills=[
                              'q',
                              'e',
                              'w',
                              'g',
                              'r',
                              's',
                              'd'
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved
                          ))

    role_configs.append(R(name='剑帝1', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          height=149,
                          custom_priority_skills=[
                              'q',
                              'e',
                              'w',
                              'g',
                              'r',
                              's',
                              'd',
                              'f',
                              'h'
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              Key.ctrl_l,
                              'h'
                          ]
                          ))


    role_configs.append(R(name='鬼泣', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          height=155,
                          custom_priority_skills=[
                              'q',
                              'e',
                              'g',
                              'r',
                              's',
                              'd',
                              'f',
                              'h',
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved
                          ))

    role_configs.append(R(name='男散打', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space], [Key.down, Key.down, Key.space]],
                          candidate_hotkeys=['x'],
                          buff_effective=True,
                          height=167,
                          custom_priority_skills=[
                              'e',
                              'g',
                              'r',
                              'd',
                              'f',
                              'h',
                              't',
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved.imag,
                          powerful_skills=[
                              'q',
                              'w',
                          ]
                          ))

    role_configs.append(R(name='审判', no=len(role_configs) + 1,
                          buffs=[[Key.left, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          height=169,
                          custom_priority_skills=[
                              'w',
                              'e',
                              'r',
                              't',
                              'a',
                              'd',
                              'f',
                              'g'
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'r',
                              'g',
                          ]
                          ))

    role_configs.append(R(name='特工', no=len(role_configs) + 1,
                          buffs=[[Key.left, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          height=173,
                          custom_priority_skills=[
                              S(name='月步', command=['s', 's', 's', 's', 's', 's', 's', 's', 's', 's', 's', 's'],
                                cd=11.8, animation_time=0.3),
                              'f',
                              S(name='锁定射击', command=['w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w'],
                                cd=11.8, concurrent=True, animation_time=0.1),
                              'e',
                              'h',
                              'g',
                              'q'
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'r',
                              't'
                          ]
                          ))

    role_configs.append(R(name='奶弓', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          buff_effective=True,
                          custom_priority_skills=[
                              S(name='加速', command=['w', 'a'], cd=2),
                              S(name='净化', command=['q', 's'], cd=2),
                              's',
                              'r',
                              'f',
                              'g',
                              'd'
                          ],
                          height=138,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved
                          ))

    role_configs.append(R(name='奶妈', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          buff_effective=True,
                          custom_priority_skills=[
                              'a',
                              S(name='勇气颂歌', command=['s', 'x', 'x', 'x', 'c'], hot_key='s',
                                hotkey_cd_command_cast=True),
                              'e',
                              'r',
                              'd',
                              'q'
                          ],
                          height=151,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'f',
                          ]
                          ))

    role_configs.append(R(name='鹦鹉', no=len(role_configs) + 1,
                          buffs=[[Key.up, Key.down, Key.space]],
                          candidate_hotkeys=['x'],
                          buff_effective=True,
                          custom_priority_skills=[
                              S(name='二觉链子', command=['a'], cd=0.3)
                          ],
                          height=151,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'r',
                          ]
                          ))

    role_configs.append(R(name='妖护士2', no=len(role_configs) + 1,
                          buffs=[[Key.left, Key.left, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'w',
                              'e',
                              'r',
                              's',
                              'f',
                              'q'
                          ],
                          height=138,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'g'
                          ]
                          ))

    role_configs.append(R(name='剑帝2', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          height=149,
                          custom_priority_skills=[
                              'q',
                              'e',
                              'w',
                              'g',
                              'r',
                              's',
                              'd',
                              'f',
                              'h'
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              Key.ctrl_l,
                              'h',
                          ]

                          ))

    role_configs.append(R(name='剑魂2', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              S(name='拔刀', command=['q', 'q'], hot_key='q', hotkey_cd_command_cast=True),
                              'g',
                              'e',
                              'f',
                              'r',
                              'w'
                          ],
                          height=155,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'd',
                              'g',
                          ]
                          ))

    role_configs.append(R(name='红眼2', no=len(role_configs) + 1,
                          buffs=[[Key.up, Key.down, Key.space], [Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'w',
                              'q',
                              'e',
                              'r',
                              # 'a',
                              'h',
                              'g'
                          ],
                          height=155,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'a',
                              Key.ctrl_l]
                          ))

    role_configs.append(R(name='剑影', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'w',
                              'q',
                              'e',
                              'r',
                              'f',
                              'd',
                              'g',
                          ],
                          height=155,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'h',
                              Key.ctrl_l
                          ]
                          ))

    role_configs.append(R(name='剑帝3', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          height=149,
                          custom_priority_skills=[
                              'q',
                              'e',
                              'w',
                              'g',
                              'r',
                              's',
                              'd',
                              'f',
                              'h'
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              Key.ctrl_l,
                              'h'
                          ]
                          ))

    role_configs.append(R(name='奶枪', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          buff_effective=True,
                          custom_priority_skills=[
                              'q',
                              'e',
                              'f',
                              't',
                              Key.ctrl_l,
                              'e',
                              'd',
                              's',
                              'r',
                          ],
                          height=158,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'w'
                          ]
                          ))

    role_configs.append(R(name='奇美拉', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'e',
                              'a',
                              S(name='毒液喷洒', command=['s', '', '', '', '', 's'], hot_key='s',
                                hotkey_cd_command_cast=True, animation_time=0.2),
                              'd',
                              S(name='95', command=['q', '', '', '', 'q'], hot_key='q',
                                hotkey_cd_command_cast=True),
                              'w',
                              'g',
                              'f',
                          ],
                          height=138,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'r'
                          ]
                          ))

    role_configs.append(R(name='奶妈2', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          buff_effective=True,
                          custom_priority_skills=[
                              'a',
                              S(name='勇气颂歌', command=['s', 'x', 'x', 'x', 'c'], hot_key='s',
                                hotkey_cd_command_cast=True),
                              'e',
                              'r',
                              'd',
                              'q'
                          ],
                          height=151,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'f',
                          ]
                          ))

    role_configs.append(R(name='漫游', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'w',
                              'q',
                              'e',
                              'r',
                              'f',
                              'd'
                          ],
                          height=170,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              Key.ctrl_l
                          ]
                          ))

    role_configs.append(R(name='魔道', no=len(role_configs) + 1,
                          buffs=[[Key.up, Key.up, Key.space], [Key.down, Key.up, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              S(name='舒露露', command=['q', 'x', 'x', 'x', 'x', 'x', 'q'], hot_key='q',
                                hotkey_cd_command_cast=True),
                              'd',
                              'w',
                              'h',
                              't',
                              's',
                              'a',
                              'e'
                          ],
                          height=138,
                          attack_center_x=80,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'e',
                              Key.ctrl_l
                          ]
                          ))

    role_configs.append(R(name='大枪', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'w',
                              'q',
                              'r',
                              's',
                              'd',
                              'f',
                              'g',

                          ],
                          height=170,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              't',
                          ]
                          ))

    role_configs.append(R(name='女散打', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          height=141,
                          custom_priority_skills=[
                              'q',
                              'w',
                              'e',
                              'd',
                              'f',
                              'h',
                              S(name='闪电', command=['z'], cd=11.6)
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved.imag,
                          powerful_skills=[
                              'r',
                              't'
                          ]
                          ))

    role_configs.append(R(name='机械', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'e',
                              'g',
                              S(name='小自爆', command=['s', 'a', '', '', '', '', 'q'], hot_key='s',
                                hotkey_cd_command_cast=True),
                              S(name='95', command=[Key.ctrl_l, 'a', 's', '', '', '', Key.ctrl_l], animation_time=1.2,
                                hot_key=Key.ctrl_l, hotkey_cd_command_cast=True),
                              S(name='自爆陷阱', command=['f', '', '', '', '', '', 'q'], hot_key='f',
                                hotkey_cd_command_cast=True),
                              S(name='大自爆', command=['d', '', '', '', '', '', 'q'], hot_key='d',
                                hotkey_cd_command_cast=True)

                          ],
                          height=170,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'r',
                              'h'
                          ]
                          ))

    role_configs.append(R(name='空姐', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space, Key.right],
                                 [Key.left, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'w',
                              S(name='切利', command=['e', 'd', '', '', '', '', 'e'], hot_key='e',
                                hotkey_cd_command_cast=True),
                              'g',
                              'a',
                              'f',
                              'd'
                          ],
                          height=158,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'q'
                          ]
                          ))

    role_configs.append(R(name='花花2', no=len(role_configs) + 1,
                          buffs=[[Key.up, Key.up, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              's',
                              'w',
                              'e',
                              'r',
                              't',
                              'q',
                              'd',
                              'a'
                          ],
                          height=141,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              Key.ctrl_l,
                              'f',
                          ]
                          ))

    role_configs.append(R(name='花花3', no=len(role_configs) + 1,
                          buffs=[[Key.up, Key.up, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              's',
                              'w',
                              'e',
                              'r',
                              't',
                              'q',
                              'd',
                              'a'
                          ],
                          height=141,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              Key.ctrl_l,
                              'f',
                          ]
                          ))

    role_configs.append(R(name='猎人', no=len(role_configs) + 1,
                          buffs=[[Key.up, Key.down, Key.space], [Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'q',
                              's',
                              'd',
                              'e',
                              'f'
                          ],
                          height=138,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'r',
                              'g',
                          ]

                          ))

    role_configs.append(R(name='关羽', no=len(role_configs) + 1,
                          buffs=[[Key.up, Key.down, Key.space], [Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'q',
                              's',
                              'd',
                              'f',
                              't',
                              'w',
                              'e',
                              'r'
                          ],
                          height=166,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'g',
                              'h',
                          ]
                          ))

    role_configs.append(R(name='男弹药', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'd',
                              's',
                              'q',
                              'w',
                              'r',
                              'g',
                              'a',
                              'h'
                          ],
                          height=170,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              Key.ctrl_l
                          ]
                          ))

    role_configs.append(R(name='漫游2', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'w',
                              's',
                              'q',
                              'e',
                              'r',
                              'f',
                              'd'
                          ],
                          height=170,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              Key.ctrl_l
                          ]
                          ))

    role_configs.append(R(name='帕拉丁', no=len(role_configs) + 1,
                          buffs=[[Key.right, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          custom_priority_skills=[
                              'd',
                              's',
                              'f',
                              'e',
                              'g',
                              'q'
                          ],
                          height=138,
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'r',
                              Key.ctrl_l,

                          ]
                          ))

    role_configs.append(R(name='专家', no=len(role_configs) + 1,
                          buffs=[[Key.left, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          height=173,
                          custom_priority_skills=[
                              'd',
                              'f',
                              'e',
                              'r',
                              's',
                              S(name='95', command=['g', '', '', 'g'], hot_key='g', hotkey_cd_command_cast=True,
                                animation_time=1.5),
                              't',
                              'q'
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              S(name='80', command=['w', '', '', 'w'], hot_key='w', hotkey_cd_command_cast=True),
                              'h',
                          ]
                          ))

    role_configs.append(R(name='特工2', no=len(role_configs) + 1,
                          buffs=[[Key.left, Key.right, Key.space]],
                          candidate_hotkeys=['x'],
                          height=173,
                          custom_priority_skills=[
                              S(name='月步', command=['s', 's', 's', 's', 's', 's', 's', 's', 's', 's', 's', 's'],
                                cd=11.8, animation_time=0.3),
                              'f',
                              S(name='锁定射击', command=['w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w'],
                                cd=11.8, concurrent=True, animation_time=0.1),
                              'e',
                              'h',
                              Key.ctrl_l,
                              'g',
                              'q'
                          ],
                          fatigue_all=default_fatigue_all,
                          fatigue_reserved=default_fatigue_reserved,
                          powerful_skills=[
                              'r',
                              't'
                          ]
                          ))


    return role_configs if account_code == 1 else role_configs1


if __name__ == "__main__":
    role_list = int(input("查询账号id:"))
    pprint(get_role_config_list(role_list))


    # print(role_list[1])
    # cike = role_list[0]
    #
    # print(cike)
