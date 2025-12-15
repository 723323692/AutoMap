# BabyBus 项目维护文档

## 项目结构

```
BabyBus/
├── config.py                 # 全局配置（路径、音效）
├── dnf/                      # DNF脚本核心模块
│   ├── __init__.py          # 模块导出
│   ├── dnf_config.py        # 游戏按键配置
│   ├── mail_config.py       # 邮件配置（从环境变量读取）
│   ├── common.py            # 公共代码（键盘监听、检测分析）
│   ├── constants.py         # 常量定义（UI坐标、检测参数）
│   ├── abyss/               # 深渊模式
│   │   ├── main.py          # 深渊主脚本
│   │   ├── det_result.py    # 检测结果类
│   │   └── logger_config.py # 日志配置
│   └── stronger/            # 强化模式
│       ├── main.py          # 强化主脚本
│       ├── player.py        # 玩家操作函数
│       ├── skill_util.py    # 技能工具
│       ├── map_util.py      # 地图工具
│       ├── method.py        # 通用方法
│       ├── movement_helper.py # 移动辅助（统一移动逻辑）
│       ├── stuck_detector.py  # 卡死检测
│       ├── role_config.py   # 角色配置类
│       ├── role_loader.py   # 角色配置加载器
│       ├── role_list.py     # 角色列表
│       ├── path_finder.py   # 路径查找
│       └── roles/           # 角色JSON配置目录
├── utils/                    # 工具模块
│   ├── __init__.py          # 模块导出
│   ├── utilities.py         # 图像处理工具
│   ├── keyboard_utils.py    # 键盘操作
│   ├── mouse_utils.py       # 鼠标操作
│   ├── window_utils.py      # 窗口截图
│   ├── mail_sender.py       # 邮件发送
│   ├── monster_cluster.py   # 怪物聚类
│   ├── fixed_length_queue.py           # 固定长度队列
│   ├── keyboard_move_controller.py     # 移动控制器
│   └── custom_thread_pool_executor.py  # 自定义线程池
├── weights/                  # YOLO模型权重
│   ├── abyss.pt             # 深渊模式模型
│   └── stronger.pt          # 强化模式模型
├── assets/                   # 资源文件
│   ├── audio/               # 音效文件
│   └── img/                 # 图片模板
└── .env.example             # 环境变量示例
```

## 核心模块说明

### dnf/common.py

公共代码模块，包含深渊和强化模式共用的功能：

```python
# 键盘监听控制器
class KeyboardController:
    def __init__(self, mover: MovementController, logger)
    def set_window_info(handle: int, x: int, y: int)  # 设置窗口信息
    def on_press(key) -> Optional[bool]               # 按键回调
    def start_listener()                              # 启动监听

# 检测结果展示线程
class DisplayThread:
    def start()                    # 启动展示
    def stop()                     # 停止展示
    def put_frame(frame)           # 放入帧

# YOLO检测结果分析
def analyse_det_result_common(
    results,
    hero_height: int,
    img: Optional[np.ndarray],
    names: List[str],
    colors: List[Tuple[int, int, int]],
    show: bool = False,
    extra_classes: Optional[List[str]] = None
) -> dict

# 调试点绘制
def draw_debug_points(img, result_dict, hero_height)

# 颜色常量
COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW, COLOR_PURPLE
```

### dnf/constants.py

常量定义模块，集中管理UI坐标和检测参数：

```python
@dataclass(frozen=True)
class UICoordinates:
    DAILY_TASK_BTN: Tuple[int, int] = (767, 542)
    MENU_BTN: Tuple[int, int] = (832, 576)
    # ... 更多UI坐标

@dataclass(frozen=True)
class DetectionParams:
    ATTACK_X: int = 200
    ATTACK_Y: int = 80
    DOOR_HIT_X: int = 25
    DOOR_HIT_Y: int = 15
    # ... 更多检测参数

# 全局实例
UI = UICoordinates()
DETECTION = DetectionParams()
WINDOW = WindowSize()
```

### dnf/stronger/movement_helper.py

统一移动逻辑模块：

```python
# 计算移动方向
def calculate_move_direction(
    hero_pos: Tuple[float, float],
    target_pos: Tuple[float, float],
    y_threshold: float = 15,
    prefer_diagonal: bool = True
) -> Optional[str]

# 移动到目标
def move_to_target(
    mover: MovementController,
    hero_pos: Tuple[float, float],
    target_pos: Tuple[float, float],
    y_threshold: float = 15,
    move_mode: str = 'running',
    stop_immediately: bool = False
) -> Optional[str]

# 判断是否在范围内
def is_in_range(hero_pos, target_pos, range_x, range_y) -> bool

# 计算距离
def get_distance(pos1, pos2) -> float
```

### dnf/stronger/stuck_detector.py

卡死检测模块：

```python
class StuckDetector:
    def __init__(
        self,
        position_threshold: float = 30.0,  # 位置变化阈值
        time_threshold: float = 5.0,       # 时间阈值
        max_recovery_attempts: int = 3     # 最大恢复次数
    )
    def update(position, room) -> StuckState  # 更新检测状态
    def get_recovery_direction() -> Optional[str]  # 获取恢复方向
    def reset()  # 重置状态

class RoomStuckDetector:
    def __init__(self, time_threshold: float = 60.0)
    def update(room) -> bool  # 是否在同一房间停留过长
```

### dnf/stronger/role_loader.py

角色配置加载器：

```python
# 从JSON加载单个角色
def load_role_from_json(json_path: str) -> Optional[RoleConfig]

# 从目录加载所有角色
def load_roles_from_directory(dir_path: str) -> List[RoleConfig]

# 保存角色到JSON
def save_role_to_json(role: RoleConfig, json_path: str) -> bool
```

## 工具模块说明

### utils/utilities.py

图像处理工具：

```python
# 模板匹配
def match_template(image, template, threshold=0.8) -> List[BBox]
def match_template_one(image, template, threshold=0.8) -> List[BBox]
def match_template_with_confidence(image, template, threshold=0.8) -> List[BBoxWithConf]

# 图像比较（SSIM）
def compare_images(img1, img2) -> float

# 绘制边界框
def plot_one_box(xyxy, img, color=None, label=None, line_thickness=None)

# 颜色转换
def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]
```

### utils/keyboard_move_controller.py

移动控制器：

```python
class MovementController:
    def move(target_direction: str, move_mode: str = 'running')
    def move_stop_immediately(target_direction, move_mode='running', stop=False)
    def stop()
    def get_current_direction() -> Optional[str]

# 支持方向: UP, DOWN, LEFT, RIGHT, RIGHT_UP, RIGHT_DOWN, LEFT_UP, LEFT_DOWN
# 支持模式: walking, running
```

### utils/mail_sender.py

邮件发送器：

```python
class EmailSender:
    def __init__(self, config: Dict[str, Any])
    def send_email(subject, content, receiver, retry_count=2) -> bool
    def send_email_with_images(subject, content, receiver, image_paths=None, retry_count=2) -> bool
```

### utils/custom_thread_pool_executor.py

自定义线程池：

```python
# 单任务线程池（同时只允许一个任务）
class SingleTaskThreadPool:
    def submit(func, *args, **kwargs) -> Optional[Future]
    def shutdown(wait=True)

# 有限任务线程池
class LimitedTaskThreadPool:
    def __init__(self, max_workers: int)
    def submit(func, *args, **kwargs) -> Optional[Future]

# 支持上下文管理器
with LimitedTaskThreadPool(max_workers=2) as pool:
    pool.submit(worker, arg)
```

### utils/fixed_length_queue.py

固定长度队列：

```python
class FixedLengthQueue(Generic[T]):
    def __init__(self, max_length: int = 5)
    def enqueue(item: T)
    def dequeue() -> Optional[T]
    def peek() -> Optional[T]
    def coords_is_stable(threshold=15, window_size=20) -> bool  # 检测坐标稳定性
    def room_is_same(min_size=20) -> bool  # 检测房间是否相同
```

## 配置管理

### 环境变量配置

敏感信息通过环境变量配置，支持 `.env` 文件自动加载：

```bash
# .env 文件
DNF_MAIL_SENDER=your_email@qq.com
DNF_MAIL_PASSWORD=your_authorization_code
DNF_SMTP_SERVER=smtp.qq.com
DNF_SMTP_PORT=465
DNF_MAIL_RECEIVER=receiver@qq.com
```

### 角色JSON配置

角色配置文件放置于 `dnf/stronger/roles/` 目录：

```json
{
    "name": "角色名称",
    "no": 1,
    "height": 50,
    "fatigue_all": 188,
    "fatigue_reserved": 30,
    "attack_center_x": 0,
    "buff_effective": false,
    "white_map_level": 2,
    "buffs": [["q"], ["w", "e"]],
    "candidate_hotkeys": ["a", "s", "d", "f"],
    "custom_priority_skills": [],
    "powerful_skills": [
        {
            "name": "大招",
            "hot_key": "space",
            "command": [],
            "concurrent": false,
            "cd": 30,
            "animation_time": 2.0
        }
    ]
}
```

### 运行时参数

在 `main.py` 文件顶部配置：

```python
show = False                    # 是否显示检测结果
quit_game_after_finish = False  # 完成后退出游戏
first_role_no = 1               # 起始角色编号
last_role_no = 16               # 结束角色编号
game_mode = 3                   # 游戏模式
```

### 神秘商店购买配置

在 `main.py` 中配置购买选项：

```python
# 买罐子
buy_tank_type = 0      # 0不买，1传说，2史诗，3史诗+传说

# 买铃铛
buy_bell_ticket = 0    # 0不买，1粉，2传说，3粉+传说

# 买闪闪明
buy_shanshanming = 2   # 0不买，1粉，2传说，3粉+传说

# 买催化剂
buy_catalyst = 0       # 0不买，1传说，2史诗，3太初，4传说+史诗，5史诗+太初，6传说+太初，7全部
```

## 神秘商店购买模块

### dnf/stronger/player.py 购买函数

```python
# 购买门票
def buy_from_mystery_shop(full_screen, x, y)

# 购买罐子
def buy_tank_from_mystery_shop(full_screen, x, y, buy_type: int = 2)
# buy_type: 0不买，1传说，2史诗，3史诗+传说

# 购买铃铛
def buy_bell_from_mystery_shop(full_screen, x, y, buy_type: int = 2)
# buy_type: 0不买，1粉，2传说，3粉+传说

# 购买闪闪明
def buy_shanshanming_from_mystery_shop(full_screen, x, y, buy_type: int = 2)
# buy_type: 0不买，1粉，2传说，3粉+传说

# 购买催化剂
def buy_catalyst_from_mystery_shop(full_screen, x, y, buy_type: int = 0)
# buy_type: 0不买，1传说，2史诗，3太初，4传说+史诗，5史诗+太初，6传说+太初，7全部

# 统一处理神秘商店
def process_mystery_shop(img, x, y, buy_tank_type, buy_bell_ticket, buy_shanshanming, buy_catalyst=0)
```

### 添加新物品购买

1. 准备模板图片，放到 `assets/img/` 目录
2. 在 `player.py` 中添加购买函数：

```python
def buy_new_item_from_mystery_shop(full_screen, x, y, buy_type: int = 0):
    """
    神秘商店购买新物品
    buy_type: 0不买，1类型A，2类型B，...
    """
    if buy_type == 0:
        return
    
    logger.info(f'检查神秘商店新物品，购买类型: {buy_type}')
    gray_screenshot = cv2.cvtColor(full_screen, cv2.COLOR_BGRA2GRAY)
    
    # 加载模板
    template = cv2.imread(
        os.path.normpath(f'{config_.project_base_path}/assets/img/new_item.png'),
        cv2.IMREAD_COLOR
    )
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    # 模板匹配
    matches = match_template_with_confidence(gray_screenshot, template_gray, threshold=0.85)
    
    # 点击购买
    for top_left, bottom_right, conf in matches:
        x1, y1 = top_left
        x2, y2 = bottom_right
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        
        mu.do_move_to(x + center_x, y + center_y)
        time.sleep(0.2)
        mu.do_click(Button.left)
        time.sleep(0.2)
        mu.do_click(Button.left)  # 双击确认
        time.sleep(0.2)
```

3. 在 `process_mystery_shop` 中添加调用
4. 在 `main.py` 中添加配置变量

### 模板图片要求

| 要求 | 说明 |
|------|------|
| 格式 | PNG |
| 尺寸 | 约 26x26 到 40x40 像素 |
| 内容 | 物品图标特征部分，不含文字 |
| 命名 | 小写字母+下划线，如 `catalyst_epic.png` |

### 现有模板图片

```
assets/img/
├── ticket.png              # 门票
├── tank_legend.png         # 罐子
├── bell26.png              # 铃铛
├── shanshanming26.png      # 闪闪明（粉）
├── shanshanming26-2.png    # 闪闪明（传说）
├── shanshanming26-3.png    # 闪闪明（史诗）
├── catalyst_legend.png     # 催化剂（传说）- 需准备
├── catalyst_epic.png       # 催化剂（史诗）- 需准备
└── catalyst_taichu.png     # 催化剂（太初）- 需准备
```

## 开发规范

### 类型提示

所有新代码应添加类型提示：

```python
def match_template(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8
) -> List[Tuple[Point, Point]]:
    ...
```

### 资源管理

使用上下文管理器管理资源：

```python
with WindowCapture(hwnd) as capturer:
    img = capturer.capture()
# 自动释放资源

with LimitedTaskThreadPool(max_workers=2) as pool:
    pool.submit(task)
# 自动关闭线程池
```

### 异常处理

使用具体的异常类型：

```python
try:
    smtp_obj.login(self.sender, self.password)
except smtplib.SMTPAuthenticationError as e:
    logger.error(f"认证失败: {e}")
    return False
except smtplib.SMTPResponseException as e:
    logger.warning(f"SMTP错误: {e.smtp_code}")
```

### 常量使用

使用 `constants.py` 中定义的常量：

```python
from dnf.constants import UI, DETECTION

# 使用UI坐标
mu.do_move_to(x + UI.DAILY_TASK_BTN[0], y + UI.DAILY_TASK_BTN[1])

# 使用检测参数
if distance < DETECTION.ATTACK_X:
    ...
```

### 移动逻辑

使用统一的移动辅助函数：

```python
from dnf.stronger.movement_helper import move_to_target, is_in_range

# 移动到目标
move_to_target(mover, hero_pos, target_pos, y_threshold=15)

# 判断是否在攻击范围
if is_in_range(hero_pos, monster_pos, DETECTION.ATTACK_X, DETECTION.ATTACK_Y):
    attack()
```

## 常见问题

### Q: 邮件发送失败
1. 检查 `.env` 文件是否存在且配置正确
2. 确认使用的是邮箱授权码而非登录密码
3. 检查网络连接和SMTP服务器可用性

### Q: 窗口截图黑屏
1. 确保游戏窗口化运行
2. 尝试切换 `use_printwindow` 参数
3. 检查是否有其他程序遮挡

### Q: 角色识别不准
1. 调整 `role.height` 参数
2. 检查模型权重文件是否正确
3. 调整检测置信度阈值

### Q: 角色卡住不动
1. 脚本内置 `StuckDetector` 会自动检测和恢复
2. 可调整 `position_threshold` 和 `time_threshold` 参数
3. 检查 `movement_helper.py` 中的移动逻辑

### Q: 过门来回蹭
1. 增大 `DETECTION.DOOR_HIT_X` 和 `DOOR_HIT_Y` 参数
2. 使用 `move_to_target` 的 `stop_immediately` 参数

### Q: 神秘商店物品识别不到
1. 检查 `assets/img/` 下对应模板图片是否存在
2. 确保图片清晰，只包含物品图标
3. 调整模板匹配阈值（默认0.85，可降低到0.8）
4. 检查图片尺寸是否合适（建议26x26到40x40）

## 更新日志

### 2024-12-12
- 新增催化剂购买功能（支持传说/史诗/太初三种品级）
- 重构README文档，移除uv改用conda环境
- 更新MAINTENANCE文档，添加神秘商店购买模块说明
- 优化过门逻辑，增大命中范围避免来回蹭
- 新增 `movement_helper.py` 统一移动逻辑
- 重构打怪和拾取移动逻辑，使用统一的 `move_to_target` 函数
- 新增 `stuck_detector.py` 卡死检测和自动恢复机制
- 新增 `role_loader.py` 支持从JSON文件加载角色配置
- 修复 `WindowCapture` 默认使用 BitBlt 避免闪屏
- 修复 `path_finder.py` 索引越界问题
- 修复 `map_util.py` 返回值为 None 的问题
- 修复 `compare_images` 空值检查

### 2024-12-11
- 移除硬编码密码，改用环境变量配置
- 提取公共代码到 `dnf/common.py`
- 添加常量定义模块 `dnf/constants.py`
- 修复文件命名错误 `excutor` → `executor`
- 修复废弃API `np.fromstring` → `np.frombuffer`
- 添加资源管理器支持（上下文管理器）
- 为所有工具模块添加类型提示
- 改进异常处理和日志记录
