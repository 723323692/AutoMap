# -*- coding:utf-8 -*-
"""
角色配置管理器 - 支持从JSON文件加载和保存角色配置
"""

__author__ = "723323692"
__version__ = '1.0'

import json
import os
from typing import List, Optional, Any
from pynput.keyboard import Key

from dnf.stronger.role_config import RoleConfig, Skill

# 配置文件路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROLE_CONFIG_FILE = os.path.join(PROJECT_ROOT, 'role_config.json')

# Key映射表
KEY_MAP = {
    'Key.ctrl_l': Key.ctrl_l,
    'Key.ctrl_r': Key.ctrl_r,
    'Key.alt_l': Key.alt_l,
    'Key.alt_r': Key.alt_r,
    'Key.shift_l': Key.shift_l,
    'Key.shift_r': Key.shift_r,
    'Key.space': Key.space,
    'Key.enter': Key.enter,
    'Key.esc': Key.esc,
    'Key.up': Key.up,
    'Key.down': Key.down,
    'Key.left': Key.left,
    'Key.right': Key.right,
    'Key.tab': Key.tab,
}

# 反向映射
KEY_MAP_REVERSE = {v: k for k, v in KEY_MAP.items()}


def key_to_str(key: Any) -> str:
    """将Key对象转换为字符串"""
    if key in KEY_MAP_REVERSE:
        return KEY_MAP_REVERSE[key]
    return str(key) if key is not None else ''


def str_to_key(s: str) -> Any:
    """将字符串转换为Key对象或普通字符串"""
    if s in KEY_MAP:
        return KEY_MAP[s]
    return s


def skill_to_dict(skill: Any) -> dict:
    """将Skill对象或字符串转换为字典"""
    if isinstance(skill, Skill):
        return {
            'type': 'skill',
            'name': skill.name,
            'hot_key': key_to_str(skill.hot_key),
            'command': [key_to_str(c) for c in (skill.command or [])],
            'concurrent': skill.concurrent,
            'cd': skill.cd,
            'animation_time': skill.animation_time,
            'hotkey_cd_command_cast': skill.hotkey_cd_command_cast
        }
    elif isinstance(skill, Key):
        return {'type': 'key', 'value': key_to_str(skill)}
    else:
        return {'type': 'str', 'value': str(skill)}


def dict_to_skill(d: dict) -> Any:
    """将字典转换为Skill对象或字符串"""
    if d.get('type') == 'skill':
        return Skill(
            name=d.get('name', ''),
            hot_key=str_to_key(d.get('hot_key', '')),
            command=[str_to_key(c) for c in d.get('command', [])],
            concurrent=d.get('concurrent', False),
            cd=d.get('cd', 0),
            animation_time=d.get('animation_time', 0.7),
            hotkey_cd_command_cast=d.get('hotkey_cd_command_cast', False)
        )
    elif d.get('type') == 'key':
        return str_to_key(d.get('value', ''))
    else:
        return d.get('value', '')


def buff_to_list(buff: List[Any]) -> List[str]:
    """将buff列表转换为字符串列表"""
    return [key_to_str(k) for k in buff]


def list_to_buff(lst: List[str]) -> List[Any]:
    """将字符串列表转换为buff列表"""
    return [str_to_key(s) for s in lst]


def role_config_to_dict(role: RoleConfig) -> dict:
    """将RoleConfig对象转换为字典"""
    return {
        'name': role.name,
        'no': role.no,
        'buffs': [buff_to_list(b) for b in role.buffs],
        'candidate_hotkeys': [key_to_str(k) for k in role.candidate_hotkeys],
        'custom_priority_skills': [skill_to_dict(s) for s in (role.custom_priority_skills or [])],
        'height': role.height,
        'fatigue_all': role.fatigue_all,
        'fatigue_reserved': role.fatigue_reserved,
        'attack_center_x': role.attack_center_x or 0,
        'attack_range_x': role.attack_range_x or 0,
        'attack_range_y': role.attack_range_y or 0,
        'buff_effective': role.buff_effective or False,
        'powerful_skills': [skill_to_dict(s) for s in (role.powerful_skills or [])],
        'white_map_level': role.white_map_level
    }


def dict_to_role_config(d: dict) -> RoleConfig:
    """将字典转换为RoleConfig对象"""
    return RoleConfig(
        name=d.get('name', ''),
        no=d.get('no', 0),
        buffs=[list_to_buff(b) for b in d.get('buffs', [])],
        candidate_hotkeys=[str_to_key(k) for k in d.get('candidate_hotkeys', ['x'])],
        custom_priority_skills=[dict_to_skill(s) for s in d.get('custom_priority_skills', [])],
        height=d.get('height', 150),
        fatigue_all=d.get('fatigue_all', 188),
        fatigue_reserved=d.get('fatigue_reserved', 0),
        attack_center_x=d.get('attack_center_x', 0),
        attack_range_x=d.get('attack_range_x', 0),
        attack_range_y=d.get('attack_range_y', 0),
        buff_effective=d.get('buff_effective', False),
        powerful_skills=[dict_to_skill(s) for s in d.get('powerful_skills', [])],
        white_map_level=d.get('white_map_level', 2)
    )


def save_role_configs(role_configs: List[RoleConfig], account_code: int, filepath: str = None):
    """保存角色配置到JSON文件"""
    if filepath is None:
        filepath = ROLE_CONFIG_FILE
    
    # 读取现有配置
    existing_config = {'account1': [], 'account2': []}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
        except:
            pass
    
    # 更新对应账号的配置
    key = 'account1' if account_code == 1 else 'account2'
    existing_config[key] = [role_config_to_dict(r) for r in role_configs]
    
    # 保存
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(existing_config, f, ensure_ascii=False, indent=2)


def load_role_configs(account_code: int, filepath: str = None) -> List[RoleConfig]:
    """从JSON文件加载角色配置"""
    if filepath is None:
        filepath = ROLE_CONFIG_FILE
    
    if not os.path.exists(filepath):
        return []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        key = 'account1' if account_code == 1 else 'account2'
        role_dicts = config.get(key, [])
        
        return [dict_to_role_config(d) for d in role_dicts]
    except Exception as e:
        print(f"加载角色配置失败: {e}")
        return []


def export_from_role_list(account_code: int = 1):
    """从role_list.py完整导出角色配置到JSON文件（覆盖现有配置）"""
    from dnf.stronger.role_list import get_role_config_list
    role_configs = get_role_config_list(account_code)
    print(f"从role_list.py获取账号{account_code}的角色配置，共{len(role_configs)}个角色")
    if role_configs:
        print(f"第一个角色: {role_configs[0].name}")
    save_role_configs(role_configs, account_code)
    print(f"已导出账号{account_code}的 {len(role_configs)} 个角色配置到 {ROLE_CONFIG_FILE}")
    return role_configs


def sync_role_configs(account_code: int = 1) -> tuple:
    """
    同步角色配置：只同步新增/删除的角色，保留已有角色的配置
    返回: (新增数量, 删除数量, 总数量)
    """
    from dnf.stronger.role_list import get_role_config_list
    
    # 获取role_list.py中的角色
    role_list_configs = get_role_config_list(account_code)
    role_list_names = {r.name for r in role_list_configs}
    role_list_dict = {r.name: r for r in role_list_configs}
    
    # 获取JSON中的角色
    json_configs = load_role_configs(account_code)
    json_names = {r.name for r in json_configs}
    json_dict = {r.name: r for r in json_configs}
    
    # 计算新增和删除的角色
    added_names = role_list_names - json_names
    removed_names = json_names - role_list_names
    
    # 如果JSON为空，直接完整导出
    if not json_configs:
        print(f"账号{account_code} JSON配置为空，执行完整导出...")
        export_from_role_list(account_code)
        return (len(role_list_configs), 0, len(role_list_configs))
    
    # 如果没有变化，不需要更新
    if not added_names and not removed_names:
        print(f"账号{account_code} 角色数量无变化，共{len(json_configs)}个角色")
        return (0, 0, len(json_configs))
    
    # 构建新的配置列表：保留现有配置 + 添加新角色
    new_configs = []
    
    # 按role_list.py中的顺序重新排列
    for role in role_list_configs:
        if role.name in json_names:
            # 保留JSON中的配置
            new_configs.append(json_dict[role.name])
        else:
            # 新增的角色，使用role_list.py中的配置
            new_configs.append(role)
    
    # 更新角色编号
    for i, role in enumerate(new_configs):
        role.no = i + 1
    
    # 保存
    save_role_configs(new_configs, account_code)
    
    print(f"账号{account_code} 同步完成: 新增{len(added_names)}个, 删除{len(removed_names)}个, 共{len(new_configs)}个角色")
    if added_names:
        print(f"  新增角色: {', '.join(added_names)}")
    if removed_names:
        print(f"  删除角色: {', '.join(removed_names)}")
    
    return (len(added_names), len(removed_names), len(new_configs))


def get_role_config_list_from_json(account_code: int) -> List[RoleConfig]:
    """
    从JSON文件加载角色配置
    如果JSON为空，则从role_list.py导出
    """
    role_configs = load_role_configs(account_code)
    
    if not role_configs:
        # JSON文件不存在或为空，从role_list.py导出
        print(f"JSON配置为空，从role_list.py导出账号{account_code}的角色配置...")
        role_configs = export_from_role_list(account_code)
    else:
        print(f"从JSON文件加载账号{account_code}的角色配置，共{len(role_configs)}个角色")
    
    return role_configs


# 测试代码
if __name__ == '__main__':
    # 导出账号1和账号2的角色配置
    print("导出账号1的角色配置...")
    export_from_role_list(1)
    print("导出账号2的角色配置...")
    export_from_role_list(2)
    print("完成！")
