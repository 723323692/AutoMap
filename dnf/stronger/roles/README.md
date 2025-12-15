# 角色配置目录

此目录用于存放角色配置文件。

## 配置文件格式

每个角色配置为一个 JSON 文件，格式如下：

```json
{
    "name": "角色名称",
    "no": 1,
    "height": 180,
    "fatigue_all": 188,
    "fatigue_reserved": 30,
    "attack_center_x": 0,
    "buff_effective": false,
    "white_map_level": 2,
    "buffs": [],
    "candidate_hotkeys": ["q", "w", "e", "r", "t", "a", "s", "d", "f", "g", "h"],
    "custom_priority_skills": [],
    "powerful_skills": []
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 角色名称 |
| no | int | 角色序号 |
| height | int | 角色高度偏移（用于检测） |
| fatigue_all | int | 总疲劳值 |
| fatigue_reserved | int | 保留疲劳值 |
| attack_center_x | int | 攻击中心X偏移 |
| buff_effective | bool | 是否需要上buff |
| white_map_level | int | 白图等级 |
| buffs | array | buff技能组合列表 |
| candidate_hotkeys | array | 候选技能快捷键 |
| custom_priority_skills | array | 自定义优先技能 |
| powerful_skills | array | 强力技能列表 |

## 技能配置格式

技能可以是简单的快捷键字符串，也可以是复杂的技能对象：

```json
{
    "name": "技能名称",
    "hot_key": "q",
    "command": ["up", "up", "space"],
    "cd": 10.0,
    "animation_time": 0.7
}
```
