# -*- coding:utf-8 -*-
"""
登录对话框 - 简洁版
"""

import os
import sys
import configparser

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QApplication, QMenu, QAction, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

from utils.auth import verify_card, get_card_expire_info, unbind_card, get_machine_code, get_unbind_info

# 卡密保存路径
CARD_CONFIG_PATH = "C:\\LT.ini"


def load_saved_card():
    """加载保存的卡密"""
    try:
        if os.path.exists(CARD_CONFIG_PATH):
            config = configparser.ConfigParser()
            config.read(CARD_CONFIG_PATH, encoding='utf-8')
            return config.get('Auth', 'card_key', fallback='')
    except:
        pass
    return ''


def save_card(card_key):
    """保存卡密"""
    try:
        config = configparser.ConfigParser()
        config['Auth'] = {'card_key': card_key}
        with open(CARD_CONFIG_PATH, 'w', encoding='utf-8') as f:
            config.write(f)
    except:
        pass


def clear_saved_card():
    """清除保存的卡密"""
    try:
        if os.path.exists(CARD_CONFIG_PATH):
            os.remove(CARD_CONFIG_PATH)
    except:
        pass


class ChineseLineEdit(QLineEdit):
    """带中文右键菜单的输入框"""
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        cut_action = QAction("剪切", self)
        cut_action.triggered.connect(self.cut)
        cut_action.setEnabled(self.hasSelectedText() and not self.isReadOnly())
        menu.addAction(cut_action)
        
        copy_action = QAction("复制", self)
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(self.hasSelectedText())
        menu.addAction(copy_action)
        
        paste_action = QAction("粘贴", self)
        paste_action.triggered.connect(self.paste)
        paste_action.setEnabled(not self.isReadOnly())
        menu.addAction(paste_action)
        
        menu.addSeparator()
        
        select_all_action = QAction("全选", self)
        select_all_action.triggered.connect(self.selectAll)
        select_all_action.setEnabled(len(self.text()) > 0)
        menu.addAction(select_all_action)
        
        menu.exec_(event.globalPos())


class LoginDialog(QDialog):
    """登录对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.card_info = None
        self.init_ui()
        
        # 加载保存的卡密
        saved_card = load_saved_card()
        if saved_card:
            self.card_input.setText(saved_card)
            self.remember_check.setChecked(True)
            self.status_label.setText("已加载保存的卡密")
        else:
            self.status_label.setText("请输入卡密登录")
    
    def init_ui(self):
        self.setWindowTitle("LT")
        self.setFixedSize(380, 240)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 设置窗口图标
        icon_path = os.path.join(PROJECT_ROOT, 'assets', 'img', 'img_gui', 'favicon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # 标题
        title = QLabel("DNF自动化脚本")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c5aa0;")
        layout.addWidget(title)
        
        # 卡密输入（使用中文右键菜单）
        card_layout = QHBoxLayout()
        
        self.card_input = ChineseLineEdit()
        self.card_input.setPlaceholderText("请输入卡密...")
        self.card_input.setFixedHeight(35)
        self.card_input.returnPressed.connect(self.do_login)
        card_layout.addWidget(self.card_input)
        
        # 记住卡密复选框
        self.remember_check = QCheckBox("记住")
        self.remember_check.setStyleSheet("color: #666;")
        card_layout.addWidget(self.remember_check)
        
        layout.addLayout(card_layout)
        
        # 按钮行
        btn_layout = QHBoxLayout()
        
        self.login_btn = QPushButton("登录")
        self.login_btn.setFixedHeight(38)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2c5aa0;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #3d6bb3; }
            QPushButton:pressed { background-color: #1e4080; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.login_btn.clicked.connect(self.do_login)
        btn_layout.addWidget(self.login_btn, 2)
        
        self.unbind_btn = QPushButton("解绑")
        self.unbind_btn.setFixedHeight(38)
        self.unbind_btn.setFixedWidth(70)
        self.unbind_btn.setToolTip("解绑卡密（扣除8小时）")
        self.unbind_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #666;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #e8e8e8; color: #333; }
        """)
        self.unbind_btn.clicked.connect(self.do_unbind)
        btn_layout.addWidget(self.unbind_btn)
        
        exit_btn = QPushButton("退出")
        exit_btn.setFixedHeight(38)
        exit_btn.setFixedWidth(70)
        exit_btn.clicked.connect(self.reject)
        btn_layout.addWidget(exit_btn)
        
        layout.addLayout(btn_layout)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def do_login(self):
        """执行登录"""
        card_key = self.card_input.text().strip()
        
        if not card_key:
            self.status_label.setText("请输入卡密")
            self.status_label.setStyleSheet("color: #c62828; font-size: 12px;")
            return
        
        self.login_btn.setEnabled(False)
        self.status_label.setText("正在验证...")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        QApplication.processEvents()
        
        # 验证卡密
        success, message, card_info = verify_card(card_key)
        
        if success:
            self.card_info = card_info
            expire_info = get_card_expire_info(card_key)
            
            # 构建到期信息
            if expire_info:
                days = expire_info.get('days_left', -1)
                hours = expire_info.get('hours_left', 0)
                minutes = expire_info.get('minutes_left', 0)
                seconds = expire_info.get('seconds_left', 0)
                expire_dt = expire_info.get('expire_datetime', '')
                if days >= 0:
                    if days > 0:
                        time_msg = f"剩余时间: {days}天{hours}时{minutes}分{seconds}秒\n到期时间: {expire_dt}"
                    else:
                        time_msg = f"剩余时间: {hours}时{minutes}分{seconds}秒\n到期时间: {expire_dt}"
                else:
                    time_msg = "永久有效"
            else:
                time_msg = "验证成功"
            
            self.status_label.setText("验证成功！")
            self.status_label.setStyleSheet("color: #2e7d32; font-size: 12px;")
            QApplication.processEvents()
            
            # 保存或清除卡密
            if self.remember_check.isChecked():
                save_card(card_key)
            else:
                clear_saved_card()
            
            # 弹出确认框显示剩余时间
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("登录成功")
            msg_box.setText(f"卡密验证成功！\n\n{time_msg}")
            msg_box.setIcon(QMessageBox.Information)
            confirm_btn = msg_box.addButton("确认", QMessageBox.AcceptRole)
            msg_box.exec_()
            
            self.accept()
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #c62828; font-size: 12px;")
            self.login_btn.setEnabled(True)
    
    def do_unbind(self):
        """解绑当前设备"""
        card_key = self.card_input.text().strip()
        
        if not card_key:
            self.status_label.setText("请先输入要解绑的卡密")
            self.status_label.setStyleSheet("color: #c62828; font-size: 12px;")
            return
        
        # 先查询解绑信息
        self.status_label.setText("正在查询...")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        QApplication.processEvents()
        
        success, info = get_unbind_info(card_key)
        
        if not success:
            self.status_label.setText(info)  # info 是错误消息
            self.status_label.setStyleSheet("color: #c62828; font-size: 12px;")
            return
        
        remaining = info.get('remaining', 0)
        deduct_hours = info.get('deduct_hours', 8)
        is_bound = info.get('is_bound', False)
        is_current_device = info.get('is_current_device', False)
        
        if not is_bound:
            self.status_label.setText("该卡密未绑定设备")
            self.status_label.setStyleSheet("color: #c62828; font-size: 12px;")
            return
        
        if remaining <= 0:
            self.status_label.setText("解绑次数已用完")
            self.status_label.setStyleSheet("color: #c62828; font-size: 12px;")
            return
        
        # 显示确认框，包含剩余次数
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认解绑")
        msg_box.setText(f"解绑将扣除{deduct_hours}小时使用时间\n\n剩余解绑次数: {remaining}次\n\n确定要解绑吗？")
        msg_box.setIcon(QMessageBox.Question)
        yes_btn = msg_box.addButton("确定", QMessageBox.YesRole)
        no_btn = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(no_btn)
        msg_box.exec_()
        
        if msg_box.clickedButton() != yes_btn:
            self.status_label.setText("请输入卡密登录")
            self.status_label.setStyleSheet("color: #666; font-size: 12px;")
            return
        
        self.status_label.setText("正在解绑...")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        QApplication.processEvents()
        
        success, message, expire_info = unbind_card(card_key)
        
        if success:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #2e7d32; font-size: 12px;")
            
            # 使用解绑接口返回的到期时间（不再调用verify避免重新绑定）
            if expire_info:
                days = expire_info.get('days_left', -1)
                hours = expire_info.get('hours_left', 0)
                minutes = expire_info.get('minutes_left', 0)
                seconds = expire_info.get('seconds_left', 0)
                expire_dt = expire_info.get('expire_datetime', '')
                if days >= 0:
                    if days > 0:
                        time_msg = f"剩余时间: {days}天{hours}时{minutes}分{seconds}秒\n到期时间: {expire_dt}"
                    else:
                        time_msg = f"剩余时间: {hours}时{minutes}分{seconds}秒\n到期时间: {expire_dt}"
                else:
                    time_msg = "永久有效"
                
                QMessageBox.information(self, "解绑成功", f"{message}\n\n{time_msg}")
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #c62828; font-size: 12px;")
    
    def get_card_info(self):
        """获取登录后的卡密信息"""
        return self.card_info
