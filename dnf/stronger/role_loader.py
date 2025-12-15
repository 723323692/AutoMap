# -*- coding:utf-8 -*-
"""
角色配置加载器 - 支持从JSON文件加载角色配置
"""

__author__ = "723323692"
__version__ = '1.0'

import json
import os
from typing import List, Optional, Dict, Any

from pynput.keyboard import Key

from dnf.stronger.role_config import RoleConfig, Skill
from dnf.stronger.logger_config import logger


# 特殊按键映射
KEY_MAP = {
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "space": Key.space,
    "tab": Key.tab,
    "ctrl": Key.ctrl_l,
    "ctrl_l": Key.ctrl_l,
    "ctrl_r": Key.ctrl_r,
    "alt": Key.alt_l,
    "alt_l": Key.alt_l,
    "alt_r": Key.alt_r,
    "shift": Key.shift_l,
    "shift_l": Key.shift_l,
    "shift_r": Key.shift_r,
    "esc": Key.esc,
    "enter": Key.enter,
}


def _parse_key(key_str: str) -> Any:
    """解析按键字符串为实际按键"""
    if isinstance(key_str, str):
        lower_key = key_str.lower()
        if lower_key in KEY_MAP:
            return KEY_MAP[lower_key]
        return key_str
    return key_str


def _parse_skill(skill_data: Any) -> Any:
    """解析技能配置"""
    if isinstance(skill_data, str):
        return _parse_key(skill_data)
    elif isinstance(skill_data, list):
        return [_parse_key(k) for k in skill_data]
    elif isinstance(skill_data, dict):
        return Skill(
            name=skill_data.get("name", ""),
            hot_key=_parse_key(skill_data.get("hot_key")) if skill_data.get("hot_key") else None,
            command=[_parse_key(k) for k in skill_data.get("command", [])],
            concurrent=skill_data.get("concurrent", False),
            cd=skill_data.get("cd", 0),
            animation_time=skill_data.get("animation_time", 0.7),
            hotkey_cd_command_cast=skill_data.get("hotkey_cd_command_cast", False)
        )
    return skill_data


def load_role_from_json(json_path: str) -> Optional[RoleConfig]:
    """
    从JSON文件加载角色配置
    
    Args:
        json_path: JSON文件路径
        
    Returns:
        RoleConfig对象，加载失败返回None
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析buffs
        buffs = []
        for buff in data.get("buffs", []):
            buffs.append([_parse_key(k) for k in buff])
        
        # 解析技能列表
        candidate_hotkeys = [_parse_key(k) for k in data.get("candidate_hotkeys", [])]
        custom_priority_skills = [_parse_skill(s) for s in data.get("custom_priority_skills", [])]
        powerful_skills = [_parse_skill(s) for s in data.get("powerful_skills", [])]
        
        return RoleConfig(
            name=data.get("name", "未命名"),
            no=data.get("no", 0),
            height=data.get("height", 180),
            fatigue_all=data.get("fatigue_all", 188),
            fatigue_reserved=data.get("fatigue_reserved", 30),
            attack_center_x=data.get("attack_center_x", 0),
            buff_effective=data.get("buff_effective", False),
            white_map_level=data.get("white_map_level", 2),
            buffs=buffs,
            candidate_hotkeys=candidate_hotkeys,
            custom_priority_skills=custom_priority_skills,
            powerful_skills=powerful_skills
        )
    except Exception as e:
        logger.error(f"加载角色配置失败 {json_path}: {e}")
        return None


def load_roles_from_directory(dir_path: str) -> List[RoleConfig]:
    """
    从目录加载所有角色配置
    
    Args:
        dir_path: 配置目录路径
        
    Returns:
        RoleConfig列表
    """
    roles = []
    
    if not os.path.exists(dir_path):
        logger.warning(f"角色配置目录不存在: {dir_path}")
        return roles
    
    for filename in sorted(os.listdir(dir_path)):
        if filename.endswith('.json') and not filename.startswith('example'):
            json_path = os.path.join(dir_path, filename)
            role = load_role_from_json(json_path)
            if role:
                roles.append(role)
                logger.debug(f"加载角色配置: {role.name}")
    
    return roles


def save_role_to_json(role: RoleConfig, json_path: str) -> bool:
    """
    保存角色配置到JSON文件
    
    Args:
        role: RoleConfig对象
        json_path: 保存路径
        
    Returns:
        是否保存成功
    """
    try:
        def serialize_key(key: Any) -> str:
            if isinstance(key, Key):
                return key.name
            return str(key)
        
        def serialize_skill(skill: Any) -> Any:
            if isinstance(skill, str):
                return skill
            elif isinstance(skill, Key):
                return skill.name
            elif isinstance(skill, list):
                return [serialize_key(k) for k in skill]
            elif isinstance(skill, Skill):
                return {
                    "name": skill.name,
                    "hot_key": serialize_key(skill.hot_key) if skill.hot_key else None,
                    "command": [serialize_key(k) for k in skill.command],
                    "concurrent": skill.concurrent,
                    "cd": skill.cd,
                    "animation_time": skill.animation_time,
                    "hotkey_cd_command_cast": skill.hotkey_cd_command_cast
                }
            return skill
        
        data = {
            "name": role.name,
            "no": role.no,
            "height": role.height,
            "fatigue_all": role.fatigue_all,
            "fatigue_reserved": role.fatigue_reserved,
            "attack_center_x": role.attack_center_x,
            "buff_effective": role.buff_effective,
            "white_map_level": role.white_map_level,
            "buffs": [[serialize_key(k) for k in buff] for buff in role.buffs],
            "candidate_hotkeys": [serialize_key(k) for k in role.candidate_hotkeys],
            "custom_priority_skills": [serialize_skill(s) for s in role.custom_priority_skills],
            "powerful_skills": [serialize_skill(s) for s in role.powerful_skills]
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return True
    except Exception as e:
        logger.error(f"保存角色配置失败 {json_path}: {e}")
        return False
