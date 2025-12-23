# BabyBus

Dungeons and Baby Bus - DNF自动化脚本

## 功能特性

- 🎮 支持妖气追踪、白图、深渊等多种模式
- 🤖 基于YOLOv8的目标检测
- 🔄 自动角色切换和任务执行
- 📧 邮件通知功能（超时提醒、任务完成通知）
- 🛡️ 卡死检测和自动恢复
- 🛒 神秘商店自动购买
- ⚙️ GUI图形界面配置
- 🎯 热键控制（F10启动/Delete暂停/End停止）
- 🔐 卡密验证系统

## 环境要求

- Python >= 3.10
- Windows 10/11
- NVIDIA显卡（推荐，支持CUDA加速）
- 游戏窗口化运行（1067x600）

## 快速开始

### 方式一：自动安装（推荐）

1. 双击运行 `install.bat`
2. 选择CUDA版本（根据显卡驱动选择）
3. 等待安装完成
4. 双击 `start.gui.bat` 启动

### 方式二：手动安装

#### 1. 安装 Miniconda

下载地址：https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe

#### 2. 创建虚拟环境

```bash
conda create -n yolov8 python=3.10 -y
conda activate yolov8
```

#### 3. 安装PyTorch（GPU版本）

```bash
# CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 或 CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

#### 4. 安装其他依赖

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 5. 检查环境

```bash
python check_env.py
```

### 启动程序

双击 `start.gui.bat` 启动图形界面。

## 使用说明

### 登录验证

首次启动需要输入卡密进行验证：
1. 在登录窗口输入卡密
2. 勾选"记住"可保存卡密，下次自动填充
3. 点击"登录"进行验证
4. 验证成功后显示剩余时间

**解绑功能**：
- 如需更换设备，可点击"解绑"按钮
- 每次解绑扣除8小时使用时间
- 最多可解绑3次

### 热键控制

| 热键 | 功能 |
|------|------|
| F10 | 启动脚本 |
| Delete | 暂停/继续 |
| End | 停止脚本 |

### 游戏模式

- **妖气追踪**：自动刷妖气追踪地图
- **白图**：自动刷跌宕群岛
- **每日1+1**：自动完成每日1+1任务
- **深渊**：自动刷深渊

### 角色配置

在GUI中可以配置：
- 起始/结束角色编号
- 跳过指定角色
- 疲劳值预留
- 购买设置（罐子、铃铛、催化剂等）

### 执行完成后操作

- **退出游戏**：脚本完成后自动退出游戏
- **关闭电脑**：脚本完成后自动关机（需管理员权限）

## 配置说明

### 邮件通知配置

创建 `.env` 文件（参考 `.env.example`）：

```env
DNF_MAIL_SENDER=your_email@qq.com
DNF_MAIL_PASSWORD=your_authorization_code
DNF_MAIL_RECEIVER=receiver@qq.com
DNF_SMTP_SERVER=smtp.qq.com
DNF_SMTP_PORT=465
```

### 神秘商店购买配置

在GUI的"购买设置"中配置，或在代码中设置：

```python
buy_tank_type = 0      # 罐子: 0不买，1传说，2史诗，3全部
buy_bell_ticket = 0    # 铃铛: 0不买，1粉，2传说，3全部
buy_shanshanming = 2   # 闪闪明: 0不买，1粉，2传说，3全部
buy_catalyst = 7       # 催化剂: 0不买，1传说，2史诗，3太初，7全部
```

## 项目结构

```
BabyBus/
├── gui_app.py           # GUI主程序
├── start.gui.bat        # 启动脚本
├── install.bat          # 安装脚本
├── check_env.py         # 环境检查脚本
├── requirements.txt     # 依赖列表
├── dnf/                 # 核心模块
│   ├── stronger/        # 妖气追踪/白图模式
│   ├── abyss/           # 深渊模式
│   └── dnf_config.py    # 游戏配置
├── utils/               # 工具模块
│   ├── window_utils.py  # 窗口截图
│   ├── keyboard_utils.py # 键盘操作
│   ├── login_dialog.py  # 登录对话框
│   ├── auth.py          # 卡密验证
│   └── mail_sender.py   # 邮件发送
├── weights/             # YOLO模型权重
└── assets/              # 资源文件
```

## 常见问题

**Q: 启动报错"未找到Python环境"**
- 运行 `python check_env.py` 检查环境
- 确保Python >= 3.10

**Q: CUDA不可用**
- 检查NVIDIA驱动是否安装
- 确认安装了GPU版本的PyTorch
- 运行 `python -c "import torch; print(torch.cuda.is_available())"`

**Q: 邮件发送失败**
- 检查 `.env` 配置是否正确
- 确认使用邮箱授权码而非登录密码

**Q: 窗口截图黑屏**
- 确保游戏窗口化运行
- 窗口大小设置为1067x600

**Q: 角色卡住不动**
- 脚本内置卡死检测，会自动尝试恢复
- 超过60秒会尝试返回上一地图
- 超过100秒会发送邮件提醒

**Q: 卡密验证失败**
- 检查网络连接是否正常
- 确认卡密是否正确
- 如已绑定其他设备，需先解绑

**Q: 解绑次数用完怎么办**
- 联系管理员重置解绑次数
- 或购买新卡密

## 许可证

本项目采用 [GNU AGPL](https://www.gnu.org/licenses/agpl-3.0.html) 许可证，附加禁止商业使用条款。

**重要限制：**
- 必须保留原作者版权声明
- 禁止商业用途（包括销售、分发或盈利）
- 商业授权请联系作者

## 作者

[冷兔](https://github.com/723323692)
- Email: 723323692@qq.com / zzs1999bd@163.com

[甘霖](https://github.com/nianling)
- Email: wemean66@gmail.com / nianlingbeige@163.com

完整许可证见 [LICENSE](LICENSE) 文件。
