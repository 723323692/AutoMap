# BabyBus

Dungeons and Baby Bus - DNF自动化脚本

## 功能特性

- 🎮 支持深渊模式和强化模式
- 🤖 基于YOLO的目标检测
- 🔄 自动角色切换和任务执行
- 📧 邮件通知功能
- 🛡️ 卡死检测和自动恢复
- 🛒 神秘商店自动购买
- ⚙️ JSON配置支持

## 环境要求

- Python 3.10.x
- Windows 10/11
- 游戏窗口化运行

## 快速开始

### 1. 安装 Miniconda

如果没有安装 Conda，请先下载安装 Miniconda：
- 下载地址：https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
- 安装时勾选"Add to PATH"选项

### 2. 创建虚拟环境

```bash
# 创建 yolov8 环境
conda create -n yolov8 python=3.10 -y

# 激活环境
conda activate yolov8
```

### 3. 安装依赖

```bash
# 先升级 pip（重要！）
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 使用清华镜像源安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 PyQt5（GUI需要）
pip install PyQt5 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 修复 OpenCV（如有问题）

```bash
pip uninstall opencv-python-headless opencv-python -y
pip install opencv-python -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 5. 启动程序

双击 `start.gui.bat` 启动图形界面。

## 配置说明

### 邮件通知配置

创建 `.env` 文件：

```bash
cp .env.example .env
# 编辑 .env 文件填入配置
```

或设置系统环境变量：

```powershell
$env:DNF_MAIL_SENDER = "your_email@qq.com"
$env:DNF_MAIL_PASSWORD = "your_authorization_code"
$env:DNF_MAIL_RECEIVER = "receiver@qq.com"
```

环境变量说明：
| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DNF_MAIL_SENDER` | 发件人邮箱 | - |
| `DNF_MAIL_PASSWORD` | 邮箱授权码 | - |
| `DNF_MAIL_RECEIVER` | 收件人邮箱 | - |
| `DNF_SMTP_SERVER` | SMTP服务器 | smtp.qq.com |
| `DNF_SMTP_PORT` | SMTP端口 | 465 |

### 神秘商店购买配置

在 `main.py` 中配置购买选项：

```python
# 买罐子: 0不买，1传说，2史诗，3史诗+传说
buy_tank_type = 0

# 买铃铛: 0不买，1粉，2传说，3粉+传说
buy_bell_ticket = 0

# 买闪闪明: 0不买，1粉，2传说，3粉+传说
buy_shanshanming = 2

# 买催化剂: 0不买，1传说，2史诗，3太初，4传说+史诗，5史诗+太初，6传说+太初，7全部
buy_catalyst = 0
```

### 角色配置

支持JSON文件配置角色，放置于 `dnf/stronger/roles/` 目录：

```json
{
  "name": "角色名",
  "height": 50,
  "skills": ["a", "s", "d", "f"],
  "buff_skills": ["q", "w"]
}
```

## 运行

### GUI模式（推荐）

双击 `start.gui.bat` 启动图形界面，支持：
- 可视化配置参数
- 实时日志显示
- 热键控制（F10启动/Delete暂停/End停止）

### 命令行模式

```powershell
# 激活环境
conda activate yolov8

# 启动GUI
python gui_app.py

# 深渊模式
.\start.abyss.bat

# 强化模式
.\start.stronger.bat
```

## 项目结构

```
BabyBus/
├── dnf/                      # 核心模块
│   ├── common.py            # 公共代码
│   ├── constants.py         # 常量定义
│   ├── abyss/               # 深渊模式
│   └── stronger/            # 强化模式
│       ├── movement_helper.py   # 移动辅助
│       ├── stuck_detector.py    # 卡死检测
│       └── role_loader.py       # 配置加载
├── utils/                    # 工具模块
│   ├── utilities.py         # 图像处理
│   ├── keyboard_utils.py    # 键盘操作
│   ├── window_utils.py      # 窗口截图
│   └── mail_sender.py       # 邮件发送
├── weights/                  # YOLO模型
└── assets/                   # 资源文件
    └── img/                 # 模板图片
```

详细文档请参阅 [MAINTENANCE.md](MAINTENANCE.md)

## 常见问题

**Q: 邮件发送失败**
- 检查 `.env` 配置是否正确
- 确认使用邮箱授权码而非登录密码

**Q: 窗口截图黑屏**
- 确保游戏窗口化运行
- 检查是否有其他程序遮挡

**Q: 角色卡住不动**
- 脚本内置卡死检测，会自动尝试恢复
- 可调整 `movement_helper.py` 中的移动参数

**Q: 神秘商店物品识别不到**
- 检查 `assets/img/` 下对应模板图片是否存在
- 调整模板匹配阈值（默认0.85）

## 许可证

本项目采用 [GNU AGPL](https://www.gnu.org/licenses/agpl-3.0.html) 许可证，附加禁止商业使用条款。

**重要限制：**
- 必须保留原作者版权声明
- 禁止商业用途（包括销售、分发或盈利）
- 商业授权请联系作者

## 作者

[冷兔](https://github.com/723323692)

- 723323692@qq.com /  zzs1999bd@163.com
- GitHub: https://github.com/723323692

完整许可证见 [LICENSE](LICENSE) 文件。
