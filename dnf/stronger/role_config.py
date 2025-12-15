# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'


from dataclasses import dataclass, asdict, field
from typing import List, Callable, Optional


@dataclass
class Skill:
    name: str = field(default="", metadata={"description": "技能名称"})
    hot_key: Optional[object] = field(default=None, metadata={"description": "技能快捷键"})
    command: Optional[List[object]] = field(default_factory=list, metadata={"description": "指令"})
    concurrent: Optional[bool] = field(default=False, metadata={"description": "是否需要同时按住"})
    cd: Optional[float] = field(default=0, metadata={"description": "技能CD,秒"})
    recent_use_time: Optional[float] = field(default=0, metadata={"description": "最近使用的时间,秒级时间戳"})
    animation_time: Optional[float] = field(default=0.7, metadata={"description": "技能动作演出时间"})
    hotkey_cd_command_cast: Optional[bool] = field(default=False, metadata={"description": "使用快捷键判断CD，且使用指令释放技能"})

    def __post_init__(self):
        if not self.name and self.hot_key is not None:
            self.name = str(self.hot_key)


@dataclass
class RoleConfig:
    """
    RoleConfig 类用于配置角色的相关属性。
    """

    name: str = field(metadata={"description": "角色名称"})
    no: int = field(metadata={"description": "序号"})
    buffs: List[List[object]] = field(metadata={"description": "buff列表"})
    candidate_hotkeys: List[object] = field(metadata={"description": "允许释放的快捷栏列表上的技能"})
    custom_priority_skills: Optional[List[object]] = field(default_factory=list, metadata={"description": "自定义的技能列表"})
    height: int = field(default=180, metadata={"description": "身高，默认值为180"})
    fatigue_all: int = field(default=188, metadata={"description": "总疲劳值，默认值为188"})
    fatigue_reserved: int = field(default=30, metadata={"description": "保留的疲劳值"})
    attack_center_x: Optional[int] = field(default=0, metadata={"description": "角色攻击中心点距离"})
    attack_range_x: Optional[int] = field(default=0, metadata={"description": "攻击范围x"})
    attack_range_y: Optional[int] = field(default=0, metadata={"description": "攻击范围y"})
    buff_effective: Optional[bool] = field(default=False, metadata={"description": "是否上buff"})
    powerful_skills: Optional[List[object]] = field(default_factory=list, metadata={"description": "强力技能列表"})
    white_map_level: int = field(default=2, metadata={"description": "白图等级，默认勇士，（0普通，1冒险，2勇士，依次类推）"})


# 直接运行这个脚本
if __name__ == '__main__':
    pass
