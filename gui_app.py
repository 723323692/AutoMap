# -*- coding:utf-8 -*-
"""
DNF自动化脚本 - PyQt5 图形界面
支持按钮和热键控制，日志输出到GUI
"""

__author__ = "723323692"
__version__ = '1.0'

import os
import sys
import json
import threading
import winsound
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QGroupBox, QLabel, QSpinBox, QComboBox, QCheckBox,
    QPushButton, QTextEdit, QRadioButton, QButtonGroup, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QLineEdit,
    QFormLayout, QDialogButtonBox, QScrollArea, QProgressDialog,
    QListWidget, QListWidgetItem, QDoubleSpinBox, QInputDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QTime
from PyQt5.QtGui import QFont, QTextCursor, QIcon, QPalette, QLinearGradient, QColor, QBrush

# 配置文件路径
ROLE_CONFIG_FILE = os.path.join(PROJECT_ROOT, 'role_config.json')
GUI_CONFIG_FILE = os.path.join(PROJECT_ROOT, 'gui_config.json')


class NoScrollSpinBox(QSpinBox):
    """禁用滚轮的SpinBox"""
    def wheelEvent(self, event):
        event.ignore()


class NoScrollComboBox(QComboBox):
    """禁用滚轮的ComboBox"""
    def wheelEvent(self, event):
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """禁用滚轮的DoubleSpinBox"""
    def wheelEvent(self, event):
        event.ignore()





class StdoutRedirector(QObject):
    """标准输出重定向器"""
    text_written = pyqtSignal(str)
    
    def write(self, text):
        if text and text.strip():
            self.text_written.emit(str(text))
    
    def flush(self):
        pass


class PreloadWorker(QThread):
    """模块预加载线程"""
    progress_signal = pyqtSignal(int)  # percent
    finished_signal = pyqtSignal(bool, str)  # success, message
    
    def run(self):
        import time as _time
        start_time = _time.time()
        
        try:
            self.progress_signal.emit(0)
            import torch
            
            self.progress_signal.emit(20)
            import cv2
            
            self.progress_signal.emit(40)
            import numpy
            
            self.progress_signal.emit(60)
            from ultralytics import YOLO
            
            self.progress_signal.emit(80)
            stronger_dir = os.path.join(PROJECT_ROOT, 'dnf', 'stronger')
            if stronger_dir not in sys.path:
                sys.path.insert(0, stronger_dir)
            if PROJECT_ROOT not in sys.path:
                sys.path.insert(0, PROJECT_ROOT)
            import dnf.stronger.main
            
            elapsed = _time.time() - start_time
            self.finished_signal.emit(True, f"加载完成，耗时 {elapsed:.1f} 秒")
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.finished_signal.emit(False, f"加载失败: {e}")


class HotkeyListener(QThread):
    """全局热键监听线程"""
    start_signal = pyqtSignal()
    stop_signal = pyqtSignal()
    pause_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._running = True
        self._last_trigger_time = {}  # 防抖动：记录每个热键的最后触发时间
        self._debounce_interval = 0.3  # 防抖动间隔（秒），缩短到0.3秒
    
    def _debounced_emit(self, key, signal):
        """带防抖动的信号发射"""
        import time
        current_time = time.time()
        last_time = self._last_trigger_time.get(key, 0)
        if current_time - last_time >= self._debounce_interval:
            self._last_trigger_time[key] = current_time
            signal.emit()
    
    def run(self):
        try:
            import keyboard
            # 只注册F10启动热键，End和Delete由脚本内部处理
            keyboard.add_hotkey('f10', lambda: self._debounced_emit('f10', self.start_signal))
            # End和Delete热键由main.py中的start_keyboard_listener处理，避免重复触发
            # keyboard.add_hotkey('end', lambda: self._debounced_emit('end', self.stop_signal))
            # keyboard.add_hotkey('delete', lambda: self._debounced_emit('delete', self.pause_signal))
            
            while self._running:
                self.msleep(50)  # 缩短检查间隔，提高响应速度
        except Exception as e:
            print(f"热键监听错误: {e}")
    
    def stop(self):
        self._running = False
        try:
            import keyboard
            keyboard.unhook_all()
        except:
            pass


class ScriptWorker(QThread):
    """脚本工作线程"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, script_type, config):
        super().__init__()
        self.script_type = script_type
        self.config = config
        self._stop_requested = False
        self._redirector = None
        self._stronger_main = None
        self._abyss_main = None
    
    def request_stop(self):
        """请求停止 - 设置脚本的停止标志"""
        self._stop_requested = True
        self.log("正在设置停止标志...")
        
        # 直接设置脚本模块的停止标志
        if self._stronger_main:
            self._stronger_main.stop_be_pressed = True
            # 确保暂停事件被设置，让脚本能继续执行到检查停止标志的地方
            if hasattr(self._stronger_main, 'pause_event'):
                self._stronger_main.pause_event.set()
            self.log("已设置stronger模块停止标志")
        if self._abyss_main:
            self._abyss_main.stop_be_pressed = True
            if hasattr(self._abyss_main, 'pause_event'):
                self._abyss_main.pause_event.set()
            self.log("已设置abyss模块停止标志")
        
        # 同时尝试通过sys.modules设置
        try:
            if 'dnf.stronger.main' in sys.modules:
                mod = sys.modules['dnf.stronger.main']
                mod.stop_be_pressed = True
                if hasattr(mod, 'pause_event'):
                    mod.pause_event.set()
            if 'dnf.abyss.main' in sys.modules:
                mod = sys.modules['dnf.abyss.main']
                mod.stop_be_pressed = True
                if hasattr(mod, 'pause_event'):
                    mod.pause_event.set()
        except:
            pass
    
    def request_pause(self):
        """请求暂停/继续"""
        try:
            if self._stronger_main and hasattr(self._stronger_main, 'pause_event'):
                if self._stronger_main.pause_event.is_set():
                    self._stronger_main.pause_event.clear()
                    self.log("已暂停stronger脚本")
                    return True  # 已暂停
                else:
                    self._stronger_main.pause_event.set()
                    self.log("已继续stronger脚本")
                    return False  # 已继续
            if self._abyss_main and hasattr(self._abyss_main, 'pause_event'):
                if self._abyss_main.pause_event.is_set():
                    self._abyss_main.pause_event.clear()
                    self.log("已暂停abyss脚本")
                    return True
                else:
                    self._abyss_main.pause_event.set()
                    self.log("已继续abyss脚本")
                    return False
            
            # 通过sys.modules尝试
            for mod_name in ['dnf.stronger.main', 'dnf.abyss.main']:
                if mod_name in sys.modules:
                    mod = sys.modules[mod_name]
                    if hasattr(mod, 'pause_event'):
                        if mod.pause_event.is_set():
                            mod.pause_event.clear()
                            return True
                        else:
                            mod.pause_event.set()
                            return False
        except Exception as e:
            self.log(f"暂停操作失败: {e}")
        return None
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_signal.emit(f"[{timestamp}] {msg}")
    
    def _start_auth_checker(self):
        """启动授权检查线程"""
        import time
        from utils.auth import heartbeat, get_verified_card
        
        def check_loop():
            while not self._stop_requested:
                time.sleep(60)  # 每60秒检查一次
                if self._stop_requested:
                    break
                card_key = get_verified_card()
                if card_key:
                    success, msg = heartbeat(card_key)
                    if not success:
                        self.log(f"[授权] 验证失败: {msg}，脚本将停止")
                        self.request_stop()
                        break
        
        checker = threading.Thread(target=check_loop, daemon=True)
        checker.start()
    
    def run(self):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        self._redirector = StdoutRedirector()
        self._redirector.text_written.connect(self._on_text)
        sys.stdout = self._redirector
        sys.stderr = self._redirector
        
        try:
            # 启动授权检查线程
            self._start_auth_checker()
            
            # 先设置loguru重定向
            self._setup_loguru()
            self.log(f"开始执行 {self.script_type} 脚本...")
            
            if self.script_type == "stronger":
                self._run_stronger()
            elif self.script_type == "abyss":
                self._run_abyss()
        except Exception as e:
            self.log(f"脚本执行出错: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            # 恢复标准输出
            sys.stdout, sys.stderr = old_stdout, old_stderr
            # 恢复loguru默认配置
            try:
                from loguru import logger
                logger.remove()
                logger.add(sys.stderr, level="DEBUG")
            except:
                pass
            self.finished_signal.emit()
    
    def _on_text(self, text):
        """处理文本输出"""
        if text.strip():
            self.log_signal.emit(text.strip())
    
    def _setup_loguru(self):
        """设置loguru日志重定向到GUI，同时保留文件日志"""
        try:
            from loguru import logger
            # 只添加GUI sink，不移除现有的文件日志handler
            # GUI只显示INFO及以上级别，文件保存所有级别
            logger.add(
                self._loguru_sink,
                format="{time:HH:mm:ss} | {level} | {message}",
                level="INFO",  # GUI只显示INFO及以上
                colorize=False,
                backtrace=False,
                diagnose=False
            )
            self.log("loguru日志已重定向到GUI")
        except Exception as e:
            self.log(f"设置loguru失败: {e}")
    
    def _loguru_sink(self, message):
        """loguru输出接收器"""
        try:
            msg = str(message).strip()
            if msg:
                self.log_signal.emit(msg)
        except:
            pass
    
    def _run_stronger(self):
        self.log("启动妖气追踪/白图脚本...")
        self.log(f"配置参数: 模式={self.config['game_mode']}, 账号={self.config.get('account_name', self.config['account_code'])}, 起始角色={self.config['first_role']}, 结束角色={self.config['last_role']}")
        
        stronger_dir = os.path.join(PROJECT_ROOT, 'dnf', 'stronger')
        original_dir = os.getcwd()
        
        try:
            os.chdir(stronger_dir)
            if stronger_dir not in sys.path:
                sys.path.insert(0, stronger_dir)
            if PROJECT_ROOT not in sys.path:
                sys.path.insert(0, PROJECT_ROOT)
            
            for key in list(sys.modules.keys()):
                if 'dnf.stronger' in key or key in ['map_util', 'skill_util', 'logger_config']:
                    del sys.modules[key]
            
            import dnf.stronger.main as stronger_main
            # 重置停止标志
            stronger_main.stop_be_pressed = False
            stronger_main.use_json_config = True  # GUI模式使用JSON配置
            stronger_main.game_mode = self.config['game_mode']
            # account_code: 'account1' -> 1, 'account2' -> 2
            account_str = self.config['account_code']
            stronger_main.account_code = int(account_str.replace('account', '')) if isinstance(account_str, str) else account_str
            # 传递账号显示名称
            stronger_main.account_name = self.config.get('account_name', '')
            stronger_main.first_role_no = self.config['first_role']
            stronger_main.last_role_no = self.config['last_role']
            # 跳过角色设置
            stronger_main.break_role = self.config.get('break_role', False)
            stronger_main.break_role_no = self.config.get('break_role_no', [])
            self.log(f"已设置脚本参数: first_role_no={stronger_main.first_role_no}, last_role_no={stronger_main.last_role_no}, break_role={stronger_main.break_role}, break_role_no={stronger_main.break_role_no}")
            stronger_main.show = self.config['show_detection']
            stronger_main.enable_uniform_pl = self.config.get('enable_uniform_pl', False)
            stronger_main.uniform_default_fatigue_reserved = self.config.get('fatigue_reserved', 0)
            # 购买设置
            stronger_main.buy_tank_type = self.config.get('buy_tank', 0)
            stronger_main.buy_bell_ticket = self.config.get('buy_bell', 0)
            stronger_main.buy_shanshanming = self.config.get('buy_ssm', 2)
            stronger_main.buy_catalyst = self.config.get('buy_catalyst', 7)
            # 执行完成后操作
            stronger_main.quit_game_after_finish = self.config.get('quit_game_after_finish', False)
            stronger_main.shutdown_pc_after_finish = self.config.get('shutdown_after_finish', False)
            
            # 保存模块引用用于停止
            self._stronger_main = stronger_main
            
            # 启动脚本内部的热键监听（End停止、Delete暂停）
            listener = threading.Thread(target=stronger_main.start_keyboard_listener, daemon=True)
            listener.start()
            stronger_main.main_script()
            self.log("脚本执行完成")
        finally:
            os.chdir(original_dir)
    
    def _run_abyss(self):
        self.log("启动深渊脚本...")
        account_type = "自己账号" if self.config.get('account_code', 1) == 1 else "五子账号"
        self.log(f"账号: {account_type}, 角色: {self.config['first_role']}-{self.config['last_role']}")
        
        abyss_dir = os.path.join(PROJECT_ROOT, 'dnf', 'abyss')
        original_dir = os.getcwd()
        
        try:
            os.chdir(abyss_dir)
            if abyss_dir not in sys.path:
                sys.path.insert(0, abyss_dir)
            if PROJECT_ROOT not in sys.path:
                sys.path.insert(0, PROJECT_ROOT)
            
            for key in list(sys.modules.keys()):
                if 'dnf.abyss' in key:
                    del sys.modules[key]
            
            import dnf.abyss.main as abyss_main
            # 重置停止标志
            abyss_main.stop_be_pressed = False
            # 设置账号类型: 'account1' -> 1, 'account2' -> 2
            account_str = self.config.get('account_code', 'account1')
            abyss_main.account_code = int(account_str.replace('account', '')) if isinstance(account_str, str) else account_str
            # 传递账号显示名称
            abyss_main.account_name = self.config.get('account_name', '')
            abyss_main.first_role_no = self.config['first_role']
            abyss_main.last_role_no = self.config['last_role']
            abyss_main.show = self.config['show_detection']
            abyss_main.enable_uniform_pl = self.config.get('enable_uniform_pl', False)
            abyss_main.uniform_default_fatigue_reserved = self.config.get('fatigue_reserved', 17)
            # 跳过角色设置
            abyss_main.break_role = self.config.get('break_role', False)
            abyss_main.break_role_no = self.config.get('break_role_no', [])
            # 购买设置
            abyss_main.buy_tank_type = self.config.get('buy_tank', 0)
            abyss_main.buy_bell_ticket = self.config.get('buy_bell', 2)
            abyss_main.buy_shanshanming = self.config.get('buy_ssm', 2)
            abyss_main.buy_catalyst = self.config.get('buy_catalyst', 7)
            self.log(f"已设置脚本参数: first_role_no={abyss_main.first_role_no}, last_role_no={abyss_main.last_role_no}, break_role={abyss_main.break_role}, break_role_no={abyss_main.break_role_no}")
            # 执行完成后操作
            abyss_main.quit_game_after_finish = self.config.get('quit_game_after_finish', False)
            abyss_main.shutdown_pc_after_finish = self.config.get('shutdown_after_finish', False)
            
            # 保存模块引用用于停止
            self._abyss_main = abyss_main
            
            # 启动脚本内部的热键监听（End停止、Delete暂停）
            listener = threading.Thread(target=abyss_main.start_keyboard_listener, daemon=True)
            listener.start()
            abyss_main.main_script()
            self.log("脚本执行完成")
        finally:
            os.chdir(original_dir)


class SkillRowWidget(QWidget):
    """单个技能行组件"""
    deleted = pyqtSignal(object)
    
    def __init__(self, skill_data=None, parent=None):
        super().__init__(parent)
        self.skill_data = skill_data or {}
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # 技能类型选择
        layout.addWidget(QLabel("类型:"))
        self.type_combo = NoScrollComboBox()
        self.type_combo.addItems(['普通按键', '特殊按键', '引爆技能', '组合技能', '自定义技能'])
        self.type_combo.setMinimumWidth(100)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)
        
        # 普通按键输入（从技能栏配置的按键中选择）
        self.str_label = QLabel("按键:")
        layout.addWidget(self.str_label)
        self.str_combo = NoScrollComboBox()
        self._populate_skill_keys(self.str_combo)
        self.str_combo.setFixedWidth(80)
        layout.addWidget(self.str_combo)
        
        # 特殊按键选择
        self.key_label = QLabel("按键:")
        layout.addWidget(self.key_label)
        self.key_combo = NoScrollComboBox()
        self.key_combo.addItems(['ctrl_l', 'alt_l', 'shift_l', 'space', 'tab', 'esc',
                                  'up', 'down', 'left', 'right', 'enter'])
        self.key_combo.setFixedWidth(80)
        layout.addWidget(self.key_combo)
        
        # 引爆技能字段
        self.detonate_name_label = QLabel("名称:")
        layout.addWidget(self.detonate_name_label)
        self.detonate_name_edit = QLineEdit()
        self.detonate_name_edit.setPlaceholderText("技能名")
        self.detonate_name_edit.setFixedWidth(60)
        layout.addWidget(self.detonate_name_edit)
        
        self.detonate_hotkey_label = QLabel("热键:")
        layout.addWidget(self.detonate_hotkey_label)
        self.detonate_hotkey_edit = QLineEdit()
        self.detonate_hotkey_edit.setPlaceholderText("q")
        self.detonate_hotkey_edit.setFixedWidth(30)
        layout.addWidget(self.detonate_hotkey_edit)
        
        self.detonate_cd_check = QCheckBox("检测CD")
        self.detonate_cd_check.setChecked(True)
        self.detonate_cd_check.stateChanged.connect(self._on_detonate_cd_changed)
        layout.addWidget(self.detonate_cd_check)
        
        self.detonate_cd_label = QLabel("CD:")
        layout.addWidget(self.detonate_cd_label)
        self.detonate_cd_spin = NoScrollDoubleSpinBox()
        self.detonate_cd_spin.setRange(0, 100)
        self.detonate_cd_spin.setDecimals(1)
        self.detonate_cd_spin.setSuffix("s")
        self.detonate_cd_spin.setFixedWidth(55)
        layout.addWidget(self.detonate_cd_spin)
        
        # 组合技能字段
        self.combo_name_label = QLabel("名称:")
        layout.addWidget(self.combo_name_label)
        self.combo_name_edit = QLineEdit()
        self.combo_name_edit.setPlaceholderText("技能名")
        self.combo_name_edit.setFixedWidth(60)
        layout.addWidget(self.combo_name_edit)
        
        self.combo_hotkey_label = QLabel("热键:")
        layout.addWidget(self.combo_hotkey_label)
        self.combo_hotkey_edit = QLineEdit()
        self.combo_hotkey_edit.setPlaceholderText("q")
        self.combo_hotkey_edit.setFixedWidth(30)
        layout.addWidget(self.combo_hotkey_edit)
        
        self.combo_command_label = QLabel("指令:")
        layout.addWidget(self.combo_command_label)
        self.combo_command_edit = QLineEdit()
        self.combo_command_edit.setPlaceholderText("q,q,q")
        self.combo_command_edit.setFixedWidth(80)
        layout.addWidget(self.combo_command_edit)
        
        # 自定义技能字段（包含所有参数）
        self.custom_name_label = QLabel("名称:")
        layout.addWidget(self.custom_name_label)
        self.custom_name_edit = QLineEdit()
        self.custom_name_edit.setPlaceholderText("可选")
        self.custom_name_edit.setFixedWidth(50)
        layout.addWidget(self.custom_name_edit)
        
        self.custom_hotkey_label = QLabel("热键:")
        layout.addWidget(self.custom_hotkey_label)
        self.custom_hotkey_edit = QLineEdit()
        self.custom_hotkey_edit.setPlaceholderText("可选")
        self.custom_hotkey_edit.setFixedWidth(30)
        layout.addWidget(self.custom_hotkey_edit)
        
        self.custom_command_label = QLabel("指令:")
        layout.addWidget(self.custom_command_label)
        self.custom_command_edit = QLineEdit()
        self.custom_command_edit.setPlaceholderText("可选")
        self.custom_command_edit.setFixedWidth(70)
        layout.addWidget(self.custom_command_edit)
        
        self.custom_cd_label = QLabel("CD:")
        layout.addWidget(self.custom_cd_label)
        self.custom_cd_spin = NoScrollDoubleSpinBox()
        self.custom_cd_spin.setRange(0, 100)
        self.custom_cd_spin.setDecimals(1)
        self.custom_cd_spin.setSuffix("s")
        self.custom_cd_spin.setFixedWidth(50)
        layout.addWidget(self.custom_cd_spin)
        
        self.custom_cd_check = QCheckBox("检测CD")
        self.custom_cd_check.setChecked(False)
        self.custom_cd_check.stateChanged.connect(self._on_custom_cd_changed)
        layout.addWidget(self.custom_cd_check)
        
        # 删除按钮
        del_btn = QPushButton("×")
        del_btn.setFixedSize(24, 24)
        del_btn.setStyleSheet("color: red; font-weight: bold;")
        del_btn.clicked.connect(lambda: self.deleted.emit(self))
        layout.addWidget(del_btn)
        
        layout.addStretch()
        
        # 加载数据
        self._load_data()
        self._on_type_changed()
    
    def _populate_skill_keys(self, combo):
        """从技能栏配置获取可用的按键列表"""
        try:
            from dnf.stronger.skill_util import ACTUAL_KEYS
            keys = [k for k in ACTUAL_KEYS if k]  # 过滤空值
            combo.addItems(keys)
        except:
            # 默认按键
            combo.addItems(['q', 'w', 'e', 'r', 't', 'a', 's', 'd', 'f', 'g', 'h'])
        combo.setMaxVisibleItems(12)
        combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
    
    def _load_data(self):
        """加载技能数据"""
        if not self.skill_data:
            return
        
        skill_type = self.skill_data.get('type', 'str')
        if skill_type == 'str':
            self.type_combo.setCurrentIndex(0)
            val = self.skill_data.get('value', '')
            idx = self.str_combo.findText(val)
            if idx >= 0:
                self.str_combo.setCurrentIndex(idx)
        elif skill_type == 'key':
            self.type_combo.setCurrentIndex(1)
            key_val = self.skill_data.get('value', '').replace('Key.', '')
            idx = self.key_combo.findText(key_val)
            if idx >= 0:
                self.key_combo.setCurrentIndex(idx)
        elif skill_type == 'skill':
            # 判断是引爆技能、组合技能还是自定义技能
            hotkey_cd = self.skill_data.get('hotkey_cd_command_cast', False)
            cmd = self.skill_data.get('command', [])
            # 引爆技能特征：指令为 [热键, '', '', 热键] 格式
            is_detonate = len(cmd) == 4 and cmd[1] == '' and cmd[2] == ''
            if is_detonate:
                # 引爆技能
                self.type_combo.setCurrentIndex(2)
                self.detonate_name_edit.setText(self.skill_data.get('name', ''))
                self.detonate_hotkey_edit.setText(self.skill_data.get('hot_key', ''))
                self.detonate_cd_check.setChecked(hotkey_cd)
                self.detonate_cd_spin.setValue(self.skill_data.get('cd', 0))
            elif hotkey_cd:
                # 组合技能（hotkey_cd_command_cast 为 True）
                self.type_combo.setCurrentIndex(3)
                self.combo_name_edit.setText(self.skill_data.get('name', ''))
                self.combo_hotkey_edit.setText(self.skill_data.get('hot_key', ''))
                self.combo_command_edit.setText(','.join(cmd) if cmd else '')
            else:
                # 自定义技能
                self.type_combo.setCurrentIndex(4)
                self.custom_name_edit.setText(self.skill_data.get('name', ''))
                self.custom_hotkey_edit.setText(self.skill_data.get('hot_key', ''))
                self.custom_command_edit.setText(','.join(cmd) if cmd else '')
                self.custom_cd_spin.setValue(self.skill_data.get('cd', 0))
                self.custom_cd_check.setChecked(hotkey_cd)
        elif skill_type == 'detonate':
            # 新添加的引爆技能
            self.type_combo.setCurrentIndex(2)
        elif skill_type == 'combo':
            # 新添加的组合技能
            self.type_combo.setCurrentIndex(3)
        elif skill_type == 'custom':
            # 新添加的自定义技能
            self.type_combo.setCurrentIndex(4)
    
    def _on_type_changed(self, _=None):
        """类型切换时显示/隐藏对应字段"""
        idx = self.type_combo.currentIndex()
        # 普通按键
        self.str_label.setVisible(idx == 0)
        self.str_combo.setVisible(idx == 0)
        # 特殊按键
        self.key_label.setVisible(idx == 1)
        self.key_combo.setVisible(idx == 1)
        # 引爆技能
        is_detonate = idx == 2
        self.detonate_name_label.setVisible(is_detonate)
        self.detonate_name_edit.setVisible(is_detonate)
        self.detonate_hotkey_label.setVisible(is_detonate)
        self.detonate_hotkey_edit.setVisible(is_detonate)
        self.detonate_cd_check.setVisible(is_detonate)
        self.detonate_cd_label.setVisible(is_detonate and not self.detonate_cd_check.isChecked())
        self.detonate_cd_spin.setVisible(is_detonate and not self.detonate_cd_check.isChecked())
        # 组合技能
        is_combo = idx == 3
        self.combo_name_label.setVisible(is_combo)
        self.combo_name_edit.setVisible(is_combo)
        self.combo_hotkey_label.setVisible(is_combo)
        self.combo_hotkey_edit.setVisible(is_combo)
        self.combo_command_label.setVisible(is_combo)
        self.combo_command_edit.setVisible(is_combo)
        # 自定义技能
        is_custom = idx == 4
        self.custom_name_label.setVisible(is_custom)
        self.custom_name_edit.setVisible(is_custom)
        self.custom_hotkey_label.setVisible(is_custom)
        self.custom_hotkey_edit.setVisible(is_custom)
        self.custom_command_label.setVisible(is_custom)
        self.custom_command_edit.setVisible(is_custom)
        self.custom_cd_check.setVisible(is_custom)
        self.custom_cd_label.setVisible(is_custom and not self.custom_cd_check.isChecked())
        self.custom_cd_spin.setVisible(is_custom and not self.custom_cd_check.isChecked())
    
    def _on_detonate_cd_changed(self, state):
        """引爆技能CD检测开关变化"""
        is_detonate = self.type_combo.currentIndex() == 2
        self.detonate_cd_label.setVisible(is_detonate and not state)
        self.detonate_cd_spin.setVisible(is_detonate and not state)
    
    def _on_custom_cd_changed(self, state):
        """自定义技能CD检测开关变化"""
        is_custom = self.type_combo.currentIndex() == 4
        self.custom_cd_label.setVisible(is_custom and not state)
        self.custom_cd_spin.setVisible(is_custom and not state)
    
    def get_data(self):
        """获取技能数据"""
        idx = self.type_combo.currentIndex()
        if idx == 0:  # 普通按键
            val = self.str_combo.currentText().strip()
            if not val:
                return None
            return {'type': 'str', 'value': val}
        elif idx == 1:  # 特殊按键
            return {'type': 'key', 'value': f'Key.{self.key_combo.currentText()}'}
        elif idx == 2:  # 引爆技能
            hotkey = self.detonate_hotkey_edit.text().strip()
            name = self.detonate_name_edit.text().strip()
            if not hotkey and not name:
                return None  # 至少要有热键或名称
            hotkey_cd = self.detonate_cd_check.isChecked()
            # 指令为: 热键, 空, 空, 热键
            cmd_list = [hotkey, '', '', hotkey] if hotkey else []
            return {
                'type': 'skill',
                'name': name,
                'hot_key': hotkey,
                'command': cmd_list,
                'concurrent': False,
                'cd': 0 if hotkey_cd else self.detonate_cd_spin.value(),
                'animation_time': self.skill_data.get('animation_time', 0.7),
                'hotkey_cd_command_cast': hotkey_cd
            }
        elif idx == 3:  # 组合技能
            name = self.combo_name_edit.text().strip()
            hotkey = self.combo_hotkey_edit.text().strip()
            cmd_text = self.combo_command_edit.text().strip()
            if not name and not hotkey and not cmd_text:
                return None  # 至少要有一个字段
            cmd_list = [c.strip() for c in cmd_text.split(',') if c.strip()] if cmd_text else []
            return {
                'type': 'skill',
                'name': name,
                'hot_key': hotkey,
                'command': cmd_list,
                'concurrent': False,
                'cd': 0,
                'animation_time': self.skill_data.get('animation_time', 0.7),
                'hotkey_cd_command_cast': True
            }
        else:  # 自定义技能
            name = self.custom_name_edit.text().strip()
            hotkey = self.custom_hotkey_edit.text().strip()
            cmd_text = self.custom_command_edit.text().strip()
            cmd_list = [c.strip() for c in cmd_text.split(',') if c.strip()] if cmd_text else []
            hotkey_cd = self.custom_cd_check.isChecked()
            return {
                'type': 'skill',
                'name': name,
                'hot_key': hotkey,
                'command': cmd_list,
                'concurrent': self.skill_data.get('concurrent', False),
                'cd': self.custom_cd_spin.value(),
                'animation_time': self.skill_data.get('animation_time', 0.7),
                'hotkey_cd_command_cast': hotkey_cd
            }


class PowerfulSkillRowWidget(SkillRowWidget):
    """高伤技能行组件（继承自SkillRowWidget，支持所有技能类型）"""
    pass


class RoleEditDialog(QDialog):
    """角色编辑对话框"""
    def __init__(self, parent=None, role_data=None, default_no=1):
        super().__init__(parent)
        self.role_data = role_data or {}
        self.default_no = default_no
        self.setWindowTitle("编辑角色" if role_data else "添加角色")
        self.setMinimumWidth(650)
        self.setMinimumHeight(500)
        self.skill_rows = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # 角色编号
        self.no_spin = NoScrollSpinBox()
        self.no_spin.setRange(1, 999)
        self.no_spin.setValue(self.role_data.get('no', self.default_no))
        form_layout.addRow("角色编号:", self.no_spin)
        
        # 角色名称
        self.name_edit = QLineEdit(self.role_data.get('name', ''))
        form_layout.addRow("角色名称:", self.name_edit)
        
        # 角色高度
        self.height_spin = NoScrollSpinBox()
        self.height_spin.setRange(100, 200)
        self.height_spin.setValue(self.role_data.get('height', 150))
        form_layout.addRow("角色高度:", self.height_spin)
        
        # 疲劳值
        fatigue_layout = QHBoxLayout()
        self.fatigue_all_spin = NoScrollSpinBox()
        self.fatigue_all_spin.setRange(0, 200)
        self.fatigue_all_spin.setValue(self.role_data.get('fatigue_all', 188))
        fatigue_layout.addWidget(QLabel("总疲劳:"))
        fatigue_layout.addWidget(self.fatigue_all_spin)
        self.fatigue_reserved_spin = NoScrollSpinBox()
        self.fatigue_reserved_spin.setRange(0, 200)
        self.fatigue_reserved_spin.setValue(self.role_data.get('fatigue_reserved', 0))
        fatigue_layout.addWidget(QLabel("预留:"))
        fatigue_layout.addWidget(self.fatigue_reserved_spin)
        fatigue_layout.addStretch()
        form_layout.addRow("疲劳值:", fatigue_layout)
        
        # 需要Buff
        self.buff_check = QCheckBox("启用")
        self.buff_check.setChecked(self.role_data.get('buff_effective', False))
        form_layout.addRow("需要Buff:", self.buff_check)
        
        layout.addLayout(form_layout)
        
        # 技能列表
        skill_group = QGroupBox("技能列表")
        skill_group_layout = QVBoxLayout(skill_group)
        
        # 技能滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        
        self.skill_container = QWidget()
        self.skill_layout = QVBoxLayout(self.skill_container)
        self.skill_layout.setSpacing(2)
        self.skill_layout.addStretch()
        scroll.setWidget(self.skill_container)
        skill_group_layout.addWidget(scroll)
        
        # 加载已有技能
        self._load_existing_skills()
        
        # 添加技能按钮
        add_btn_layout = QHBoxLayout()
        add_str_btn = QPushButton("+ 普通按键")
        add_str_btn.clicked.connect(lambda: self._add_skill_row({'type': 'str'}))
        add_btn_layout.addWidget(add_str_btn)
        

        
        add_detonate_btn = QPushButton("+ 引爆技能")
        add_detonate_btn.clicked.connect(lambda: self._add_skill_row({'type': 'detonate'}))
        add_btn_layout.addWidget(add_detonate_btn)
        
        add_combo_btn = QPushButton("+ 组合技能")
        add_combo_btn.clicked.connect(lambda: self._add_skill_row({'type': 'combo'}))
        add_btn_layout.addWidget(add_combo_btn)
        
        add_custom_btn = QPushButton("+ 自定义")
        add_custom_btn.clicked.connect(lambda: self._add_skill_row({'type': 'custom'}))
        add_btn_layout.addWidget(add_custom_btn)
        
        add_btn_layout.addStretch()
        
        # 保存技能按钮
        save_skills_btn = QPushButton("💾 保存技能")
        save_skills_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        save_skills_btn.clicked.connect(self._save_skills)
        add_btn_layout.addWidget(save_skills_btn)
        
        skill_group_layout.addLayout(add_btn_layout)
        
        # 技能保存状态提示
        self.skill_status_label = QLabel("")
        self.skill_status_label.setStyleSheet("color: #666; font-size: 11px;")
        skill_group_layout.addWidget(self.skill_status_label)
        
        layout.addWidget(skill_group)
        
        # 高伤技能列表
        powerful_group = QGroupBox("高伤技能 (大招)")
        powerful_group_layout = QVBoxLayout(powerful_group)
        
        # 高伤技能滚动区域
        powerful_scroll = QScrollArea()
        powerful_scroll.setWidgetResizable(True)
        powerful_scroll.setMaximumHeight(100)
        
        self.powerful_container = QWidget()
        self.powerful_layout = QVBoxLayout(self.powerful_container)
        self.powerful_layout.setSpacing(2)
        self.powerful_layout.addStretch()
        powerful_scroll.setWidget(self.powerful_container)
        powerful_group_layout.addWidget(powerful_scroll)
        
        # 加载已有高伤技能
        self.powerful_rows = []
        self._load_existing_powerful_skills()
        
        # 添加高伤技能按钮
        powerful_btn_layout = QHBoxLayout()
        add_powerful_btn = QPushButton("+ 添加高伤技能")
        add_powerful_btn.clicked.connect(self._add_powerful_skill_row)
        powerful_btn_layout.addWidget(add_powerful_btn)
        powerful_btn_layout.addStretch()
        powerful_group_layout.addLayout(powerful_btn_layout)
        
        layout.addWidget(powerful_group)
        
        # 确定取消按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._confirm_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _save_skills(self, _=None):
        """保存技能列表"""
        skills = self._get_skills()
        skill_count = len(skills)
        if skill_count > 0:
            self.skill_status_label.setText(f"✓ 已保存 {skill_count} 个技能")
            self.skill_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            self.skill_status_label.setText("⚠ 没有有效的技能")
            self.skill_status_label.setStyleSheet("color: #ff9800; font-size: 11px;")
    
    def _confirm_save(self, _=None):
        """确认保存"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入角色名称")
            return
        
        reply = QMessageBox.question(
            self, "确认保存",
            f"确定要保存角色 \"{name}\" 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self.accept()
    
    def _load_existing_skills(self):
        """加载已有技能"""
        skills = self.role_data.get('custom_priority_skills', [])
        for s in skills:
            if isinstance(s, str):
                self._add_skill_row({'type': 'str', 'value': s})
            elif isinstance(s, dict):
                self._add_skill_row(s)
    
    def _add_skill_row(self, skill_data=None):
        """添加一行技能"""
        # clicked信号会传入布尔值，需要过滤
        if isinstance(skill_data, bool):
            skill_data = None
        row = SkillRowWidget(skill_data, self)
        row.deleted.connect(self._remove_skill_row)
        self.skill_rows.append(row)
        # 插入到 stretch 之前
        self.skill_layout.insertWidget(self.skill_layout.count() - 1, row)
    
    def _remove_skill_row(self, row):
        """删除技能行"""
        if row in self.skill_rows:
            self.skill_rows.remove(row)
            self.skill_layout.removeWidget(row)
            row.deleteLater()
    
    def _get_skills(self):
        """获取所有技能数据"""
        result = []
        for row in self.skill_rows:
            data = row.get_data()
            if data:
                result.append(data)
        return result
    
    def _load_existing_powerful_skills(self):
        """加载已有高伤技能"""
        skills = self.role_data.get('powerful_skills', [])
        for s in skills:
            if isinstance(s, str):
                self._add_powerful_skill_row({'type': 'str', 'value': s})
            elif isinstance(s, dict):
                self._add_powerful_skill_row(s)
    
    def _add_powerful_skill_row(self, skill_data=None):
        """添加一行高伤技能"""
        # clicked信号会传入布尔值，需要过滤
        if isinstance(skill_data, bool):
            skill_data = None
        row = PowerfulSkillRowWidget(skill_data, self)
        row.deleted.connect(self._remove_powerful_skill_row)
        self.powerful_rows.append(row)
        self.powerful_layout.insertWidget(self.powerful_layout.count() - 1, row)
    
    def _remove_powerful_skill_row(self, row):
        """删除高伤技能行"""
        if row in self.powerful_rows:
            self.powerful_rows.remove(row)
            self.powerful_layout.removeWidget(row)
            row.deleteLater()
    
    def _get_powerful_skills(self):
        """获取所有高伤技能数据"""
        result = []
        for row in self.powerful_rows:
            data = row.get_data()
            if data:
                result.append(data)
        return result
    
    def get_data(self):
        """获取完整的角色数据"""
        return {
            'name': self.name_edit.text(),
            'no': self.no_spin.value(),
            'buffs': self.role_data.get('buffs', [[]]),
            'candidate_hotkeys': self.role_data.get('candidate_hotkeys', ['x']),
            'custom_priority_skills': self._get_skills(),
            'height': self.height_spin.value(),
            'fatigue_all': self.fatigue_all_spin.value(),
            'fatigue_reserved': self.fatigue_reserved_spin.value(),
            'attack_center_x': self.role_data.get('attack_center_x', 0),
            'attack_range_x': self.role_data.get('attack_range_x', 0),
            'attack_range_y': self.role_data.get('attack_range_y', 0),
            'buff_effective': self.buff_check.isChecked(),
            'powerful_skills': self._get_powerful_skills(),
            'white_map_level': self.role_data.get('white_map_level', 2)
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.hotkey_listener = None
        self.is_paused = False
        self.role_config = {'account1': [], 'account2': []}
        self.gui_config = {}
        # 不再自动同步，只在用户点击"从代码强制同步"时才同步
        # self.auto_sync_role_config()
        self.load_role_config()
        self.load_gui_config()
        self.init_ui()
        self.load_mail_config()  # 加载邮件配置（日志在预加载完成后显示）
        self.apply_gui_config()  # 应用保存的配置
        self.start_hotkey_listener()
        self.init_schedule_timer()  # 初始化定时器
        self.preload_modules()  # 后台预加载重量级模块
    
    def auto_sync_role_config(self):
        """启动时自动同步角色配置（只同步新增/删除的角色）"""
        try:
            from dnf.stronger.role_config_manager import sync_role_configs
            # 同步两个账号的角色配置
            added1, removed1, total1 = sync_role_configs(1)
            added2, removed2, total2 = sync_role_configs(2)
            
            if added1 or removed1 or added2 or removed2:
                print(f"角色配置已同步: 账号1({total1}个,+{added1}/-{removed1}), 账号2({total2}个,+{added2}/-{removed2})")
            else:
                print(f"角色配置无变化: 账号1({total1}个), 账号2({total2}个)")
        except Exception as e:
            print(f"自动同步角色配置失败: {e}")
    
    def init_ui(self):
        self.setWindowTitle("DNF Return my hard-earned money")
        # 背景图尺寸 2304x1440，比例 16:10，缩小到 1152x720
        self.setMinimumSize(1000, 625)
        self.resize(1152, 720)
        
        # 设置窗口图标
        icon_path = os.path.join(PROJECT_ROOT, 'assets', 'img', 'img_gui', 'favicon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 10, 30, 10)  # 减小边距
        layout.setSpacing(8)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.tabs.addTab(self._create_stronger_tab(), "妖气追踪/白图")
        self.tabs.addTab(self._create_abyss_tab(), "深渊模式")
        self.tabs.addTab(self._create_role_tab(), "账号||角色配置")
        self.tabs.addTab(self._create_key_config_tab(), "按键配置")
        self.tabs.addTab(self._create_skill_bar_tab(), "技能栏配置")
        self.tabs.addTab(self._create_settings_tab(), "设置")
        
        # 日志区域
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 8, 8, 8)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMinimumHeight(120)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.start_btn = QPushButton("▶ 启动 (F10)")
        self.start_btn.setMinimumSize(130, 40)
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.start_btn.clicked.connect(self.start_script)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("■ 停止 (End)")
        self.stop_btn.setMinimumSize(130, 40)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_script)
        btn_layout.addWidget(self.stop_btn)
        
        self.pause_btn = QPushButton("⏸ 暂停 (Del)")
        self.pause_btn.setMinimumSize(130, 40)
        self.pause_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; }")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_script)
        btn_layout.addWidget(self.pause_btn)
        
        btn_layout.addStretch()
        
        clear_btn = QPushButton("清空日志")
        clear_btn.setMinimumHeight(40)
        clear_btn.clicked.connect(self.clear_log)
        btn_layout.addWidget(clear_btn)
        
        layout.addLayout(btn_layout)
        
        self.statusBar().showMessage("就绪 - F10启动 | Delete暂停 | End停止")
        self.log("程序已启动")
        self.log("热键: F10=启动, Delete=暂停/继续, End=停止")

    def _create_stronger_tab(self):
        """创建妖气追踪选项卡"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 游戏模式
        mode_group = QGroupBox("游戏模式")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(6)
        mode_layout.setContentsMargins(8, 8, 8, 8)
        self.mode_group = QButtonGroup()
        modes = ["白图(跌宕群岛)", "每日1+1", "妖气追踪", "妖怪歼灭", "先1+1再白图", "先1+1再妖气追踪"]
        row1, row2 = QHBoxLayout(), QHBoxLayout()
        for i, mode in enumerate(modes):
            rb = QRadioButton(mode)
            self.mode_group.addButton(rb, i + 1)
            (row1 if i < 3 else row2).addWidget(rb)
            if mode == "妖气追踪":
                rb.setChecked(True)
        mode_layout.addLayout(row1)
        mode_layout.addLayout(row2)
        layout.addWidget(mode_group)
        
        # 角色设置
        role_group = QGroupBox("角色设置")
        role_layout = QVBoxLayout(role_group)
        role_layout.setSpacing(6)
        role_layout.setContentsMargins(8, 8, 8, 8)
        lbl_w = 70  # 标签宽度
        spin_w = 65  # 数字框宽度
        combo_w = 115  # 下拉框宽度
        
        acc_layout = QHBoxLayout()
        lbl_acc = QLabel("账号类型:")
        lbl_acc.setFixedWidth(lbl_w)
        acc_layout.addWidget(lbl_acc)
        self.stronger_account_combo = QComboBox()
        self.stronger_account_combo.setMinimumWidth(150)
        acc_layout.addWidget(self.stronger_account_combo)
        acc_layout.addStretch()
        role_layout.addLayout(acc_layout)
        
        range_layout = QHBoxLayout()
        lbl_first = QLabel("起始角色:")
        lbl_first.setFixedWidth(lbl_w)
        range_layout.addWidget(lbl_first)
        self.first_role = NoScrollSpinBox()
        self.first_role.setFixedWidth(spin_w)
        self.first_role.setRange(1, 50)
        self.first_role.setValue(1)
        range_layout.addWidget(self.first_role)
        lbl_last = QLabel("结束角色:")
        lbl_last.setFixedWidth(lbl_w)
        range_layout.addWidget(lbl_last)
        self.last_role = NoScrollSpinBox()
        self.last_role.setFixedWidth(spin_w)
        self.last_role.setRange(1, 50)
        # 从角色配置获取默认账号的角色数量，没有则默认1
        default_role_count = len(self.role_config.get('account1', [])) or 1
        self.last_role.setValue(default_role_count)
        range_layout.addWidget(self.last_role)
        range_layout.addStretch()
        role_layout.addLayout(range_layout)
        
        # 跳过角色设置
        skip_layout = QHBoxLayout()
        self.skip_role_enabled = QCheckBox("启用跳过角色")
        self.skip_role_enabled.setFixedWidth(120)
        self.skip_role_enabled.setToolTip("在白图/妖气追踪模式下跳过指定角色")
        skip_layout.addWidget(self.skip_role_enabled)
        lbl_skip = QLabel("跳过编号:")
        lbl_skip.setFixedWidth(70)
        skip_layout.addWidget(lbl_skip)
        self.skip_role_list = QLineEdit()
        self.skip_role_list.setFixedWidth(150)
        self.skip_role_list.setPlaceholderText("例如: 3,5,10")
        skip_layout.addWidget(self.skip_role_list)
        skip_layout.addStretch()
        role_layout.addLayout(skip_layout)
        
        layout.addWidget(role_group)
        
        # 疲劳值设置
        fatigue_group = QGroupBox("疲劳值设置")
        fatigue_layout = QHBoxLayout(fatigue_group)
        fatigue_layout.setSpacing(10)
        fatigue_layout.setContentsMargins(8, 8, 8, 8)
        self.stronger_uniform = QCheckBox("使用统一预留疲劳值")
        self.stronger_uniform.setFixedWidth(160)
        fatigue_layout.addWidget(self.stronger_uniform)
        lbl_fatigue = QLabel("预留疲劳值:")
        lbl_fatigue.setFixedWidth(80)
        fatigue_layout.addWidget(lbl_fatigue)
        self.stronger_fatigue = NoScrollSpinBox()
        self.stronger_fatigue.setFixedWidth(spin_w)
        self.stronger_fatigue.setRange(0, 200)
        self.stronger_fatigue.setValue(0)
        fatigue_layout.addWidget(self.stronger_fatigue)
        fatigue_layout.addStretch()
        layout.addWidget(fatigue_group)
        
        # 购买设置
        buy_group = QGroupBox("神秘商店购买设置")
        buy_layout = QVBoxLayout(buy_group)
        buy_layout.setSpacing(6)
        buy_layout.setContentsMargins(8, 8, 8, 8)
        buy_row1 = QHBoxLayout()
        lbl_tank = QLabel("罐子:")
        lbl_tank.setFixedWidth(45)
        buy_row1.addWidget(lbl_tank)
        self.buy_tank = NoScrollComboBox()
        self.buy_tank.setFixedWidth(combo_w)
        self.buy_tank.addItems(["不买", "买传说", "买史诗", "买史诗+传说"])
        buy_row1.addWidget(self.buy_tank)
        lbl_bell = QLabel("铃铛:")
        lbl_bell.setFixedWidth(50)
        buy_row1.addWidget(lbl_bell)
        self.buy_bell = NoScrollComboBox()
        self.buy_bell.setFixedWidth(combo_w)
        self.buy_bell.addItems(["不买", "买粉罐子", "买传说罐子", "买粉+传说"])
        buy_row1.addWidget(self.buy_bell)
        buy_row1.addStretch()
        buy_layout.addLayout(buy_row1)
        
        buy_row2 = QHBoxLayout()
        lbl_ssm = QLabel("闪闪明:")
        lbl_ssm.setFixedWidth(50)
        buy_row2.addWidget(lbl_ssm)
        self.buy_ssm = NoScrollComboBox()
        self.buy_ssm.setFixedWidth(combo_w)
        self.buy_ssm.addItems(["不买", "买粉罐子", "买传说罐子", "买粉+传说"])
        self.buy_ssm.setCurrentIndex(2)
        buy_row2.addWidget(self.buy_ssm)
        lbl_catalyst = QLabel("催化剂:")
        lbl_catalyst.setFixedWidth(50)
        buy_row2.addWidget(lbl_catalyst)
        self.buy_catalyst = NoScrollComboBox()
        self.buy_catalyst.setFixedWidth(combo_w)
        self.buy_catalyst.addItems(["不买", "传说", "史诗", "太初", "传说+史诗", "史诗+太初", "传说+太初", "全部"])
        self.buy_catalyst.setCurrentIndex(7)
        buy_row2.addWidget(self.buy_catalyst)
        buy_row2.addStretch()
        buy_layout.addLayout(buy_row2)
        layout.addWidget(buy_group)
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll
    
    def _create_abyss_tab(self):
        """创建深渊选项卡"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        lbl_w = 75  # 标签宽度
        spin_w = 70  # 数字框宽度
        combo_w = 120  # 下拉框宽度
        
        # 角色设置
        role_group = QGroupBox("角色设置")
        role_layout = QVBoxLayout(role_group)
        role_layout.setSpacing(6)
        role_layout.setContentsMargins(8, 8, 8, 8)
        
        # 账号类型
        acc_layout = QHBoxLayout()
        lbl_acc = QLabel("账号类型:")
        lbl_acc.setFixedWidth(lbl_w)
        acc_layout.addWidget(lbl_acc)
        self.abyss_account_combo = QComboBox()
        self.abyss_account_combo.setMinimumWidth(150)
        acc_layout.addWidget(self.abyss_account_combo)
        acc_layout.addStretch()
        role_layout.addLayout(acc_layout)
        
        # 角色范围
        range_layout = QHBoxLayout()
        lbl_first = QLabel("起始角色:")
        lbl_first.setFixedWidth(lbl_w)
        range_layout.addWidget(lbl_first)
        self.abyss_first = NoScrollSpinBox()
        self.abyss_first.setFixedWidth(spin_w)
        self.abyss_first.setRange(1, 50)
        self.abyss_first.setValue(1)
        range_layout.addWidget(self.abyss_first)
        lbl_last = QLabel("结束角色:")
        lbl_last.setFixedWidth(lbl_w)
        range_layout.addWidget(lbl_last)
        self.abyss_last = NoScrollSpinBox()
        self.abyss_last.setFixedWidth(spin_w)
        self.abyss_last.setRange(1, 50)
        # 从角色配置获取默认账号的角色数量，没有则默认1
        default_role_count = len(self.role_config.get('account1', [])) or 1
        self.abyss_last.setValue(default_role_count)
        range_layout.addWidget(self.abyss_last)
        range_layout.addStretch()
        role_layout.addLayout(range_layout)
        
        # 跳过角色设置
        skip_layout = QHBoxLayout()
        self.abyss_skip_role_enabled = QCheckBox("启用跳过角色")
        self.abyss_skip_role_enabled.setFixedWidth(120)
        self.abyss_skip_role_enabled.setToolTip("在深渊模式下跳过指定角色")
        skip_layout.addWidget(self.abyss_skip_role_enabled)
        lbl_skip = QLabel("跳过编号:")
        lbl_skip.setFixedWidth(70)
        skip_layout.addWidget(lbl_skip)
        self.abyss_skip_role_list = QLineEdit()
        self.abyss_skip_role_list.setFixedWidth(150)
        self.abyss_skip_role_list.setPlaceholderText("例如: 3,5,10")
        skip_layout.addWidget(self.abyss_skip_role_list)
        skip_layout.addStretch()
        role_layout.addLayout(skip_layout)
        
        layout.addWidget(role_group)
        
        fatigue_group = QGroupBox("疲劳值设置")
        fatigue_layout = QHBoxLayout(fatigue_group)
        fatigue_layout.setSpacing(10)
        fatigue_layout.setContentsMargins(8, 8, 8, 8)
        self.abyss_uniform = QCheckBox("使用统一预留疲劳值")
        self.abyss_uniform.setFixedWidth(160)
        fatigue_layout.addWidget(self.abyss_uniform)
        lbl_fatigue = QLabel("预留疲劳值:")
        lbl_fatigue.setFixedWidth(80)
        fatigue_layout.addWidget(lbl_fatigue)
        self.abyss_fatigue = NoScrollSpinBox()
        self.abyss_fatigue.setFixedWidth(spin_w)
        self.abyss_fatigue.setRange(0, 200)
        self.abyss_fatigue.setValue(17)
        fatigue_layout.addWidget(self.abyss_fatigue)
        fatigue_layout.addStretch()
        layout.addWidget(fatigue_group)
        
        buy_group = QGroupBox("神秘商店购买设置")
        buy_layout = QVBoxLayout(buy_group)
        buy_layout.setSpacing(6)
        buy_layout.setContentsMargins(8, 8, 8, 8)
        buy_row1 = QHBoxLayout()
        lbl_tank = QLabel("罐子:")
        lbl_tank.setFixedWidth(45)
        buy_row1.addWidget(lbl_tank)
        self.abyss_tank = NoScrollComboBox()
        self.abyss_tank.setFixedWidth(combo_w)
        self.abyss_tank.addItems(["不买", "买传说", "买史诗", "买史诗+传说"])
        buy_row1.addWidget(self.abyss_tank)
        lbl_bell = QLabel("铃铛:")
        lbl_bell.setFixedWidth(50)
        buy_row1.addWidget(lbl_bell)
        self.abyss_bell = NoScrollComboBox()
        self.abyss_bell.setFixedWidth(combo_w)
        self.abyss_bell.addItems(["不买", "买粉罐子", "买传说罐子", "买粉+传说"])
        self.abyss_bell.setCurrentIndex(2)
        buy_row1.addWidget(self.abyss_bell)
        buy_row1.addStretch()
        buy_layout.addLayout(buy_row1)
        
        buy_row2 = QHBoxLayout()
        lbl_ssm = QLabel("闪闪明:")
        lbl_ssm.setFixedWidth(50)
        buy_row2.addWidget(lbl_ssm)
        self.abyss_ssm = NoScrollComboBox()
        self.abyss_ssm.setFixedWidth(combo_w)
        self.abyss_ssm.addItems(["不买", "买粉罐子", "买传说罐子", "买粉+传说"])
        self.abyss_ssm.setCurrentIndex(2)
        buy_row2.addWidget(self.abyss_ssm)
        lbl_catalyst = QLabel("催化剂:")
        lbl_catalyst.setFixedWidth(50)
        buy_row2.addWidget(lbl_catalyst)
        self.abyss_catalyst = NoScrollComboBox()
        self.abyss_catalyst.setFixedWidth(combo_w)
        self.abyss_catalyst.addItems(["不买", "传说", "史诗", "太初", "传说+史诗", "史诗+太初", "传说+太初", "全部"])
        self.abyss_catalyst.setCurrentIndex(7)
        buy_row2.addWidget(self.abyss_catalyst)
        buy_row2.addStretch()
        buy_layout.addLayout(buy_row2)
        layout.addWidget(buy_group)
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll
    
    def _create_role_tab(self):
        """创建角色列表选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 账号选择和操作按钮
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("选择账号:"))
        
        # 账号选择下拉框
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(150)
        self._refresh_account_combo()
        self.account_combo.currentIndexChanged.connect(self.refresh_role_table)
        top_layout.addWidget(self.account_combo)
        
        # 账号管理按钮
        add_acc_btn = QPushButton("添加账号")
        add_acc_btn.clicked.connect(self.add_account)
        top_layout.addWidget(add_acc_btn)
        
        rename_acc_btn = QPushButton("重命名")
        rename_acc_btn.clicked.connect(self.rename_account)
        top_layout.addWidget(rename_acc_btn)
        
        del_acc_btn = QPushButton("删除账号")
        del_acc_btn.clicked.connect(self.delete_account)
        top_layout.addWidget(del_acc_btn)
        
        top_layout.addStretch()
        
        add_btn = QPushButton("添加角色")
        add_btn.clicked.connect(self.add_role)
        top_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("编辑角色")
        edit_btn.clicked.connect(self.edit_role)
        top_layout.addWidget(edit_btn)
        
        del_btn = QPushButton("删除角色")
        del_btn.clicked.connect(self.delete_role)
        top_layout.addWidget(del_btn)
        
        # 上移下移按钮
        up_btn = QPushButton("↑上移")
        up_btn.clicked.connect(self.move_role_up)
        top_layout.addWidget(up_btn)
        
        down_btn = QPushButton("↓下移")
        down_btn.clicked.connect(self.move_role_down)
        top_layout.addWidget(down_btn)
        
        sync_btn = QPushButton("从代码强制同步")
        sync_btn.setToolTip("将role_list.py中的配置完整覆盖到JSON（会丢失在JSON中的修改）")
        sync_btn.clicked.connect(self.force_sync_from_code)
        top_layout.addWidget(sync_btn)
        
        layout.addLayout(top_layout)
        
        # 角色表格
        self.role_table = QTableWidget()
        self.role_table.setColumnCount(7)
        self.role_table.setHorizontalHeaderLabels(["编号", "角色名称", "高度", "总疲劳", "预留疲劳", "需要Buff", "技能"])
        self.role_table.verticalHeader().setVisible(False)  # 隐藏左侧行号
        # 启用水平滚动条
        self.role_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # 设置列宽
        header = self.role_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # 编号
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # 角色名称
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # 高度
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # 总疲劳
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # 预留疲劳
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # 需要Buff
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 技能列自适应内容
        header.setStretchLastSection(False)
        # 设置固定列宽
        header.resizeSection(0, 50)   # 编号
        header.resizeSection(1, 80)   # 角色名称
        header.resizeSection(2, 50)   # 高度
        header.resizeSection(3, 60)   # 总疲劳
        header.resizeSection(4, 70)   # 预留疲劳
        header.resizeSection(5, 70)   # 需要Buff
        self.role_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.role_table.setSelectionBehavior(QTableWidget.SelectRows)  # 选中整行
        self.role_table.setSelectionMode(QTableWidget.SingleSelection)  # 单选模式
        self.role_table.doubleClicked.connect(self.edit_role)
        layout.addWidget(self.role_table)
        
        # 底部按钮和提示
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(QLabel("提示: 移动角色后需点击保存按钮"))
        bottom_layout.addStretch()
        save_btn = QPushButton("💾 保存角色配置")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px 15px;")
        save_btn.clicked.connect(self.save_role_changes)
        bottom_layout.addWidget(save_btn)
        layout.addLayout(bottom_layout)
        
        self.refresh_role_table()
        return widget
    
    def _create_key_config_tab(self):
        """创建按键配置选项卡"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)
        
        label_width = 70
        combo_width = 100
        
        # 游戏按键配置
        game_key_group = QGroupBox("游戏按键配置")
        game_key_layout = QVBoxLayout(game_key_group)
        game_key_layout.setSpacing(8)
        game_key_layout.setContentsMargins(10, 10, 10, 10)
        
        # 一行显示：再次挑战 + 返回城镇 + 移动物品 + 移动角色
        row1 = QHBoxLayout()
        lbl1 = QLabel("再次挑战:")
        lbl1.setFixedWidth(label_width)
        lbl1.setToolTip("游戏中再次挑战的按键")
        row1.addWidget(lbl1)
        self.key_try_again_combo = NoScrollComboBox()
        self.key_try_again_combo.setFixedWidth(combo_width)
        self._populate_key_combo(self.key_try_again_combo)
        self.key_try_again_combo.setCurrentText("小键盘0")
        row1.addWidget(self.key_try_again_combo)
        row1.addSpacing(20)
        lbl2 = QLabel("返回城镇:")
        lbl2.setFixedWidth(label_width)
        lbl2.setToolTip("游戏中返回城镇的按键")
        row1.addWidget(lbl2)
        self.key_return_town_combo = NoScrollComboBox()
        self.key_return_town_combo.setFixedWidth(combo_width)
        self._populate_key_combo(self.key_return_town_combo)
        self.key_return_town_combo.setCurrentText("F12")
        row1.addWidget(self.key_return_town_combo)
        row1.addSpacing(20)
        lbl3 = QLabel("移动物品:")
        lbl3.setFixedWidth(label_width)
        lbl3.setToolTip("游戏中移动物品的按键")
        row1.addWidget(lbl3)
        self.key_collect_loot_combo = NoScrollComboBox()
        self.key_collect_loot_combo.setFixedWidth(combo_width)
        self._populate_key_combo(self.key_collect_loot_combo)
        self.key_collect_loot_combo.setCurrentText("右Ctrl")
        row1.addWidget(self.key_collect_loot_combo)
        row1.addSpacing(20)
        lbl4 = QLabel("移动角色:")
        lbl4.setFixedWidth(label_width)
        lbl4.setToolTip("游戏中移动角色的按键")
        row1.addWidget(lbl4)
        self.key_collect_role_combo = NoScrollComboBox()
        self.key_collect_role_combo.setFixedWidth(combo_width)
        self._populate_key_combo(self.key_collect_role_combo)
        self.key_collect_role_combo.setCurrentText("小键盘7")
        row1.addWidget(self.key_collect_role_combo)
        row1.addStretch()
        game_key_layout.addLayout(row1)
        
        layout.addWidget(game_key_group)
        
        # 脚本控制按键配置
        script_key_group = QGroupBox("脚本控制按键配置")
        script_key_layout = QVBoxLayout(script_key_group)
        script_key_layout.setSpacing(8)
        script_key_layout.setContentsMargins(10, 10, 10, 10)
        
        # 一行显示：启动 + 暂停 + 停止
        row3 = QHBoxLayout()
        lbl5 = QLabel("启动脚本:")
        lbl5.setFixedWidth(label_width)
        lbl5.setToolTip("启动脚本的热键")
        row3.addWidget(lbl5)
        self.key_start_script_combo = NoScrollComboBox()
        self.key_start_script_combo.setFixedWidth(combo_width)
        self._populate_script_key_combo(self.key_start_script_combo)
        self.key_start_script_combo.setCurrentText("F10")
        row3.addWidget(self.key_start_script_combo)
        row3.addSpacing(30)
        lbl6 = QLabel("暂停脚本:")
        lbl6.setFixedWidth(label_width)
        lbl6.setToolTip("暂停/继续脚本的热键")
        row3.addWidget(lbl6)
        self.key_pause_script_combo = NoScrollComboBox()
        self.key_pause_script_combo.setFixedWidth(combo_width)
        self._populate_script_key_combo(self.key_pause_script_combo)
        self.key_pause_script_combo.setCurrentText("Delete")
        row3.addWidget(self.key_pause_script_combo)
        row3.addSpacing(30)
        lbl7 = QLabel("停止脚本:")
        lbl7.setFixedWidth(label_width)
        lbl7.setToolTip("停止脚本的热键")
        row3.addWidget(lbl7)
        self.key_stop_script_combo = NoScrollComboBox()
        self.key_stop_script_combo.setFixedWidth(combo_width)
        self._populate_script_key_combo(self.key_stop_script_combo)
        self.key_stop_script_combo.setCurrentText("End")
        row3.addWidget(self.key_stop_script_combo)
        row3.addStretch()
        script_key_layout.addLayout(row3)
        
        layout.addWidget(script_key_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        load_key_btn = QPushButton("从配置文件加载")
        load_key_btn.setFixedSize(130, 35)
        load_key_btn.clicked.connect(self.load_key_config)
        btn_layout.addWidget(load_key_btn)
        
        save_key_btn = QPushButton("保存按键配置")
        save_key_btn.setFixedSize(130, 35)
        save_key_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        save_key_btn.clicked.connect(self.save_key_config)
        btn_layout.addWidget(save_key_btn)
        
        reset_key_btn = QPushButton("恢复默认配置")
        reset_key_btn.setFixedSize(130, 35)
        reset_key_btn.clicked.connect(self.reset_key_config)
        btn_layout.addWidget(reset_key_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 说明
        note_group = QGroupBox("说明")
        note_layout = QVBoxLayout(note_group)
        note_layout.setSpacing(4)
        note_layout.setContentsMargins(8, 8, 8, 8)
        note_layout.addWidget(QLabel("• 游戏按键需要与游戏内设置保持一致"))
        note_layout.addWidget(QLabel("• 脚本控制按键用于控制脚本的启动、暂停和停止"))
        note_layout.addWidget(QLabel("• 修改后点击'保存按键配置'使配置生效"))
        note_layout.addWidget(QLabel("• 配置保存在 dnf/dnf_config.py 文件中"))
        layout.addWidget(note_group)
        
        layout.addStretch()
        
        # 延迟加载配置（等 log_text 创建后再加载）
        QTimer.singleShot(100, self.load_key_config)
        
        scroll.setWidget(widget)
        return scroll
    
    def _populate_key_combo(self, combo):
        """填充游戏按键下拉框"""
        keys = [
            "小键盘0", "小键盘1", "小键盘2", "小键盘3", "小键盘4",
            "小键盘5", "小键盘6", "小键盘7", "小键盘8", "小键盘9",
            "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
            "左Ctrl", "右Ctrl", "左Alt", "右Alt", "左Shift", "右Shift",
            "Space", "Enter", "Tab", "Esc", "Backspace",
            "Insert", "Delete", "Home", "End", "PageUp", "PageDown",
            "上", "下", "左", "右"
        ]
        combo.addItems(keys)
        combo.setMaxVisibleItems(12)
        combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
    
    def _populate_script_key_combo(self, combo):
        """填充脚本控制按键下拉框"""
        keys = [
            "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
            "Delete", "End", "Home", "Insert", "PageUp", "PageDown",
            "Pause", "ScrollLock", "PrintScreen"
        ]
        combo.addItems(keys)
        combo.setMaxVisibleItems(12)
        combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
    
    def _key_display_to_code(self, display_name):
        """将显示名称转换为代码表示"""
        key_map = {
            "小键盘0": "numpad_0", "小键盘1": "KeyCode.from_vk(97)", "小键盘2": "numpad_2",
            "小键盘3": "KeyCode.from_vk(99)", "小键盘4": "KeyCode.from_vk(100)",
            "小键盘5": "KeyCode.from_vk(101)", "小键盘6": "KeyCode.from_vk(102)",
            "小键盘7": "numpad_7", "小键盘8": "KeyCode.from_vk(104)",
            "小键盘9": "KeyCode.from_vk(105)",
            "F1": "Key.f1", "F2": "Key.f2", "F3": "Key.f3", "F4": "Key.f4",
            "F5": "Key.f5", "F6": "Key.f6", "F7": "Key.f7", "F8": "Key.f8",
            "F9": "Key.f9", "F10": "Key.f10", "F11": "Key.f11", "F12": "Key.f12",
            "左Ctrl": "Key.ctrl_l", "右Ctrl": "Key.ctrl_r",
            "左Alt": "Key.alt_l", "右Alt": "Key.alt_r",
            "左Shift": "Key.shift_l", "右Shift": "Key.shift_r",
            "Space": "Key.space", "Enter": "Key.enter", "Tab": "Key.tab",
            "Esc": "Key.esc", "Backspace": "Key.backspace",
            "Insert": "Key.insert", "Delete": "Key.delete",
            "Home": "Key.home", "End": "Key.end",
            "PageUp": "Key.page_up", "PageDown": "Key.page_down",
            "上": "Key.up", "下": "Key.down", "左": "Key.left", "右": "Key.right",
            "Pause": "Key.pause", "ScrollLock": "Key.scroll_lock",
            "PrintScreen": "Key.print_screen"
        }
        return key_map.get(display_name, f"Key.{display_name.lower()}")
    
    def _key_code_to_display(self, code_str):
        """将代码表示转换为显示名称"""
        code_map = {
            "numpad_0": "小键盘0", "KeyCode.from_vk(96)": "小键盘0",
            "KeyCode.from_vk(97)": "小键盘1", "numpad_2": "小键盘2",
            "KeyCode.from_vk(98)": "小键盘2", "KeyCode.from_vk(99)": "小键盘3",
            "KeyCode.from_vk(100)": "小键盘4", "KeyCode.from_vk(101)": "小键盘5",
            "KeyCode.from_vk(102)": "小键盘6", "numpad_7": "小键盘7",
            "KeyCode.from_vk(103)": "小键盘7", "KeyCode.from_vk(104)": "小键盘8",
            "KeyCode.from_vk(105)": "小键盘9",
            "Key.f1": "F1", "Key.f2": "F2", "Key.f3": "F3", "Key.f4": "F4",
            "Key.f5": "F5", "Key.f6": "F6", "Key.f7": "F7", "Key.f8": "F8",
            "Key.f9": "F9", "Key.f10": "F10", "Key.f11": "F11", "Key.f12": "F12",
            "Key.ctrl_l": "左Ctrl", "Key.ctrl_r": "右Ctrl",
            "Key.alt_l": "左Alt", "Key.alt_r": "右Alt",
            "Key.shift_l": "左Shift", "Key.shift_r": "右Shift",
            "Key.space": "Space", "Key.enter": "Enter", "Key.tab": "Tab",
            "Key.esc": "Esc", "Key.backspace": "Backspace",
            "Key.insert": "Insert", "Key.delete": "Delete",
            "Key.home": "Home", "Key.end": "End",
            "Key.page_up": "PageUp", "Key.page_down": "PageDown",
            "Key.up": "上", "Key.down": "下", "Key.left": "左", "Key.right": "右",
            "Key.pause": "Pause", "Key.scroll_lock": "ScrollLock",
            "Key.print_screen": "PrintScreen",
            "f10": "F10", "delete": "Delete", "end": "End"
        }
        return code_map.get(code_str, code_str)
    
    def load_key_config(self, _=None):
        """从 dnf_config.py 加载按键配置"""
        try:
            config_path = os.path.join(PROJECT_ROOT, 'dnf', 'dnf_config.py')
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import re
            
            # 解析 key_try_again
            match = re.search(r'key_try_again\s*=\s*(\S+)', content)
            if match:
                val = match.group(1)
                display = self._key_code_to_display(val)
                idx = self.key_try_again_combo.findText(display)
                if idx >= 0:
                    self.key_try_again_combo.setCurrentIndex(idx)
            
            # 解析 key_return_to_town
            match = re.search(r'key_return_to_town\s*=\s*(\S+)', content)
            if match:
                val = match.group(1)
                display = self._key_code_to_display(val)
                idx = self.key_return_town_combo.findText(display)
                if idx >= 0:
                    self.key_return_town_combo.setCurrentIndex(idx)
            
            # 解析 Key_collect_loot
            match = re.search(r'Key_collect_loot\s*=\s*(\S+)', content)
            if match:
                val = match.group(1)
                display = self._key_code_to_display(val)
                idx = self.key_collect_loot_combo.findText(display)
                if idx >= 0:
                    self.key_collect_loot_combo.setCurrentIndex(idx)
            
            # 解析 Key_collect_role
            match = re.search(r'Key_collect_role\s*=\s*(\S+)', content)
            if match:
                val = match.group(1)
                display = self._key_code_to_display(val)
                idx = self.key_collect_role_combo.findText(display)
                if idx >= 0:
                    self.key_collect_role_combo.setCurrentIndex(idx)
            
            # 解析 key_start_script
            match = re.search(r"key_start_script\s*=\s*['\"]?(\w+)['\"]?", content)
            if match:
                val = match.group(1)
                display = self._key_code_to_display(val)
                idx = self.key_start_script_combo.findText(display)
                if idx >= 0:
                    self.key_start_script_combo.setCurrentIndex(idx)
            
            # 解析 key_pause_script
            match = re.search(r'key_pause_script\s*=\s*\{keyboard\.Key\.(\w+)\}', content)
            if match:
                val = match.group(1)
                display = self._key_code_to_display(val.capitalize())
                idx = self.key_pause_script_combo.findText(display)
                if idx >= 0:
                    self.key_pause_script_combo.setCurrentIndex(idx)
            
            # 解析 key_stop_script
            match = re.search(r'key_stop_script\s*=\s*\{keyboard\.Key\.(\w+)\}', content)
            if match:
                val = match.group(1)
                display = self._key_code_to_display(val.capitalize())
                idx = self.key_stop_script_combo.findText(display)
                if idx >= 0:
                    self.key_stop_script_combo.setCurrentIndex(idx)
            
            self.log("按键配置已加载")
        except Exception as e:
            self.log(f"加载按键配置失败: {e}")
    
    def save_key_config(self, _=None):
        """保存按键配置到 dnf_config.py"""
        try:
            config_path = os.path.join(PROJECT_ROOT, 'dnf', 'dnf_config.py')
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import re
            
            # 获取选择的按键
            try_again = self._key_display_to_code(self.key_try_again_combo.currentText())
            return_town = self._key_display_to_code(self.key_return_town_combo.currentText())
            collect_loot = self._key_display_to_code(self.key_collect_loot_combo.currentText())
            collect_role = self._key_display_to_code(self.key_collect_role_combo.currentText())
            start_script = self.key_start_script_combo.currentText().lower()
            pause_script = self.key_pause_script_combo.currentText().lower()
            stop_script = self.key_stop_script_combo.currentText().lower()
            
            # 替换配置
            content = re.sub(r'(key_try_again\s*=\s*)\S+', f'\\1{try_again}', content)
            content = re.sub(r'(key_return_to_town\s*=\s*)\S+', f'\\1{return_town}', content)
            content = re.sub(r'(Key_collect_loot\s*=\s*)\S+', f'\\1{collect_loot}', content)
            content = re.sub(r'(Key_collect_role\s*=\s*)\S+', f'\\1{collect_role}', content)
            content = re.sub(r"(key_start_script\s*=\s*)['\"]?\w+['\"]?", f"\\1'{start_script}'", content)
            content = re.sub(r'(key_pause_script\s*=\s*)\{keyboard\.Key\.\w+\}', f'\\1{{keyboard.Key.{pause_script}}}', content)
            content = re.sub(r'(key_stop_script\s*=\s*)\{keyboard\.Key\.\w+\}', f'\\1{{keyboard.Key.{stop_script}}}', content)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 重新加载 dnf_config 模块使配置立即生效
            import importlib
            import dnf.dnf_config
            importlib.reload(dnf.dnf_config)
            
            # 如果脚本正在运行，重新注册热键
            hotkey_reloaded = False
            try:
                if 'dnf.stronger.main' in sys.modules:
                    stronger_main = sys.modules['dnf.stronger.main']
                    if hasattr(stronger_main, 'reload_hotkeys'):
                        stop_key, pause_key = stronger_main.reload_hotkeys()
                        hotkey_reloaded = True
                        self.log(f"热键已重新注册: 停止={stop_key}, 暂停={pause_key}")
            except Exception as e:
                self.log(f"重新注册热键失败: {e}")
            
            self.log("按键配置已保存并生效")
            msg = "按键配置已保存！" + ("\n热键已立即生效。" if hotkey_reloaded else "\n下次启动脚本时生效。")
            QMessageBox.information(self, "成功", msg)
        except Exception as e:
            self.log(f"保存按键配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {e}")
    
    def reset_key_config(self, _=None):
        """恢复默认按键配置"""
        reply = QMessageBox.question(self, "确认", "确定要恢复默认按键配置吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.key_try_again_combo.setCurrentText("小键盘0")
            self.key_return_town_combo.setCurrentText("F12")
            self.key_collect_loot_combo.setCurrentText("右Ctrl")
            self.key_collect_role_combo.setCurrentText("小键盘7")
            self.key_start_script_combo.setCurrentText("F10")
            self.key_pause_script_combo.setCurrentText("Delete")
            self.key_stop_script_combo.setCurrentText("End")
            self.log("按键配置已恢复默认值")
    
    def _create_skill_bar_tab(self):
        """创建技能栏配置选项卡"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)
        
        label_width = 50
        combo_width = 80
        
        # 技能栏第一行
        row1_group = QGroupBox("技能栏第一行 (上排)")
        row1_layout = QVBoxLayout(row1_group)
        row1_layout.setSpacing(8)
        row1_layout.setContentsMargins(10, 10, 10, 10)
        
        row1 = QHBoxLayout()
        # 槽位1
        row1.addWidget(QLabel("槽位1:"))
        self.skill_slot_1 = QLineEdit("q")
        self.skill_slot_1.setFixedWidth(combo_width)
        row1.addWidget(self.skill_slot_1)
        row1.addSpacing(15)
        # 槽位2
        row1.addWidget(QLabel("槽位2:"))
        self.skill_slot_2 = QLineEdit("w")
        self.skill_slot_2.setFixedWidth(combo_width)
        row1.addWidget(self.skill_slot_2)
        row1.addSpacing(15)
        # 槽位3
        row1.addWidget(QLabel("槽位3:"))
        self.skill_slot_3 = QLineEdit("e")
        self.skill_slot_3.setFixedWidth(combo_width)
        row1.addWidget(self.skill_slot_3)
        row1.addSpacing(15)
        # 槽位4
        row1.addWidget(QLabel("槽位4:"))
        self.skill_slot_4 = QLineEdit("r")
        self.skill_slot_4.setFixedWidth(combo_width)
        row1.addWidget(self.skill_slot_4)
        row1.addSpacing(15)
        # 槽位5
        row1.addWidget(QLabel("槽位5:"))
        self.skill_slot_5 = QLineEdit("t")
        self.skill_slot_5.setFixedWidth(combo_width)
        row1.addWidget(self.skill_slot_5)
        row1.addSpacing(15)
        # 槽位6
        row1.addWidget(QLabel("槽位6:"))
        self.skill_slot_6 = QLineEdit("ctrl_l")
        self.skill_slot_6.setFixedWidth(combo_width)
        row1.addWidget(self.skill_slot_6)
        row1.addSpacing(15)
        # 槽位7
        row1.addWidget(QLabel("槽位7:"))
        self.skill_slot_7 = QLineEdit("")
        self.skill_slot_7.setFixedWidth(combo_width)
        self.skill_slot_7.setPlaceholderText("空")
        row1.addWidget(self.skill_slot_7)
        row1.addStretch()
        row1_layout.addLayout(row1)
        layout.addWidget(row1_group)
        
        # 技能栏第二行
        row2_group = QGroupBox("技能栏第二行 (下排)")
        row2_layout = QVBoxLayout(row2_group)
        row2_layout.setSpacing(8)
        row2_layout.setContentsMargins(10, 10, 10, 10)
        
        row2 = QHBoxLayout()
        # 槽位8
        row2.addWidget(QLabel("槽位1:"))
        self.skill_slot_8 = QLineEdit("a")
        self.skill_slot_8.setFixedWidth(combo_width)
        row2.addWidget(self.skill_slot_8)
        row2.addSpacing(15)
        # 槽位9
        row2.addWidget(QLabel("槽位2:"))
        self.skill_slot_9 = QLineEdit("s")
        self.skill_slot_9.setFixedWidth(combo_width)
        row2.addWidget(self.skill_slot_9)
        row2.addSpacing(15)
        # 槽位10
        row2.addWidget(QLabel("槽位3:"))
        self.skill_slot_10 = QLineEdit("d")
        self.skill_slot_10.setFixedWidth(combo_width)
        row2.addWidget(self.skill_slot_10)
        row2.addSpacing(15)
        # 槽位11
        row2.addWidget(QLabel("槽位4:"))
        self.skill_slot_11 = QLineEdit("f")
        self.skill_slot_11.setFixedWidth(combo_width)
        row2.addWidget(self.skill_slot_11)
        row2.addSpacing(15)
        # 槽位12
        row2.addWidget(QLabel("槽位5:"))
        self.skill_slot_12 = QLineEdit("g")
        self.skill_slot_12.setFixedWidth(combo_width)
        row2.addWidget(self.skill_slot_12)
        row2.addSpacing(15)
        # 槽位13
        row2.addWidget(QLabel("槽位6:"))
        self.skill_slot_13 = QLineEdit("h")
        self.skill_slot_13.setFixedWidth(combo_width)
        row2.addWidget(self.skill_slot_13)
        row2.addSpacing(15)
        # 槽位14
        row2.addWidget(QLabel("槽位7:"))
        self.skill_slot_14 = QLineEdit("alt_l")
        self.skill_slot_14.setFixedWidth(combo_width)
        row2.addWidget(self.skill_slot_14)
        row2.addStretch()
        row2_layout.addLayout(row2)
        layout.addWidget(row2_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        load_skill_btn = QPushButton("从配置文件加载")
        load_skill_btn.setFixedSize(130, 35)
        load_skill_btn.clicked.connect(self.load_skill_bar_config)
        btn_layout.addWidget(load_skill_btn)
        
        save_skill_btn = QPushButton("保存技能栏配置")
        save_skill_btn.setFixedSize(130, 35)
        save_skill_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        save_skill_btn.clicked.connect(self.save_skill_bar_config)
        btn_layout.addWidget(save_skill_btn)
        
        reset_skill_btn = QPushButton("恢复默认配置")
        reset_skill_btn.setFixedSize(130, 35)
        reset_skill_btn.clicked.connect(self.reset_skill_bar_config)
        btn_layout.addWidget(reset_skill_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 说明
        note_group = QGroupBox("说明")
        note_layout = QVBoxLayout(note_group)
        note_layout.setSpacing(4)
        note_layout.setContentsMargins(8, 8, 8, 8)
        note_layout.addWidget(QLabel("• 技能栏按键需要与游戏内技能栏设置保持一致"))
        note_layout.addWidget(QLabel("• 普通按键直接输入字母，如: q, w, e, r"))
        note_layout.addWidget(QLabel("• 特殊按键使用: ctrl_l(左Ctrl), alt_l(左Alt), tab, space 等"))
        note_layout.addWidget(QLabel("• 空槽位留空即可"))
        note_layout.addWidget(QLabel("• 配置保存在 dnf/stronger/skill_util.py 文件中"))
        layout.addWidget(note_group)
        
        layout.addStretch()
        
        # 延迟加载配置
        QTimer.singleShot(150, self.load_skill_bar_config)
        
        scroll.setWidget(widget)
        return scroll
    
    def load_skill_bar_config(self, _=None):
        """从 JSON 或 skill_util 模块加载技能栏配置"""
        try:
            import json
            keys = None
            
            # 优先从 JSON 文件加载
            config_path = os.path.join(PROJECT_ROOT, 'skill_bar_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    keys = data.get('ACTUAL_KEYS', [])
            
            # 如果没有 JSON 文件，从模块导入
            if not keys:
                from dnf.stronger.skill_util import ACTUAL_KEYS
                keys = list(ACTUAL_KEYS)
            
            # 映射到输入框
            slot_inputs = [
                self.skill_slot_1, self.skill_slot_2, self.skill_slot_3, self.skill_slot_4,
                self.skill_slot_5, self.skill_slot_6, self.skill_slot_7,
                self.skill_slot_8, self.skill_slot_9, self.skill_slot_10, self.skill_slot_11,
                self.skill_slot_12, self.skill_slot_13, self.skill_slot_14
            ]
            
            for i, key in enumerate(keys):
                if i < len(slot_inputs):
                    slot_inputs[i].setText(key if key else "")
            
            self.log("技能栏配置已加载")
        except Exception as e:
            self.log(f"加载技能栏配置失败: {e}")
    
    def save_skill_bar_config(self, _=None):
        """保存技能栏配置到 JSON 文件"""
        try:
            # 获取所有槽位的值
            slots = [
                self.skill_slot_1.text().strip(),
                self.skill_slot_2.text().strip(),
                self.skill_slot_3.text().strip(),
                self.skill_slot_4.text().strip(),
                self.skill_slot_5.text().strip(),
                self.skill_slot_6.text().strip(),
                self.skill_slot_7.text().strip(),
                self.skill_slot_8.text().strip(),
                self.skill_slot_9.text().strip(),
                self.skill_slot_10.text().strip(),
                self.skill_slot_11.text().strip(),
                self.skill_slot_12.text().strip(),
                self.skill_slot_13.text().strip(),
                self.skill_slot_14.text().strip(),
            ]
            
            # 保存到 JSON 文件
            import json
            config_path = os.path.join(PROJECT_ROOT, 'skill_bar_config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({'ACTUAL_KEYS': slots}, f, ensure_ascii=False, indent=2)
            
            # 更新模块中的变量
            import dnf.stronger.skill_util as skill_util
            skill_util.ACTUAL_KEYS = slots
            
            self.log("技能栏配置已保存并生效")
            QMessageBox.information(self, "成功", "技能栏配置已保存并立即生效！")
        except Exception as e:
            self.log(f"保存技能栏配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {e}")
    
    def reset_skill_bar_config(self, _=None):
        """恢复默认技能栏配置"""
        reply = QMessageBox.question(self, "确认", "确定要恢复默认技能栏配置吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.skill_slot_1.setText("q")
            self.skill_slot_2.setText("w")
            self.skill_slot_3.setText("e")
            self.skill_slot_4.setText("r")
            self.skill_slot_5.setText("t")
            self.skill_slot_6.setText("ctrl_l")
            self.skill_slot_7.setText("")
            self.skill_slot_8.setText("a")
            self.skill_slot_9.setText("s")
            self.skill_slot_10.setText("d")
            self.skill_slot_11.setText("f")
            self.skill_slot_12.setText("g")
            self.skill_slot_13.setText("h")
            self.skill_slot_14.setText("alt_l")
            self.log("技能栏配置已恢复默认值")
    
    def _create_settings_tab(self):
        """创建设置选项卡"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 邮件配置
        mail_group = QGroupBox("邮件提醒配置")
        mail_layout = QVBoxLayout(mail_group)
        mail_layout.setSpacing(6)
        mail_layout.setContentsMargins(8, 8, 8, 8)
        label_width = 85  # 统一标签宽度
        
        # 发件人邮箱
        row1 = QHBoxLayout()
        lbl1 = QLabel("发件人邮箱:")
        lbl1.setFixedWidth(label_width)
        row1.addWidget(lbl1)
        self.mail_sender = QLineEdit()
        self.mail_sender.setFixedSize(300, 28)
        self.mail_sender.setPlaceholderText("发件人邮箱地址")
        row1.addWidget(self.mail_sender)
        row1.addStretch()
        mail_layout.addLayout(row1)
        
        # 授权码
        row2 = QHBoxLayout()
        lbl2 = QLabel("授权码:")
        lbl2.setFixedWidth(label_width)
        row2.addWidget(lbl2)
        self.mail_password = QLineEdit()
        self.mail_password.setFixedSize(300, 28)
        self.mail_password.setPlaceholderText("邮箱授权码（非登录密码）")
        self.mail_password.setEchoMode(QLineEdit.Password)
        row2.addWidget(self.mail_password)
        row2.addStretch()
        mail_layout.addLayout(row2)
        
        # 收件人邮箱
        row3 = QHBoxLayout()
        lbl3 = QLabel("收件人邮箱:")
        lbl3.setFixedWidth(label_width)
        row3.addWidget(lbl3)
        self.mail_receiver = QLineEdit()
        self.mail_receiver.setFixedSize(300, 28)
        self.mail_receiver.setPlaceholderText("收件人邮箱地址")
        row3.addWidget(self.mail_receiver)
        row3.addStretch()
        mail_layout.addLayout(row3)
        
        # SMTP服务器
        row4 = QHBoxLayout()
        lbl4 = QLabel("SMTP服务器:")
        lbl4.setFixedWidth(label_width)
        row4.addWidget(lbl4)
        self.smtp_server = QLineEdit()
        self.smtp_server.setFixedSize(200, 28)
        self.smtp_server.setText("smtp.qq.com")
        self.smtp_server.setPlaceholderText("SMTP服务器")
        row4.addWidget(self.smtp_server)
        lbl_port = QLabel("端口:")
        lbl_port.setFixedWidth(40)
        row4.addWidget(lbl_port)
        self.smtp_port = NoScrollSpinBox()
        self.smtp_port.setFixedSize(80, 28)
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(465)
        row4.addWidget(self.smtp_port)
        row4.addStretch()
        mail_layout.addLayout(row4)
        
        # 邮件按钮 - 与输入框对齐
        row5 = QHBoxLayout()
        spacer = QLabel("")
        spacer.setFixedWidth(label_width)
        row5.addWidget(spacer)
        test_mail_btn = QPushButton("测试邮件")
        test_mail_btn.setFixedSize(100, 30)
        test_mail_btn.clicked.connect(self.test_mail)
        row5.addWidget(test_mail_btn)
        save_mail_btn = QPushButton("保存邮件配置")
        save_mail_btn.setFixedSize(120, 30)
        save_mail_btn.clicked.connect(self.save_mail_config)
        row5.addWidget(save_mail_btn)
        row5.addStretch()
        mail_layout.addLayout(row5)
        
        layout.addWidget(mail_group)
        
        # 执行完成后操作
        finish_group = QGroupBox("执行完成后操作")
        finish_layout = QVBoxLayout(finish_group)
        finish_layout.setSpacing(4)
        finish_layout.setContentsMargins(8, 8, 8, 8)
        self.quit_game_after_finish = QCheckBox("脚本执行完成后退出游戏")
        finish_layout.addWidget(self.quit_game_after_finish)
        self.shutdown_after_finish = QCheckBox("脚本执行完成后关机（需先勾选退出游戏）")
        self.shutdown_after_finish.setToolTip("勾选后，脚本执行完成并退出游戏后，电脑将在60秒后自动关机")
        finish_layout.addWidget(self.shutdown_after_finish)
        layout.addWidget(finish_group)
        
        # 定时启动设置
        schedule_group = QGroupBox("定时启动设置")
        schedule_layout = QVBoxLayout(schedule_group)
        schedule_layout.setSpacing(6)
        schedule_layout.setContentsMargins(8, 8, 8, 8)
        
        # 启用定时启动
        row_enable = QHBoxLayout()
        self.schedule_enabled = QCheckBox("启用定时启动")
        self.schedule_enabled.setToolTip("到达设定时间后自动启动脚本")
        self.schedule_enabled.stateChanged.connect(self.on_schedule_enabled_changed)
        row_enable.addWidget(self.schedule_enabled)
        row_enable.addStretch()
        schedule_layout.addLayout(row_enable)
        
        # 定时时间设置
        row_time = QHBoxLayout()
        lbl_time = QLabel("启动时间:")
        lbl_time.setFixedWidth(label_width)
        row_time.addWidget(lbl_time)
        self.schedule_hour = NoScrollSpinBox()
        self.schedule_hour.setRange(0, 23)
        self.schedule_hour.setValue(2)  # 默认 02 时
        self.schedule_hour.setFixedSize(50, 28)
        self.schedule_hour.valueChanged.connect(self.on_schedule_time_changed)
        row_time.addWidget(self.schedule_hour)
        row_time.addWidget(QLabel("时"))
        self.schedule_minute = NoScrollSpinBox()
        self.schedule_minute.setRange(0, 59)
        self.schedule_minute.setValue(3)  # 默认 03 分
        self.schedule_minute.setFixedSize(50, 28)
        self.schedule_minute.valueChanged.connect(self.on_schedule_time_changed)
        row_time.addWidget(self.schedule_minute)
        row_time.addWidget(QLabel("分"))
        
        # 定时启动模式选择
        lbl_mode = QLabel("启动模式:")
        lbl_mode.setFixedWidth(70)
        row_time.addWidget(lbl_mode)
        self.schedule_mode = NoScrollComboBox()
        self.schedule_mode.setFixedWidth(120)
        self.schedule_mode.addItems(["当前选项卡", "妖气追踪/白图", "深渊模式"])
        self.schedule_mode.currentIndexChanged.connect(self.on_schedule_mode_changed)
        row_time.addWidget(self.schedule_mode)
        row_time.addStretch()
        schedule_layout.addLayout(row_time)
        
        # 定时状态显示
        row_status = QHBoxLayout()
        self.schedule_status_label = QLabel("定时状态: 未启用")
        self.schedule_status_label.setStyleSheet("color: #666;")
        row_status.addWidget(self.schedule_status_label)
        row_status.addStretch()
        schedule_layout.addLayout(row_status)
        
        layout.addWidget(schedule_group)
        
        # 显示设置
        display_group = QGroupBox("显示设置")
        display_layout = QVBoxLayout(display_group)
        display_layout.setSpacing(4)
        display_layout.setContentsMargins(8, 8, 8, 8)
        self.show_detection = QCheckBox("显示检测结果窗口（调试用）")
        display_layout.addWidget(self.show_detection)
        self.enable_pic_log = QCheckBox("启用截图日志")
        self.enable_pic_log.setChecked(True)
        display_layout.addWidget(self.enable_pic_log)
        layout.addWidget(display_group)
        
        # 快捷键说明
        key_group = QGroupBox("快捷键说明")
        key_layout = QVBoxLayout(key_group)
        key_layout.setSpacing(4)
        key_layout.setContentsMargins(8, 8, 8, 8)
        key_layout.addWidget(QLabel("F10 键 - 启动脚本"))
        key_layout.addWidget(QLabel("Delete 键 - 暂停/继续脚本"))
        key_layout.addWidget(QLabel("End 键 - 停止脚本"))
        layout.addWidget(key_group)
        
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll
    
    def test_mail(self, _=None):
        """测试邮件发送"""
        sender = self.mail_sender.text().strip()
        password = self.mail_password.text().strip()
        receiver = self.mail_receiver.text().strip()
        smtp_server = self.smtp_server.text().strip()
        smtp_port = self.smtp_port.value()
        
        if not all([sender, password, receiver, smtp_server]):
            QMessageBox.warning(self, "警告", "请填写完整的邮件配置")
            return
        
        try:
            from utils.mail_sender import EmailSender
            test_config = {
                'sender': sender,
                'password': password,
                'receiver': receiver,
                'smtp_server': smtp_server,
                'smtp_port': smtp_port
            }
            mail_sender = EmailSender(test_config)
            mail_sender.send_email("DNF脚本测试邮件", "这是一封测试邮件，如果您收到说明邮件配置正确。", receiver)
            QMessageBox.information(self, "成功", "测试邮件已发送，请检查收件箱")
            self.log("测试邮件已发送")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发送失败: {str(e)}")
            self.log(f"测试邮件发送失败: {e}")
    
    def save_mail_config(self, _=None):
        """保存邮件配置到.env文件"""
        sender = self.mail_sender.text().strip()
        password = self.mail_password.text().strip()
        receiver = self.mail_receiver.text().strip()
        smtp_server = self.smtp_server.text().strip()
        smtp_port = self.smtp_port.value()
        
        env_path = os.path.join(PROJECT_ROOT, '.env')
        env_content = f"""# 邮件配置 - 由GUI自动生成
# 发件人邮箱
DNF_MAIL_SENDER={sender}
# 邮箱授权码（不是登录密码）
DNF_MAIL_PASSWORD={password}
# SMTP服务器（默认QQ邮箱）
DNF_SMTP_SERVER={smtp_server}
# SMTP端口
DNF_SMTP_PORT={smtp_port}
# 收件人邮箱
DNF_MAIL_RECEIVER={receiver}
"""
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            QMessageBox.information(self, "成功", "邮件配置已保存到 .env 文件")
            self.log("邮件配置已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def load_mail_config(self):
        """从.env文件加载邮件配置"""
        env_path = os.path.join(PROJECT_ROOT, '.env')
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            if key == 'DNF_MAIL_SENDER':
                                self.mail_sender.setText(value)
                            elif key == 'DNF_MAIL_PASSWORD':
                                self.mail_password.setText(value)
                            elif key == 'DNF_MAIL_RECEIVER':
                                self.mail_receiver.setText(value)
                            elif key == 'DNF_SMTP_SERVER':
                                self.smtp_server.setText(value)
                            elif key == 'DNF_SMTP_PORT':
                                try:
                                    self.smtp_port.setValue(int(value))
                                except:
                                    pass
                # 检查配置是否完整
                sender = self.mail_sender.text().strip()
                password = self.mail_password.text().strip()
                if sender and password:
                    self._mail_config_msg = "邮件配置已加载"
                else:
                    self._mail_config_msg = "邮件配置不完整，发送功能可能无法正常工作"
            except Exception as e:
                self._mail_config_msg = f"加载邮件配置失败: {e}"
        else:
            self._mail_config_msg = "邮件配置不完整，发送功能可能无法正常工作"
    
    def _show_mail_config_log(self):
        """显示邮件配置日志（在预加载完成后调用）"""
        if hasattr(self, '_mail_config_msg'):
            self.log(self._mail_config_msg)
    
    def start_hotkey_listener(self):
        """启动热键监听"""
        self.hotkey_listener = HotkeyListener()
        self.hotkey_listener.start_signal.connect(self.start_script)
        self.hotkey_listener.stop_signal.connect(self.stop_script)
        self.hotkey_listener.pause_signal.connect(self.pause_script)
        self.hotkey_listener.start()
    
    def init_schedule_timer(self):
        """初始化定时启动定时器"""
        self.schedule_timer = QTimer(self)
        self.schedule_timer.timeout.connect(self.check_schedule_time)
        self.schedule_timer.start(1000)  # 每秒检查一次
        self._last_triggered_minute = -1  # 防止同一分钟重复触发
        self.update_schedule_status()
    
    def preload_modules(self):
        """后台预加载重量级模块，加速脚本启动"""
        self._preload_done = False
        self.start_btn.setEnabled(False)
        self.start_btn.setText("加载中...")
        
        # 创建预加载线程（进度窗口由main函数管理）
        self._preload_worker = PreloadWorker()
        self._preload_worker.progress_signal.connect(self._on_preload_progress)
        self._preload_worker.finished_signal.connect(self._on_preload_finished)
        self._preload_worker.start()
    
    def _on_preload_progress(self, percent):
        """预加载进度更新"""
        pass  # 进度由外部窗口处理
    
    def _on_preload_finished(self, success, message):
        """预加载完成回调"""
        self._preload_done = True
        self.log(message)
        self._show_mail_config_log()  # 显示邮件配置状态
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶ 启动 (F10)")
    
    def on_schedule_enabled_changed(self, state):
        """定时启动开关变化"""
        self.update_schedule_status()
        if state:
            self.log(f"定时启动已启用，将在 {self.schedule_hour.value():02d}:{self.schedule_minute.value():02d} 自动启动")
        else:
            self.log("定时启动已禁用")
    
    def on_schedule_time_changed(self, value):
        """定时时间改变"""
        self.update_schedule_status()
        self._last_triggered_minute = -1  # 重置触发记录
    
    def on_schedule_mode_changed(self, index):
        """定时模式改变"""
        self.update_schedule_status()
    
    def update_schedule_status(self):
        """更新定时状态显示"""
        if self.schedule_enabled.isChecked():
            time_str = f"{self.schedule_hour.value():02d}:{self.schedule_minute.value():02d}"
            mode_text = self.schedule_mode.currentText()
            self.schedule_status_label.setText(f"定时状态: 将在 {time_str} 启动 [{mode_text}]")
            self.schedule_status_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        else:
            self.schedule_status_label.setText("定时状态: 未启用")
            self.schedule_status_label.setStyleSheet("color: #666;")
    
    def check_schedule_time(self, _=None):
        """检查是否到达定时启动时间"""
        if not self.schedule_enabled.isChecked():
            return
        
        # 如果脚本已在运行，不重复启动
        if self.worker and self.worker.isRunning():
            return
        
        current_time = QTime.currentTime()
        current_minute = current_time.hour() * 60 + current_time.minute()
        schedule_minute = self.schedule_hour.value() * 60 + self.schedule_minute.value()
        
        # 检查是否到达设定时间（同一分钟内只触发一次）
        if current_minute == schedule_minute and self._last_triggered_minute != current_minute:
            self._last_triggered_minute = current_minute
            self.log(f"定时启动触发！当前时间: {current_time.toString('HH:mm:ss')}")
            self.scheduled_start()
    
    def scheduled_start(self):
        """定时启动脚本"""
        mode_index = self.schedule_mode.currentIndex()
        
        if mode_index == 0:  # 当前选项卡
            self.start_script()
        elif mode_index == 1:  # 妖气追踪/白图
            self.tabs.setCurrentIndex(0)
            QTimer.singleShot(100, self.start_script)
        elif mode_index == 2:  # 深渊模式
            self.tabs.setCurrentIndex(1)
            QTimer.singleShot(100, self.start_script)
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg_lower = message.lower()
        
        # 根据日志类型设置颜色
        if 'error' in msg_lower or '错误' in message or '失败' in message:
            color = '#8B0000'  # 深红色 - 错误
        elif 'warning' in msg_lower or '警告' in message or 'warn' in msg_lower:
            color = '#fb8c00'  # 橙色 - 警告
        elif 'info' in msg_lower:
            color = '#228B22'  # 绿色 - INFO
        elif '完成' in message or '成功' in message or '已启动' in message or '已加载' in message:
            color = '#228B22'  # 绿色 - 成功
        elif '停止' in message or '暂停' in message:
            color = '#1e88e5'  # 蓝色 - 状态变化
        else:
            color = '#333333'  # 默认深灰色
        
        self.log_text.append(f'<span style="color:{color}">[{timestamp}] {message}</span>')
        self.log_text.moveCursor(QTextCursor.End)
        
        # 限制日志行数，防止内存泄漏
        self._trim_log_lines()
    
    def _trim_log_lines(self, max_lines=1000):
        """限制日志行数，防止内存泄漏"""
        doc = self.log_text.document()
        if doc.blockCount() > max_lines:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, doc.blockCount() - max_lines)
            cursor.removeSelectedText()
            self.log_text.moveCursor(QTextCursor.End)
    
    def clear_log(self, _=None):
        self.log_text.clear()
    
    # 角色配置管理
    def load_role_config(self):
        """加载角色配置"""
        if os.path.exists(ROLE_CONFIG_FILE):
            try:
                with open(ROLE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.role_config = json.load(f)
            except:
                pass
    
    def save_role_config(self):
        """保存角色配置"""
        with open(ROLE_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.role_config, f, ensure_ascii=False, indent=2)
    
    def load_gui_config(self):
        """加载GUI配置"""
        if os.path.exists(GUI_CONFIG_FILE):
            try:
                with open(GUI_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.gui_config = json.load(f)
            except:
                pass
    
    def save_gui_config(self):
        """保存GUI配置"""
        config = {
            # 妖气追踪/白图配置
            'game_mode': self.mode_group.checkedId(),
            'account_code': self.stronger_account_combo.currentData() or 'account1',
            'first_role': self.first_role.value(),
            'last_role': self.last_role.value(),
            'skip_role_enabled': self.skip_role_enabled.isChecked(),
            'skip_role_list': self.skip_role_list.text(),
            'stronger_uniform': self.stronger_uniform.isChecked(),
            'stronger_fatigue': self.stronger_fatigue.value(),
            'buy_tank': self.buy_tank.currentIndex(),
            'buy_bell': self.buy_bell.currentIndex(),
            'buy_ssm': self.buy_ssm.currentIndex(),
            'buy_catalyst': self.buy_catalyst.currentIndex(),
            # 深渊配置
            'abyss_account_code': self.abyss_account_combo.currentData() or 'account1',
            'abyss_first': self.abyss_first.value(),
            'abyss_last': self.abyss_last.value(),
            'abyss_skip_role_enabled': self.abyss_skip_role_enabled.isChecked(),
            'abyss_skip_role_list': self.abyss_skip_role_list.text(),
            'abyss_uniform': self.abyss_uniform.isChecked(),
            'abyss_fatigue': self.abyss_fatigue.value(),
            'abyss_tank': self.abyss_tank.currentIndex(),
            'abyss_bell': self.abyss_bell.currentIndex(),
            'abyss_ssm': self.abyss_ssm.currentIndex(),
            'abyss_catalyst': self.abyss_catalyst.currentIndex(),
            # 执行完成后操作（都不保存，每次默认关闭）
            # 'quit_game_after_finish' 不保存，每次默认关闭
            # 'shutdown_after_finish' 不保存，每次默认关闭
            # 设置
            # 'show_detection' 不保存，每次默认关闭
            'enable_pic_log': self.enable_pic_log.isChecked(),
            # 定时启动设置（只保存时间和模式，不保存启用状态）
            # 'schedule_enabled' 不保存，每次默认关闭
            'schedule_hour': self.schedule_hour.value(),
            'schedule_minute': self.schedule_minute.value(),
            'schedule_mode': self.schedule_mode.currentIndex(),
            # 当前选项卡
            'current_tab': self.tabs.currentIndex()
        }
        with open(GUI_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def apply_gui_config(self):
        """应用保存的GUI配置"""
        if not self.gui_config:
            self.log("没有找到保存的配置")
            return
        try:
            c = self.gui_config
            
            # 妖气追踪/白图配置
            if 'game_mode' in c:
                btn = self.mode_group.button(c['game_mode'])
                if btn:
                    btn.setChecked(True)
            if 'account_code' in c:
                idx = self.stronger_account_combo.findData(c['account_code'])
                if idx >= 0:
                    self.stronger_account_combo.setCurrentIndex(idx)
            if 'first_role' in c:
                self.first_role.setValue(c['first_role'])
            if 'last_role' in c:
                self.last_role.setValue(c['last_role'])
            if 'skip_role_enabled' in c:
                self.skip_role_enabled.setChecked(c['skip_role_enabled'])
            if 'skip_role_list' in c:
                self.skip_role_list.setText(c['skip_role_list'])
            if 'stronger_uniform' in c:
                self.stronger_uniform.setChecked(c['stronger_uniform'])
            if 'stronger_fatigue' in c:
                self.stronger_fatigue.setValue(c['stronger_fatigue'])
            if 'buy_tank' in c:
                self.buy_tank.setCurrentIndex(c['buy_tank'])
            if 'buy_bell' in c:
                self.buy_bell.setCurrentIndex(c['buy_bell'])
            if 'buy_ssm' in c:
                self.buy_ssm.setCurrentIndex(c['buy_ssm'])
            if 'buy_catalyst' in c:
                self.buy_catalyst.setCurrentIndex(c['buy_catalyst'])
            # 深渊配置
            if 'abyss_account_code' in c:
                idx = self.abyss_account_combo.findData(c['abyss_account_code'])
                if idx >= 0:
                    self.abyss_account_combo.setCurrentIndex(idx)
            if 'abyss_first' in c:
                self.abyss_first.setValue(c['abyss_first'])
            if 'abyss_last' in c:
                self.abyss_last.setValue(c['abyss_last'])
            if 'abyss_skip_role_enabled' in c:
                self.abyss_skip_role_enabled.setChecked(c['abyss_skip_role_enabled'])
            if 'abyss_skip_role_list' in c:
                self.abyss_skip_role_list.setText(c['abyss_skip_role_list'])
            if 'abyss_uniform' in c:
                self.abyss_uniform.setChecked(c['abyss_uniform'])
            if 'abyss_fatigue' in c:
                self.abyss_fatigue.setValue(c['abyss_fatigue'])
            if 'abyss_tank' in c:
                self.abyss_tank.setCurrentIndex(c['abyss_tank'])
            if 'abyss_bell' in c:
                self.abyss_bell.setCurrentIndex(c['abyss_bell'])
            if 'abyss_ssm' in c:
                self.abyss_ssm.setCurrentIndex(c['abyss_ssm'])
            if 'abyss_catalyst' in c:
                self.abyss_catalyst.setCurrentIndex(c['abyss_catalyst'])

            # 执行完成后操作（都不加载，每次默认关闭）
            # quit_game_after_finish 不加载，每次默认关闭
            # shutdown_after_finish 不加载，每次默认关闭
            # 设置
            # show_detection 不加载，每次默认关闭
            if 'enable_pic_log' in c:
                self.enable_pic_log.setChecked(c['enable_pic_log'])
            # 定时启动设置（只加载时间和模式，启用状态每次默认关闭）
            # schedule_enabled 不加载，每次默认关闭
            if 'schedule_hour' in c:
                self.schedule_hour.setValue(c['schedule_hour'])
            if 'schedule_minute' in c:
                self.schedule_minute.setValue(c['schedule_minute'])
            if 'schedule_mode' in c:
                self.schedule_mode.setCurrentIndex(c['schedule_mode'])
            # 不再恢复选项卡，每次打开默认显示第一个选项卡
            # if 'current_tab' in c:
            #     self.tabs.setCurrentIndex(c['current_tab'])
            # 日志显示界面实际值（配置应用后）
            self.log(f"正在加载配置: 起始角色={self.first_role.value()}, 结束角色={self.last_role.value()}")
            self.log("已加载上次配置")
        except Exception as e:
            self.log(f"加载配置失败: {e}")
    
    def get_current_account_key(self):
        """获取当前选中的账号key"""
        if hasattr(self, 'account_combo'):
            return self.account_combo.currentData() or 'account1'
        return 'account1'
    
    def _get_account_names(self):
        """获取账号名称映射"""
        return self.role_config.get('account_names', {})
    
    def _refresh_account_combo(self):
        """刷新所有账号下拉框"""
        account_names = self._get_account_names()
        
        # 获取所有账号key
        account_keys = [k for k in self.role_config.keys() if k != 'account_names']
        
        # 刷新角色配置页面的下拉框
        self._refresh_single_account_combo(self.account_combo, account_keys, account_names)
        
        # 刷新白图页面的下拉框
        if hasattr(self, 'stronger_account_combo'):
            self._refresh_single_account_combo(self.stronger_account_combo, account_keys, account_names)
        
        # 刷新深渊页面的下拉框
        if hasattr(self, 'abyss_account_combo'):
            self._refresh_single_account_combo(self.abyss_account_combo, account_keys, account_names)
    
    def _refresh_single_account_combo(self, combo, account_keys, account_names):
        """刷新单个账号下拉框"""
        combo.blockSignals(True)
        current_key = combo.currentData() if combo.count() > 0 else None
        combo.clear()
        
        for key in account_keys:
            display_name = account_names.get(key, key.replace('account', '账号'))
            combo.addItem(display_name, key)
        
        if current_key:
            idx = combo.findData(current_key)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        
        combo.blockSignals(False)
    
    def add_account(self, _=None):
        """添加新账号"""
        # 弹出输入框让用户输入账号名称
        name, ok = QInputDialog.getText(self, "添加账号", "请输入账号名称:")
        if not ok or not name.strip():
            return
        
        name = name.strip()
        
        # 找到下一个可用的账号编号
        existing_nums = []
        for key in self.role_config.keys():
            if key.startswith('account') and key != '_account_names':
                try:
                    num = int(key.replace('account', ''))
                    existing_nums.append(num)
                except:
                    pass
        next_num = max(existing_nums) + 1 if existing_nums else 1
        new_key = f'account{next_num}'
        
        self.role_config[new_key] = []
        # 确保account_names存在
        if 'account_names' not in self.role_config:
            self.role_config['account_names'] = {}
        self.role_config['account_names'][new_key] = name
        self.save_role_config()
        self._refresh_account_combo()
        
        # 选中新账号
        idx = self.account_combo.findData(new_key)
        if idx >= 0:
            self.account_combo.setCurrentIndex(idx)
        
        self.log(f"已添加账号: {name}")
    
    def rename_account(self, _=None):
        """重命名当前账号"""
        key = self.get_current_account_key()
        account_names = self._get_account_names()
        current_name = account_names.get(key, key.replace('account', '账号'))
        
        name, ok = QInputDialog.getText(self, "重命名账号", "请输入新名称:", text=current_name)
        if not ok or not name.strip():
            return
        
        # 确保account_names存在
        if 'account_names' not in self.role_config:
            self.role_config['account_names'] = {}
        self.role_config['account_names'][key] = name.strip()
        self.save_role_config()
        self._refresh_account_combo()
        self.log(f"已重命名账号: {name.strip()}")
    
    def _save_account_names(self):
        """保存账号名称（随role_config一起保存）"""
        self.save_role_config()
    
    def delete_account(self, _=None):
        """删除当前账号"""
        if len([k for k in self.role_config.keys() if k != 'account_names']) <= 1:
            QMessageBox.warning(self, "警告", "至少需要保留一个账号")
            return
        
        key = self.get_current_account_key()
        account_names = self._get_account_names()
        display_name = account_names.get(key, key.replace('account', '账号'))
        role_count = len(self.role_config.get(key, []))
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除 {display_name} 吗？\n该账号下有 {role_count} 个角色将被删除。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.role_config[key]
            # 删除账号名称
            if 'account_names' in self.role_config and key in self.role_config['account_names']:
                del self.role_config['account_names'][key]
            self.save_role_config()
            self._refresh_account_combo()
            self.refresh_role_table()
            self.log(f"已删除账号: {display_name}")
    
    def refresh_role_table(self, _=None):
        """刷新角色表格"""
        key = self.get_current_account_key()
        roles = self.role_config.get(key, [])
        self.role_table.setRowCount(len(roles))
        for i, role in enumerate(roles):
            self.role_table.setItem(i, 0, QTableWidgetItem(str(role.get('no', i + 1))))
            self.role_table.setItem(i, 1, QTableWidgetItem(role.get('name', '')))
            self.role_table.setItem(i, 2, QTableWidgetItem(str(role.get('height', 150))))
            self.role_table.setItem(i, 3, QTableWidgetItem(str(role.get('fatigue_all', 188))))
            self.role_table.setItem(i, 4, QTableWidgetItem(str(role.get('fatigue_reserved', 0))))
            self.role_table.setItem(i, 5, QTableWidgetItem("是" if role.get('buff_effective') else "否"))
            # 提取技能信息
            skills = role.get('custom_priority_skills', [])
            skill_display = []
            for s in skills:
                if isinstance(s, str):
                    # 兼容旧格式（直接是字符串）
                    skill_display.append(f"普通按键[{s}]")
                elif isinstance(s, dict):
                    skill_type = s.get('type', '')
                    if skill_type == 'str':
                        # 普通按键
                        skill_display.append(f"普通按键[{s.get('value', '')}]")
                    elif skill_type == 'key':
                        # 特殊按键
                        key_val = s.get('value', '').replace('Key.', '')
                        skill_display.append(f"特殊按键[{key_val}]")
                    elif skill_type == 'skill':
                        # 判断是引爆技能、组合技能还是自定义技能
                        cmd = s.get('command', [])
                        hotkey_cd = s.get('hotkey_cd_command_cast', False)
                        is_detonate = len(cmd) == 4 and cmd[1] == '' and cmd[2] == ''
                        key = s.get('hot_key', '') or s.get('name', '')
                        if is_detonate:
                            skill_display.append(f"引爆技能[{key}]")
                        elif hotkey_cd:
                            skill_display.append(f"组合技能[{key}]")
                        else:
                            skill_display.append(f"自定义[{key}]")
                    else:
                        # 未知类型，展示为自定义
                        key = s.get('hot_key', '') or s.get('name', '') or s.get('value', '')
                        skill_display.append(f"自定义[{key}]")
            # 提取大招信息并合并到技能展示
            powerful_skills = role.get('powerful_skills', [])
            powerful_display = []
            for s in powerful_skills:
                if isinstance(s, str):
                    powerful_display.append(s)
                elif isinstance(s, dict):
                    skill_type = s.get('type', '')
                    if skill_type == 'str':
                        powerful_display.append(s.get('value', ''))
                    elif skill_type == 'key':
                        powerful_display.append(s.get('value', '').replace('Key.', ''))
                    else:
                        powerful_display.append(s.get('hot_key', '') or s.get('name', '') or s.get('value', ''))
            
            # 合并展示：技能 + 大招
            all_display = ' || '.join(skill_display)
            if powerful_display:
                all_display += f" 【大招: {' | '.join(powerful_display)}】"
            self.role_table.setItem(i, 6, QTableWidgetItem(all_display))
    
    def add_role(self, _=None):
        """添加角色"""
        key = self.get_current_account_key()
        # 计算默认编号：已有角色中最大编号 + 1
        existing_nos = [r.get('no', 0) for r in self.role_config[key]]
        default_no = max(existing_nos) + 1 if existing_nos else 1
        dialog = RoleEditDialog(self, default_no=default_no)
        if dialog.exec_() == QDialog.Accepted:
            role_data = dialog.get_data()
            self.role_config[key].append(role_data)
            self.save_role_config()
            self.refresh_role_table()
            self.log(f"已添加角色: {role_data['name']}")
    
    def edit_role(self, _=None):
        """编辑角色"""
        row = self.role_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选择要编辑的角色")
            return
        key = self.get_current_account_key()
        role_data = self.role_config[key][row].copy()  # 使用副本避免直接修改
        old_no = role_data.get('no', row + 1)
        dialog = RoleEditDialog(self, role_data)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            new_no = new_data.get('no', old_no)
            
            # 更新角色数据
            self.role_config[key][row] = new_data
            
            # 如果编号改变了，处理编号冲突
            if new_no != old_no:
                roles = self.role_config[key]
                # 找出其他角色中编号 >= new_no 的，让它们编号+1
                for r in roles:
                    if r is not new_data and r.get('no', 0) >= new_no:
                        r['no'] = r.get('no', 0) + 1
            
            # 按编号重新排序
            self.role_config[key].sort(key=lambda x: x.get('no', 999))
            self.save_role_config()
            self.refresh_role_table()
            self.log(f"已更新角色: {new_data['name']} (编号: {new_no})")
    
    def delete_role(self, _=None):
        """删除角色"""
        row = self.role_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选择要删除的角色")
            return
        key = self.get_current_account_key()
        name = self.role_config[key][row].get('name', '')
        if QMessageBox.question(self, "确认", f"确定删除角色 '{name}'?") == QMessageBox.Yes:
            del self.role_config[key][row]
            self.save_role_config()
            self.refresh_role_table()
            self.log(f"已删除角色: {name}")
    
    def move_role_up(self, _=None):
        """上移角色"""
        row = self.role_table.currentRow()
        if row <= 0:
            return
        self._swap_roles(row, row - 1)
        self.role_table.selectRow(row - 1)
    
    def move_role_down(self, _=None):
        """下移角色"""
        row = self.role_table.currentRow()
        key = self.get_current_account_key()
        if row < 0 or row >= len(self.role_config[key]) - 1:
            return
        self._swap_roles(row, row + 1)
        self.role_table.selectRow(row + 1)
    
    def _swap_roles(self, row1, row2):
        """交换两个角色的位置（不自动保存）"""
        key = self.get_current_account_key()
        roles = self.role_config[key]
        
        # 交换位置
        roles[row1], roles[row2] = roles[row2], roles[row1]
        
        # 重新分配编号
        for i, r in enumerate(roles):
            r['no'] = i + 1
        
        self.refresh_role_table()
        name = roles[row2].get('name', '')
        self.log(f"已移动角色 '{name}'（未保存）")
    
    def save_role_changes(self, _=None):
        """保存角色配置更改"""
        self.save_role_config()
        self.log("已保存角色配置")
    

    
    def force_sync_from_code(self, _=None):
        """从role_list.py强制同步角色配置到JSON（完整覆盖）"""
        reply = QMessageBox.warning(
            self, "确认强制同步", 
            "此操作将用role_list.py中的配置完整覆盖JSON文件！\n\n"
            "您在JSON中对角色的修改（如疲劳值、技能等）将会丢失。\n\n"
            "是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            from dnf.stronger.role_config_manager import export_from_role_list
            
            # 导出全部账号
            export_from_role_list(1)
            export_from_role_list(2)
            
            # 重新加载配置
            self.load_role_config()
            self._refresh_account_combo()  # 刷新账号下拉框
            self.refresh_role_table()
            
            count1 = len(self.role_config.get('account1', []))
            count2 = len(self.role_config.get('account2', []))
            self.log(f"已强制同步角色配置: 账号1={count1}个, 账号2={count2}个")
            QMessageBox.information(self, "成功", f"已强制同步角色配置\n账号1: {count1}个角色\n账号2: {count2}个角色")
        except Exception as e:
            import traceback
            self.log(f"强制同步失败: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"强制同步失败: {str(e)}")

    def start_script(self, _=None):
        """启动脚本"""
        # 检查worker是否真正在运行
        if self.worker and self.worker.isRunning():
            # 检查脚本模块的停止标志，如果已经设置了停止，说明脚本正在退出中
            try:
                if 'dnf.stronger.main' in sys.modules:
                    mod = sys.modules['dnf.stronger.main']
                    if mod.stop_be_pressed:
                        self.log("等待上一次脚本完全停止...")
                        self.worker.wait(2000)  # 等待最多2秒
                        if self.worker.isRunning():
                            self.worker.terminate()
                            self.worker.wait(500)
                        self.log("上一次脚本已停止")
                    else:
                        self.log("脚本已在运行中")
                        return
                else:
                    self.log("脚本已在运行中")
                    return
            except Exception:
                self.log("脚本已在运行中")
                return
        
        # 重置停止标志（确保下次能正常启动）
        try:
            if 'dnf.stronger.main' in sys.modules:
                sys.modules['dnf.stronger.main'].stop_be_pressed = False
            if 'dnf.abyss.main' in sys.modules:
                sys.modules['dnf.abyss.main'].stop_be_pressed = False
        except Exception:
            pass
        
        current_tab = self.tabs.currentIndex()
        
        if current_tab == 0:  # 妖气追踪
            # 解析跳过角色列表
            skip_list = []
            if self.skip_role_enabled.isChecked() and self.skip_role_list.text().strip():
                try:
                    skip_list = [int(x.strip()) for x in self.skip_role_list.text().split(',') if x.strip()]
                except:
                    self.log("跳过角色列表格式错误，已忽略")
            
            config = {
                'game_mode': self.mode_group.checkedId(),
                'account_code': self.stronger_account_combo.currentData() or 'account1',
                'account_name': self.stronger_account_combo.currentText(),
                'first_role': self.first_role.value(),
                'last_role': self.last_role.value(),
                'show_detection': self.show_detection.isChecked(),
                'enable_uniform_pl': self.stronger_uniform.isChecked(),
                'fatigue_reserved': self.stronger_fatigue.value(),
                'break_role': self.skip_role_enabled.isChecked(),
                'break_role_no': skip_list,
                'buy_tank': self.buy_tank.currentIndex(),
                'buy_bell': self.buy_bell.currentIndex(),
                'buy_ssm': self.buy_ssm.currentIndex(),
                'buy_catalyst': self.buy_catalyst.currentIndex(),
                'quit_game_after_finish': self.quit_game_after_finish.isChecked(),
                'shutdown_after_finish': self.shutdown_after_finish.isChecked()
            }
            skip_info = f", 跳过角色={skip_list}" if skip_list else ""
            self.log(f"启动配置: 模式={config['game_mode']}, 角色={config['first_role']}-{config['last_role']}{skip_info}")
            self.worker = ScriptWorker("stronger", config)
        elif current_tab == 1:  # 深渊
            # 解析跳过角色列表
            abyss_skip_list = []
            if self.abyss_skip_role_enabled.isChecked() and self.abyss_skip_role_list.text().strip():
                try:
                    abyss_skip_list = [int(x.strip()) for x in self.abyss_skip_role_list.text().split(',') if x.strip()]
                except:
                    self.log("跳过角色列表格式错误，已忽略")
            
            config = {
                'account_code': self.abyss_account_combo.currentData() or 'account1',
                'account_name': self.abyss_account_combo.currentText(),
                'first_role': self.abyss_first.value(),
                'last_role': self.abyss_last.value(),
                'show_detection': self.show_detection.isChecked(),
                'enable_uniform_pl': self.abyss_uniform.isChecked(),
                'fatigue_reserved': self.abyss_fatigue.value(),
                'break_role': self.abyss_skip_role_enabled.isChecked(),
                'break_role_no': abyss_skip_list,
                'buy_tank': self.abyss_tank.currentIndex(),
                'buy_bell': self.abyss_bell.currentIndex(),
                'buy_ssm': self.abyss_ssm.currentIndex(),
                'buy_catalyst': self.abyss_catalyst.currentIndex(),
                'quit_game_after_finish': self.quit_game_after_finish.isChecked(),
                'shutdown_after_finish': self.shutdown_after_finish.isChecked()
            }
            skip_info = f", 跳过角色={abyss_skip_list}" if abyss_skip_list else ""
            self.log(f"启动配置: 账号={config['account_code']}, 角色={config['first_role']}-{config['last_role']}{skip_info}")
            self.worker = ScriptWorker("abyss", config)
        elif current_tab == 2:  # 角色列表
            self.refresh_role_table()
            return
        else:
            self.log("请切换到妖气追踪或深渊模式后启动")
            return
        
        self.worker.log_signal.connect(self.on_log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()
        
        # 播放启动提示音
        try:
            import config as config_
            threading.Thread(target=lambda: winsound.PlaySound(config_.sound1, winsound.SND_FILENAME), daemon=True).start()
        except Exception as e:
            self.log(f"播放提示音失败: {e}")
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.is_paused = False
        self.statusBar().showMessage("运行中...")
        self.log("脚本已启动")
    
    def stop_script(self, _=None):
        """停止脚本"""
        if not self.worker or not self.worker.isRunning():
            return
        
        # 防止重复停止
        if hasattr(self, '_stopping') and self._stopping:
            return
        self._stopping = True
        
        self.log("正在停止脚本...")
        
        # 播放停止提示音
        try:
            import config as config_
            threading.Thread(target=lambda: winsound.PlaySound(config_.sound2, winsound.SND_FILENAME), daemon=True).start()
        except:
            pass
        
        # 设置脚本模块的停止标志
        self.worker.request_stop()
        
        # 等待一段时间后检查是否停止，如果没停止则强制终止
        def force_stop():
            if self.worker and self.worker.isRunning():
                self.log("脚本未响应停止信号，正在强制终止...")
                self.worker.terminate()
                self.worker.wait(1000)
                self.on_finished()
        
        QTimer.singleShot(3000, force_stop)
    
    def pause_script(self, _=None):
        """暂停/继续脚本"""
        if not self.worker or not self.worker.isRunning():
            return
        
        # 播放暂停提示音
        try:
            import config as config_
            threading.Thread(target=lambda: winsound.PlaySound(config_.sound3, winsound.SND_FILENAME), daemon=True).start()
        except:
            pass
        
        # 直接操作脚本的pause_event
        result = self.worker.request_pause()
        if result is True:
            self.is_paused = True
            self.pause_btn.setText("▶ 继续 (Del)")
            self.log("脚本已暂停")
            self.statusBar().showMessage("已暂停")
        elif result is False:
            self.is_paused = False
            self.pause_btn.setText("⏸ 暂停 (Del)")
            self.log("脚本继续运行")
            self.statusBar().showMessage("运行中...")
        else:
            self.log("暂停操作失败")
    
    def on_log(self, message):
        """接收日志"""
        msg_lower = message.lower()
        
        # 根据日志类型设置颜色
        if 'error' in msg_lower or '错误' in message or '失败' in message:
            color = '#8B0000'  # 深红色 - 错误
        elif 'warning' in msg_lower or '警告' in message or 'warn' in msg_lower:
            color = '#fb8c00'  # 橙色 - 警告
        elif 'info' in msg_lower:
            color = '#228B22'  # 绿色 - INFO
        elif '完成' in message or '成功' in message:
            color = '#228B22'  # 绿色 - 成功
        elif 'debug' in msg_lower:
            color = '#666666'  # 灰色 - DEBUG
        else:
            color = '#333333'  # 默认深灰色
        
        self.log_text.append(f'<span style="color:{color}">{message}</span>')
        self.log_text.moveCursor(QTextCursor.End)
        
        # 限制日志行数，防止内存泄漏
        self._trim_log_lines()
    
    def on_finished(self, _=None):
        """脚本结束"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ 暂停 (Del)")
        self.is_paused = False
        self._stopping = False  # 重置停止标志
        self.statusBar().showMessage("就绪 - F10启动 | Delete暂停 | End停止")
        self.log("脚本已停止")
        
        # 重置脚本模块的停止标志，确保下次能正常启动
        try:
            if 'dnf.stronger.main' in sys.modules:
                sys.modules['dnf.stronger.main'].stop_be_pressed = False
            if 'dnf.abyss.main' in sys.modules:
                sys.modules['dnf.abyss.main'].stop_be_pressed = False
        except Exception:
            pass
        
        # 清理 worker 引用，帮助垃圾回收
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
    
    def closeEvent(self, event):
        """关闭窗口"""
        # 保存配置
        try:
            self.save_gui_config()
            self.log("配置已保存")
        except Exception as e:
            self.log(f"保存配置失败: {e}")
        
        # 停止定时器
        if hasattr(self, 'schedule_timer') and self.schedule_timer:
            self.schedule_timer.stop()
        
        # 停止热键监听
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener.wait(1000)
            self.hotkey_listener.deleteLater()
            self.hotkey_listener = None
        
        # 停止脚本
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(self, "确认", "脚本正在运行，确定要退出吗？",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return
            self.stop_script()
            self.worker.wait(3000)
            self.worker.deleteLater()
            self.worker = None
        
        event.accept()


def check_single_instance():
    """检测程序是否已经在运行（使用互斥锁）"""
    import ctypes
    
    kernel32 = ctypes.windll.kernel32
    mutex_name = "DNF_AutoScript_Mutex_723323692"
    
    # 尝试创建互斥锁
    mutex = kernel32.CreateMutexW(None, True, mutex_name)
    last_error = kernel32.GetLastError()
    
    # ERROR_ALREADY_EXISTS = 183
    if last_error == 183:
        kernel32.CloseHandle(mutex)
        return False, "程序已经在运行中，请勿重复启动！"
    
    return True, mutex


def check_dnf_running():
    """检测DNF游戏是否已启动"""
    try:
        from utils.window_utils import get_window_handle
        from dnf import window_title
        get_window_handle(window_title)
        return True, window_title
    except Exception:
        return False, None


def main():
    # 先检测程序是否重复运行（在创建QApplication之前）
    is_single, result = check_single_instance()
    if not is_single:
        # 需要先创建QApplication才能显示消息框
        temp_app = QApplication(sys.argv)
        QMessageBox.warning(None, "警告", result)
        sys.exit(1)
    mutex = result  # 保存互斥锁，程序退出时自动释放
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 检测DNF游戏是否启动
    dnf_running, dnf_title = check_dnf_running()
    if not dnf_running:
        QMessageBox.warning(
            None, "提示", 
            "未检测到DNF游戏窗口！\n\n请先启动游戏，再运行本程序。"
        )
        sys.exit(0)
    
    # 设置窗口图标（任务栏图标）
    icon_path = os.path.join(PROJECT_ROOT, 'assets', 'img', 'img_gui', 'favicon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 登录验证
    from utils.login_dialog import LoginDialog
    from utils.auth import start_heartbeat_thread, is_verified
    
    login_dialog = LoginDialog()
    if login_dialog.exec_() != QDialog.Accepted:
        sys.exit(0)
    
    # 启动心跳检测线程（每5分钟验证一次）
    start_heartbeat_thread(300)
    
    # 背景图路径
    bg_path = os.path.join(PROJECT_ROOT, 'assets', 'img', 'img_gui', 'shenjie.jpg')
    bg_url = bg_path.replace('\\', '/')
    
    # 设置应用样式 - 简洁清晰主题
    style = """
        /* 主窗口背景*/
        QMainWindow {
            background-image: url("BG_PATH");
            background-repeat: no-repeat;
            background-position: center;
        }
        QMainWindow > QWidget#centralWidget {
            background: transparent;
        }
        
        /* 全局字体 */
        QWidget {
            font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            font-size: 12px;
            color: #333333;
        }
        
        /* 分组框*/
        QGroupBox {
            border: 1px solid rgba(176, 196, 222, 180);
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: rgba(255, 255, 255, 160);
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
            color: #2c5aa0;
            font-weight: bold;
        }
        
        /* 选项卡*/
        QTabWidget::pane {
            border: 1px solid rgba(176, 196, 222, 180);
            border-radius: 5px;
            background-color: rgba(255, 255, 255, 140);
            top: -1px;
        }
        QTabBar::tab {
            background-color: rgba(232, 240, 248, 200);
            color: #333333;
            padding: 8px 18px;
            margin-right: 2px;
            border: 1px solid rgba(176, 196, 222, 180);
            border-bottom: none;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        QTabBar::tab:selected {
            background-color: rgba(255, 255, 255, 220);
            color: #2c5aa0;
            font-weight: bold;
            border-bottom: 1px solid rgba(255, 255, 255, 220);
        }
        QTabBar::tab:hover:!selected {
            background-color: rgba(245, 249, 252, 220);
            color: #2c5aa0;
        }
        
        /* 按钮 */
        QPushButton {
            padding: 6px 16px;
            background-color: rgba(232, 240, 248, 200);
            border: 1px solid rgba(176, 196, 222, 180);
            border-radius: 4px;
            color: #333333;
        }
        QPushButton:hover {
            background-color: rgba(208, 228, 247, 220);
            border-color: #7ba7d7;
        }
        QPushButton:pressed {
            background-color: rgba(184, 212, 240, 240);
        }
        QPushButton:disabled {
            background-color: rgba(224, 224, 224, 180);
            color: #999999;
            border-color: #cccccc;
        }
        
        /* 输入框 */
        QSpinBox, QComboBox, QLineEdit {
            background-color: rgba(255, 255, 255, 200);
            border: 1px solid rgba(176, 196, 222, 180);
            border-radius: 3px;
            padding: 4px 6px;
            color: #333333;
            min-height: 20px;
        }
        QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
            border-color: #5b9bd5;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            width: 0px;
            border: none;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox::down-arrow {
            width: 12px;
            height: 12px;
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            border: 1px solid #b0c4de;
            selection-background-color: #cce5ff;
            color: #333333;
        }
        
        /* 文本框 */
        QTextEdit {
            background-color: rgba(255, 255, 255, 180);
            border: 1px solid rgba(176, 196, 222, 180);
            border-radius: 4px;
            color: #2e7d32;
        }
        
        /* 单选框和复选框 */
        QRadioButton, QCheckBox {
            color: #333333;
            spacing: 6px;
        }
        QRadioButton::indicator, QCheckBox::indicator {
            width: 14px;
            height: 14px;
        }
        
        /* 表格 */
        QTableWidget {
            background-color: rgba(255, 255, 255, 180);
            border: 1px solid rgba(176, 196, 222, 180);
            gridline-color: #d0d0d0;
            color: #333333;
            selection-background-color: rgba(255, 235, 205, 220);
            selection-color: #333333;
        }
        QHeaderView::section {
            background-color: rgba(232, 240, 248, 200);
            color: #2c5aa0;
            padding: 5px;
            border: 1px solid rgba(176, 196, 222, 180);
            font-weight: bold;
        }
        
        /* 状态栏 */
        QStatusBar {
            background-color: rgba(255, 255, 255, 160);
            color: #333333;
        }
        
        /* 标签 */
        QLabel {
            color: #333333;
        }
        
        /* 滚动区域 */
        QScrollArea {
            background: transparent;
            border: none;
        }
        QScrollArea > QWidget > QWidget {
            background: transparent;
        }
        
        /* 滚动条 */
        QScrollBar:vertical {
            background: #f0f0f0;
            width: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #c0c0c0;
            border-radius: 5px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background: #a0a0a0;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """
    app.setStyleSheet(style.replace('BG_PATH', bg_url))
    
    # 创建独立的加载进度窗口
    from PyQt5.QtWidgets import QProgressDialog
    from PyQt5.QtCore import Qt
    
    progress = QProgressDialog("正在加载模块...", None, 0, 100)
    progress.setWindowTitle("初始化")
    progress.setWindowModality(Qt.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.setCancelButton(None)
    progress.setAutoClose(False)
    progress.setMinimumWidth(300)
    progress.setStyleSheet("""
        QProgressDialog { background-color: white; }
        QProgressBar {
            border: 1px solid #bbb;
            border-radius: 5px;
            text-align: center;
            height: 22px;
            background-color: #e0e0e0;
        }
        QProgressBar::chunk {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4CAF50, stop:1 #81C784);
            border-radius: 4px;
        }
    """)
    progress.setValue(0)
    progress.show()
    QApplication.processEvents()
    
    # 创建主窗口（会触发预加载）
    window = MainWindow()
    
    # 连接预加载信号到独立进度窗口
    if hasattr(window, '_preload_worker'):
        window._preload_worker.progress_signal.connect(lambda p: (progress.setValue(p), QApplication.processEvents()))
        window._preload_worker.finished_signal.connect(lambda s, m: (progress.close(), window.show()))
    else:
        progress.close()
        window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
