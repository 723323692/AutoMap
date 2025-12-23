# -*- coding:utf-8 -*-
"""
卡密生成器 - 网络版本（连接服务器管理卡密）
"""

import os
import sys
import json
import random
import string
import requests
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QSpinBox, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QLineEdit, QTextEdit,
    QInputDialog, QFileDialog, QCheckBox, QDialog, QFormLayout, QDialogButtonBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

# 配置
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'card_generator_config.json')


def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'server_url': 'http://123.207.83.152:5000', 'api_secret': 'BabyBus2024SecretKey'}


def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _calc_checksum(data, salt='BabyBusCard2024'):
    """计算校验码（4位）"""
    import hashlib
    hash_str = hashlib.md5(f"{data}{salt}".encode()).hexdigest().upper()
    # 取哈希的特定位置组成4位校验码
    return hash_str[0] + hash_str[7] + hash_str[15] + hash_str[31]


def verify_card_format(card_key):
    """验证卡密格式是否正确（本地校验）"""
    if not card_key or len(card_key) != 34:
        return False
    
    # 检查前缀
    prefix = card_key[:2]
    valid_prefixes = ['TK', 'ZK', 'YK', 'JK', 'NK', 'SK', 'YJ']
    if prefix not in valid_prefixes:
        return False
    
    # 验证校验码
    main_part = card_key[:30]  # 前缀 + 28位随机
    checksum = card_key[30:]   # 最后4位校验码
    expected = _calc_checksum(main_part)
    
    return checksum == expected


def generate_card_key(expire_days=None):
    """
    生成卡密（34位 = 2位前缀 + 28位随机 + 4位校验码）
    前缀规则：
    - TK: 1天
    - ZK: 7天
    - YK: 30天
    - JK: 90天
    - NK: 180天
    - SK: 365天
    - YJ: 永久
    """
    # 根据有效期确定前缀
    prefix_map = {
        1: 'TK',    # 天卡
        7: 'ZK',    # 周卡
        30: 'YK',   # 月卡
        90: 'JK',   # 季卡
        180: 'NK',  # 半年卡
        365: 'SK',  # 年卡
        None: 'YJ'  # 永久
    }
    prefix = prefix_map.get(expire_days, 'YK')
    
    # 生成28位随机字符
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '').replace('L', '')
    random_part = ''.join(random.choice(chars) for _ in range(28))
    
    # 计算校验码
    main_part = prefix + random_part
    checksum = _calc_checksum(main_part)
    
    # 格式：2位前缀 + 28位随机 + 4位校验码 = 34位
    return main_part + checksum


class ConfigDialog(QDialog):
    """服务器配置对话框"""
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config or {}
        self.setWindowTitle("服务器配置")
        self.setFixedSize(400, 150)
        
        layout = QFormLayout(self)
        
        self.url_input = QLineEdit(self.config.get('server_url', ''))
        self.url_input.setPlaceholderText("http://your-server:5000")
        layout.addRow("服务器地址:", self.url_input)
        
        self.secret_input = QLineEdit(self.config.get('api_secret', ''))
        self.secret_input.setEchoMode(QLineEdit.Password)
        layout.addRow("API密钥:", self.secret_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_config(self):
        return {
            'server_url': self.url_input.text().strip().rstrip('/'),
            'api_secret': self.secret_input.text().strip()
        }


class EditCardDialog(QDialog):
    """编辑卡密对话框"""
    def __init__(self, parent=None, card_key='', card_info=None):
        super().__init__(parent)
        self.card_key = card_key
        self.card_info = card_info or {}
        self.setWindowTitle(f"编辑卡密 - {card_key}")
        self.setFixedSize(450, 350)
        
        layout = QFormLayout(self)
        
        # 卡密（只读）
        card_label = QLabel(card_key)
        card_label.setStyleSheet("color: #2c5aa0; font-weight: bold;")
        layout.addRow("卡密:", card_label)
        
        # 状态
        self.disabled_check = QCheckBox("禁用")
        self.disabled_check.setChecked(bool(self.card_info.get('disabled')))
        layout.addRow("状态:", self.disabled_check)
        
        # 到期时间
        self.expire_input = QLineEdit()
        expire_date = self.card_info.get('expire_date', '')
        self.expire_input.setText(expire_date if expire_date else '')
        self.expire_input.setPlaceholderText("格式: 2025-12-25 12:00:00 (留空=永久)")
        layout.addRow("到期时间:", self.expire_input)
        
        # 有效天数
        self.expire_days_spin = QSpinBox()
        self.expire_days_spin.setRange(0, 9999)
        self.expire_days_spin.setValue(self.card_info.get('expire_days', 0) or 0)
        self.expire_days_spin.setSpecialValueText("永久")
        layout.addRow("有效天数:", self.expire_days_spin)
        
        # 机器码
        self.machine_input = QLineEdit()
        self.machine_input.setText(self.card_info.get('machine_code', '') or '')
        self.machine_input.setPlaceholderText("留空=未绑定")
        layout.addRow("机器码:", self.machine_input)
        
        # 绑定时间
        self.bind_time_input = QLineEdit()
        self.bind_time_input.setText(self.card_info.get('bind_time', '') or '')
        self.bind_time_input.setPlaceholderText("格式: 2025-12-24 12:00:00")
        layout.addRow("绑定时间:", self.bind_time_input)
        
        # 解绑次数（显示已用/最大）
        unbind_layout = QHBoxLayout()
        unbind_used = self.card_info.get('unbind_count', 0) or 0
        self.unbind_used_label = QLabel(f"已用: {unbind_used}")
        unbind_layout.addWidget(self.unbind_used_label)
        
        unbind_layout.addWidget(QLabel("最大:"))
        self.max_unbind_spin = QSpinBox()
        self.max_unbind_spin.setRange(0, 99)
        self.max_unbind_spin.setValue(self.card_info.get('max_unbind_count', 3) if self.card_info.get('max_unbind_count') is not None else 3)
        unbind_layout.addWidget(self.max_unbind_spin)
        unbind_layout.addStretch()
        layout.addRow("解绑次数:", unbind_layout)
        
        # 备注
        self.remark_input = QLineEdit()
        self.remark_input.setText(self.card_info.get('remark', '') or '')
        layout.addRow("备注:", self.remark_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_data(self):
        data = {
            'max_unbind_count': self.max_unbind_spin.value(),
            'remark': self.remark_input.text().strip(),
            'disabled': 1 if self.disabled_check.isChecked() else 0,
        }
        
        expire = self.expire_input.text().strip()
        if expire:
            data['expire_date'] = expire
        
        expire_days = self.expire_days_spin.value()
        if expire_days > 0:
            data['expire_days'] = expire_days
        
        machine = self.machine_input.text().strip()
        data['machine_code'] = machine if machine else None
        
        bind_time = self.bind_time_input.text().strip()
        data['bind_time'] = bind_time if bind_time else None
        
        return data


# 数据库列名到中文的映射
COLUMN_NAME_MAP = {
    'card_key': '卡密',
    'card_type': '类型',
    'expire_date': '到期时间',
    'expire_days': '有效天数',
    'machine_code': '机器码',
    'bind_time': '绑定时间',
    'last_use': '最后使用',
    'last_ip': '最后IP',
    'create_time': '创建时间',
    'remark': '备注',
    'disabled': '禁用',
    'unbind_count': '已用解绑',
    'max_unbind_count': '最大解绑',
    'total_deducted_hours': '累计扣时',
}


def get_chinese_columns(columns):
    """将英文列名转换为中文"""
    return [COLUMN_NAME_MAP.get(col, col) for col in columns]


class BatchTimeDialog(QDialog):
    """批量调整时间对话框"""
    def __init__(self, parent=None, api_request_func=None):
        super().__init__(parent)
        self.api_request = api_request_func
        self.matched_count = 0
        self.matched_cards = []
        self.setWindowTitle("批量调整卡密时间")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout(self)
        
        # 使用标签页
        from PyQt5.QtWidgets import QTabWidget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 标签页1：快捷查询
        quick_tab = QWidget()
        quick_layout = QVBoxLayout(quick_tab)
        
        # 查询条件组
        query_group = QGroupBox("查询条件")
        query_form = QFormLayout(query_group)
        
        # 按激活时间快捷选择
        bind_btn_layout = QHBoxLayout()
        bind_btns = [
            ("今天激活", "bind", 0),
            ("昨天激活", "bind", 1),
            ("3天内激活", "bind", 3),
            ("7天内激活", "bind", 7),
        ]
        for text, qtype, days in bind_btns:
            btn = QPushButton(text)
            btn.setFixedWidth(75)
            btn.clicked.connect(lambda _, t=qtype, d=days: self.set_quick_query(t, d))
            bind_btn_layout.addWidget(btn)
        bind_btn_layout.addStretch()
        query_form.addRow("按激活时间:", bind_btn_layout)
        
        # 按到期时间快捷选择
        expire_btn_layout = QHBoxLayout()
        expire_btns = [
            ("今天到期", "expire", 0),
            ("明天到期", "expire", 1),
            ("3天内到期", "expire", 3),
            ("7天内到期", "expire", 7),
        ]
        for text, qtype, days in expire_btns:
            btn = QPushButton(text)
            btn.setFixedWidth(75)
            btn.clicked.connect(lambda _, t=qtype, d=days: self.set_quick_query(t, d))
            expire_btn_layout.addWidget(btn)
        expire_btn_layout.addStretch()
        query_form.addRow("按到期时间:", expire_btn_layout)
        
        self.bind_before_input = QLineEdit()
        self.bind_before_input.setPlaceholderText("例: 2025-12-23 23:00 (该时间之前激活的)")
        query_form.addRow("激活时间早于:", self.bind_before_input)
        
        self.bind_after_input = QLineEdit()
        self.bind_after_input.setPlaceholderText("例: 2025-12-20 00:00 (该时间之后激活的)")
        query_form.addRow("激活时间晚于:", self.bind_after_input)
        
        self.expire_before_input = QLineEdit()
        self.expire_before_input.setPlaceholderText("例: 2025-12-25 00:00 (该时间之前到期的)")
        query_form.addRow("到期时间早于:", self.expire_before_input)
        
        preview_layout = QHBoxLayout()
        preview_btn = QPushButton("查询")
        preview_btn.clicked.connect(self.preview_query)
        preview_layout.addWidget(preview_btn)
        
        self.match_label = QLabel("匹配: 0 张卡密")
        self.match_label.setStyleSheet("color: #2c5aa0; font-weight: bold;")
        preview_layout.addWidget(self.match_label)
        preview_layout.addStretch()
        query_form.addRow("", preview_layout)
        
        quick_layout.addWidget(query_group)
        
        # 快捷查询结果表格
        self.quick_result_table = QTableWidget()
        self.quick_result_table.setSelectionBehavior(QTableWidget.SelectRows)
        quick_layout.addWidget(self.quick_result_table)
        
        self.tab_widget.addTab(quick_tab, "快捷查询")
        
        # 标签页2：SQL查询
        sql_tab = QWidget()
        sql_layout = QVBoxLayout(sql_tab)
        
        sql_group = QGroupBox("自定义SQL查询")
        sql_form = QVBoxLayout(sql_group)
        
        sql_tip = QLabel("输入SELECT语句查询cards表，例如:\nSELECT * FROM cards WHERE bind_time < '2025-12-23 23:00:00'")
        sql_tip.setStyleSheet("color: #666; font-size: 11px;")
        sql_form.addWidget(sql_tip)
        
        self.sql_input = QTextEdit()
        self.sql_input.setPlaceholderText("SELECT card_key FROM cards WHERE ...")
        self.sql_input.setFixedHeight(80)
        sql_form.addWidget(self.sql_input)
        
        sql_btn_layout = QHBoxLayout()
        exec_sql_btn = QPushButton("执行SQL查询")
        exec_sql_btn.clicked.connect(self.execute_sql)
        sql_btn_layout.addWidget(exec_sql_btn)
        
        self.sql_result_label = QLabel("结果: 0 条")
        self.sql_result_label.setStyleSheet("color: #2c5aa0; font-weight: bold;")
        sql_btn_layout.addWidget(self.sql_result_label)
        sql_btn_layout.addStretch()
        sql_form.addLayout(sql_btn_layout)
        
        sql_layout.addWidget(sql_group)
        
        # SQL结果表格
        self.sql_result_table = QTableWidget()
        self.sql_result_table.setSelectionBehavior(QTableWidget.SelectRows)
        sql_layout.addWidget(self.sql_result_table)
        
        self.tab_widget.addTab(sql_tab, "SQL查询")
        
        # 操作组（公共）
        action_group = QGroupBox("批量操作")
        action_layout = QFormLayout(action_group)
        
        time_layout = QHBoxLayout()
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(-9999, 9999)
        self.hours_spin.setValue(0)
        self.hours_spin.setFixedWidth(80)
        time_layout.addWidget(self.hours_spin)
        time_layout.addWidget(QLabel("小时"))
        
        for text, hours in [("-8h", -8), ("+8h", 8), ("+24h", 24), ("+72h", 72)]:
            btn = QPushButton(text)
            btn.setFixedWidth(50)
            btn.clicked.connect(lambda _, h=hours: self.hours_spin.setValue(h))
            time_layout.addWidget(btn)
        time_layout.addStretch()
        action_layout.addRow("调整时间:", time_layout)
        
        tip = QLabel("正数=增加时间，负数=减少时间")
        tip.setStyleSheet("color: #666; font-size: 11px;")
        action_layout.addRow("", tip)
        
        layout.addWidget(action_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.ok_btn = QPushButton("执行批量调整")
        self.ok_btn.setStyleSheet("background-color: #2c5aa0; color: white; font-weight: bold;")
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
    
    def execute_sql(self):
        """执行SQL查询"""
        if not self.api_request:
            return
        
        sql = self.sql_input.toPlainText().strip()
        if not sql:
            self.sql_result_label.setText("请输入SQL")
            return
        
        result, error = self.api_request('POST', '/api/admin/sql', {'sql': sql})
        
        if error:
            self.sql_result_label.setText(f"错误: {error}")
            self.sql_result_label.setStyleSheet("color: #c62828; font-weight: bold;")
            return
        
        if result and result.get('success'):
            count = result.get('count', 0)
            data = result.get('data', [])
            columns = result.get('columns', [])
            self.matched_cards = [row.get('card_key') for row in data if row.get('card_key')]
            self.matched_count = len(self.matched_cards)
            
            self.sql_result_label.setText(f"结果: {count} 条")
            self.sql_result_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
            
            # 用表格展示结果
            self.sql_result_table.clear()
            self.sql_result_table.setRowCount(len(data))
            self.sql_result_table.setColumnCount(len(columns))
            self.sql_result_table.setHorizontalHeaderLabels(get_chinese_columns(columns))
            
            for row_idx, row_data in enumerate(data):
                for col_idx, col_name in enumerate(columns):
                    value = row_data.get(col_name, '')
                    item = QTableWidgetItem(str(value) if value is not None else '')
                    self.sql_result_table.setItem(row_idx, col_idx, item)
            
            self.sql_result_table.resizeColumnsToContents()
        else:
            self.sql_result_label.setText(f"失败: {result.get('message', '未知错误')}")
            self.sql_result_label.setStyleSheet("color: #c62828; font-weight: bold;")
    
    def set_quick_query(self, query_type, days):
        """设置快捷查询"""
        now = datetime.now()
        # 清空所有输入
        self.bind_before_input.setText('')
        self.bind_after_input.setText('')
        self.expire_before_input.setText('')
        
        if query_type == 'bind':
            # 按激活时间查询
            if days == 0:
                # 今天激活
                start = now.replace(hour=0, minute=0, second=0)
                self.bind_after_input.setText(start.strftime('%Y-%m-%d %H:%M'))
            else:
                # N天内激活
                start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
                self.bind_after_input.setText(start.strftime('%Y-%m-%d %H:%M'))
        elif query_type == 'expire':
            # 按到期时间查询
            if days == 0:
                # 今天到期
                end = now.replace(hour=23, minute=59, second=59)
                self.expire_before_input.setText(end.strftime('%Y-%m-%d %H:%M'))
                self.bind_after_input.setText('')  # 清空激活时间条件
            else:
                # N天内到期
                end = (now + timedelta(days=days)).replace(hour=23, minute=59, second=59)
                self.expire_before_input.setText(end.strftime('%Y-%m-%d %H:%M'))
        
        self.preview_query()
    
    def preview_query(self):
        """预览查询结果"""
        if not self.api_request:
            return
        
        # 构建SQL查询
        conditions = []
        bind_before = self.bind_before_input.text().strip()
        bind_after = self.bind_after_input.text().strip()
        expire_before = self.expire_before_input.text().strip()
        
        if bind_before:
            if len(bind_before) == 16:
                bind_before += ':59'
            elif len(bind_before) == 10:
                bind_before += ' 23:59:59'
            conditions.append(f"bind_time <= '{bind_before}'")
        
        if bind_after:
            if len(bind_after) == 16:
                bind_after += ':00'
            elif len(bind_after) == 10:
                bind_after += ' 00:00:00'
            conditions.append(f"bind_time >= '{bind_after}'")
        
        if expire_before:
            if len(expire_before) == 16:
                expire_before += ':59'
            elif len(expire_before) == 10:
                expire_before += ' 23:59:59'
            conditions.append(f"expire_date <= '{expire_before}'")
            conditions.append("expire_date IS NOT NULL")
        
        if not conditions:
            conditions.append("machine_code IS NOT NULL")  # 默认查已绑定的
        
        where_clause = ' AND '.join(conditions)
        sql = f"SELECT * FROM cards WHERE {where_clause}"
        
        result, error = self.api_request('POST', '/api/admin/sql', {'sql': sql})
        
        if result and result.get('success'):
            count = result.get('count', 0)
            data = result.get('data', [])
            columns = result.get('columns', [])
            self.matched_cards = [row.get('card_key') for row in data if row.get('card_key')]
            self.matched_count = count
            
            self.match_label.setText(f"匹配: {count} 张卡密")
            if count > 0:
                self.match_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
            else:
                self.match_label.setStyleSheet("color: #c62828; font-weight: bold;")
            
            # 用表格展示结果
            self.quick_result_table.clear()
            self.quick_result_table.setRowCount(len(data))
            self.quick_result_table.setColumnCount(len(columns))
            self.quick_result_table.setHorizontalHeaderLabels(get_chinese_columns(columns))
            
            for row_idx, row_data in enumerate(data):
                for col_idx, col_name in enumerate(columns):
                    value = row_data.get(col_name, '')
                    item = QTableWidgetItem(str(value) if value is not None else '')
                    self.quick_result_table.setItem(row_idx, col_idx, item)
            
            self.quick_result_table.resizeColumnsToContents()
        else:
            self.match_label.setText(f"查询失败: {result.get('message', '') if result else error}")
            self.match_label.setStyleSheet("color: #c62828; font-weight: bold;")
    
    def get_data(self):
        data = {'hours': self.hours_spin.value()}
        
        bind_before = self.bind_before_input.text().strip()
        if bind_before:
            if len(bind_before) == 16:
                bind_before += ':59'
            data['bind_date_end'] = bind_before
        
        bind_after = self.bind_after_input.text().strip()
        if bind_after:
            if len(bind_after) == 16:
                bind_after += ':00'
            data['bind_date_start'] = bind_after
        
        return data


class CardGeneratorWindow(QMainWindow):
    """卡密生成器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.all_cards = {}
        self.init_ui()
        self.load_cards()
    
    def init_ui(self):
        self.setWindowTitle("卡密生成器 - 网络版")
        self.setMinimumSize(950, 600)
        
        icon_path = os.path.join(PROJECT_ROOT, 'assets', 'img', 'img_gui', 'favicon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 服务器配置区域
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel("服务器:"))
        self.server_label = QLabel(self.config.get('server_url', '未配置'))
        self.server_label.setStyleSheet("color: #2c5aa0;")
        server_layout.addWidget(self.server_label)
        server_layout.addStretch()
        
        config_btn = QPushButton("配置服务器")
        config_btn.clicked.connect(self.show_config_dialog)
        server_layout.addWidget(config_btn)
        layout.addLayout(server_layout)
        
        # 生成区域
        gen_group = QGroupBox("生成卡密")
        gen_layout = QHBoxLayout(gen_group)
        
        gen_layout.addWidget(QLabel("数量:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(1)
        self.count_spin.setFixedWidth(60)
        gen_layout.addWidget(self.count_spin)
        
        gen_layout.addWidget(QLabel("有效期:"))
        self.expire_combo = QComboBox()
        self.expire_combo.addItems(['1天', '7天', '30天', '90天', '180天', '365天', '永久'])
        self.expire_combo.setCurrentIndex(2)  # 默认30天
        self.expire_combo.setFixedWidth(80)
        gen_layout.addWidget(self.expire_combo)
        
        gen_layout.addWidget(QLabel("备注:"))
        self.remark_input = QLineEdit()
        self.remark_input.setPlaceholderText("可选备注...")
        self.remark_input.setFixedWidth(150)
        gen_layout.addWidget(self.remark_input)
        
        gen_btn = QPushButton("生成卡密")
        gen_btn.setStyleSheet("background-color: #2c5aa0; color: white; font-weight: bold;")
        gen_btn.clicked.connect(self.generate_cards)
        gen_layout.addWidget(gen_btn)
        
        gen_layout.addStretch()
        layout.addWidget(gen_group)
        
        # 卡密列表
        list_group = QGroupBox("卡密列表")
        list_layout = QVBoxLayout(list_group)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索卡密/备注/机器码...")
        self.search_input.textChanged.connect(self.filter_cards)
        self.search_input.setFixedWidth(200)
        toolbar.addWidget(self.search_input)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['全部', '未使用', '已绑定', '已过期', '已禁用'])
        self.filter_combo.currentIndexChanged.connect(self.filter_cards)
        toolbar.addWidget(self.filter_combo)
        
        toolbar.addStretch()
        
        batch_time_btn = QPushButton("批量调整时间")
        batch_time_btn.clicked.connect(self.batch_adjust_time)
        toolbar.addWidget(batch_time_btn)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_cards)
        toolbar.addWidget(refresh_btn)
        
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self.export_cards)
        toolbar.addWidget(export_btn)
        
        delete_btn = QPushButton("删除选中")
        delete_btn.setStyleSheet("color: #c62828;")
        delete_btn.clicked.connect(self.delete_selected)
        toolbar.addWidget(delete_btn)
        
        list_layout.addLayout(toolbar)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            '卡密', '状态', '到期时间', '剩余', '机器码', '绑定时间', '解绑次数', '最后使用', '备注', '操作'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 55)
        self.table.setColumnWidth(2, 135)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 135)
        self.table.setColumnWidth(5, 125)
        self.table.setColumnWidth(6, 60)
        self.table.setColumnWidth(7, 125)
        self.table.setColumnWidth(8, 60)
        self.table.setColumnWidth(9, 130)  # 操作列加宽
        list_layout.addWidget(self.table)
        
        layout.addWidget(list_group)
        
        self.statusBar().showMessage("就绪")

    def show_config_dialog(self):
        """显示配置对话框"""
        dialog = ConfigDialog(self, self.config)
        if dialog.exec_() == QDialog.Accepted:
            self.config = dialog.get_config()
            save_config(self.config)
            self.server_label.setText(self.config.get('server_url', '未配置'))
            self.load_cards()
    
    def api_request(self, method, endpoint, data=None):
        """发送API请求"""
        url = f"{self.config.get('server_url', '')}{endpoint}"
        headers = {'X-Admin-Key': self.config.get('api_secret', '')}
        
        try:
            if method == 'GET':
                resp = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                resp = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                resp = requests.delete(url, headers=headers, timeout=10)
            else:
                return None, "不支持的请求方法"
            
            return resp.json(), None
        except requests.exceptions.ConnectionError:
            return None, "无法连接到服务器"
        except requests.exceptions.Timeout:
            return None, "请求超时"
        except Exception as e:
            return None, str(e)
    
    def generate_cards(self):
        """生成卡密"""
        count = self.count_spin.value()
        expire_text = self.expire_combo.currentText()
        remark = self.remark_input.text().strip()
        
        expire_days = {
            '1天': 1, '7天': 7, '30天': 30, '90天': 90,
            '180天': 180, '365天': 365, '永久': None
        }.get(expire_text)
        
        new_keys = []
        failed = 0
        
        for _ in range(count):
            key = generate_card_key(expire_days)  # 传入有效期天数
            result, error = self.api_request('POST', '/api/admin/card', {
                'card_key': key,
                'expire_days': expire_days,  # 传递有效天数，激活时才计算到期时间
                'remark': remark
            })
            
            if error:
                QMessageBox.warning(self, "错误", f"生成失败: {error}")
                return
            
            if result and result.get('success'):
                new_keys.append(key)
            else:
                failed += 1
        
        self.load_cards()
        self.statusBar().showMessage(f"成功生成 {len(new_keys)} 个卡密" + (f"，失败 {failed} 个" if failed else ""))
        
        if new_keys and len(new_keys) <= 10:
            msg = "生成的卡密:\n\n" + "\n".join(new_keys)
            QMessageBox.information(self, "生成成功", msg)
    
    def load_cards(self):
        """加载卡密列表"""
        result, error = self.api_request('GET', '/api/admin/cards')
        
        if error:
            self.statusBar().showMessage(f"加载失败: {error}")
            return
        
        if result and result.get('success'):
            self.all_cards = result.get('data', {})
            self.display_cards(self.all_cards)
        else:
            self.statusBar().showMessage(f"加载失败: {result.get('message', '未知错误')}")
    
    def display_cards(self, cards):
        """显示卡密列表"""
        self.table.setRowCount(0)
        
        for key, info in cards.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 卡密
            self.table.setItem(row, 0, QTableWidgetItem(key))
            
            # 状态
            status = self.get_card_status(info)
            status_item = QTableWidgetItem(status)
            if status == '已过期':
                status_item.setForeground(Qt.red)
            elif status == '已禁用':
                status_item.setForeground(Qt.darkGray)
            elif status == '已绑定':
                status_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 1, status_item)
            
            # 到期时间（未激活显示有效天数，已激活显示到期时间）
            expire_date = info.get('expire_date')
            expire_days = info.get('expire_days')
            if expire_date:
                expire = expire_date
            elif expire_days:
                expire = f"激活后{expire_days}天"
            else:
                expire = "永久"
            self.table.setItem(row, 2, QTableWidgetItem(expire))
            
            # 剩余时间（未激活显示完整有效期）
            remaining = self.calc_remaining_time(info.get('expire_date'), info.get('expire_days'))
            self.table.setItem(row, 3, QTableWidgetItem(remaining))
            
            # 机器码
            machine = info.get('machine_code', '') or ''
            self.table.setItem(row, 4, QTableWidgetItem(machine))
            
            # 绑定时间
            bind_time = info.get('bind_time', '') or ''
            self.table.setItem(row, 5, QTableWidgetItem(bind_time))
            
            # 解绑次数
            unbind_count = info.get('unbind_count', 0) or 0
            max_unbind = info.get('max_unbind_count', 3) if info.get('max_unbind_count') is not None else 3
            self.table.setItem(row, 6, QTableWidgetItem(f"{unbind_count}/{max_unbind}"))
            
            # 最后使用
            last_use = info.get('last_use', '') or ''
            self.table.setItem(row, 7, QTableWidgetItem(last_use))
            
            # 备注
            remark = info.get('remark', '') or ''
            self.table.setItem(row, 8, QTableWidgetItem(remark))
            
            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            
            if info.get('disabled'):
                enable_btn = QPushButton("启用")
                enable_btn.setFixedSize(38, 22)
                enable_btn.clicked.connect(lambda _, k=key: self.toggle_card(k))
                btn_layout.addWidget(enable_btn)
            else:
                disable_btn = QPushButton("禁用")
                disable_btn.setFixedSize(38, 22)
                disable_btn.clicked.connect(lambda _, k=key: self.toggle_card(k))
                btn_layout.addWidget(disable_btn)
            
            if info.get('machine_code'):
                unbind_btn = QPushButton("解绑")
                unbind_btn.setFixedSize(38, 22)
                unbind_btn.clicked.connect(lambda _, k=key: self.unbind_card(k))
                btn_layout.addWidget(unbind_btn)
            
            edit_btn = QPushButton("编辑")
            edit_btn.setFixedSize(38, 22)
            edit_btn.clicked.connect(lambda _, k=key, i=info: self.edit_card(k, i))
            btn_layout.addWidget(edit_btn)
            
            self.table.setCellWidget(row, 9, btn_widget)
        
        self.statusBar().showMessage(f"共 {len(cards)} 个卡密")
    
    def calc_remaining_time(self, expire_date, expire_days=None):
        """计算剩余时间"""
        if not expire_date:
            # 未激活的卡密，显示完整有效期
            if expire_days:
                if expire_days >= 365:
                    return f"{expire_days // 365}年"
                elif expire_days >= 30:
                    return f"{expire_days}天"
                else:
                    return f"{expire_days * 24}小时"
            return "永久"
        try:
            if ' ' in expire_date:
                expire_dt = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
            else:
                expire_dt = datetime.strptime(expire_date, '%Y-%m-%d')
                expire_dt = expire_dt.replace(hour=23, minute=59, second=59)
            
            delta = expire_dt - datetime.now()
            if delta.total_seconds() <= 0:
                return "已过期"
            
            days = delta.days
            hours = delta.seconds // 3600
            if days > 0:
                return f"{days}天{hours}时"
            else:
                return f"{hours}小时"
        except:
            return expire_date

    def get_card_status(self, info):
        """获取卡密状态"""
        if info.get('disabled'):
            return '已禁用'
        
        expire_date = info.get('expire_date')
        if expire_date:
            try:
                if ' ' in expire_date:
                    expire_dt = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
                else:
                    expire_dt = datetime.strptime(expire_date, '%Y-%m-%d')
                if datetime.now() > expire_dt:
                    return '已过期'
            except:
                pass
        
        if info.get('machine_code'):
            return '已绑定'
        
        return '未使用'
    
    def filter_cards(self):
        """筛选卡密"""
        search_text = self.search_input.text().strip().upper()
        filter_type = self.filter_combo.currentText()
        
        filtered = {}
        for key, info in self.all_cards.items():
            if search_text:
                searchable = f"{key} {info.get('remark', '')} {info.get('machine_code', '')}".upper()
                if search_text not in searchable:
                    continue
            
            status = self.get_card_status(info)
            if filter_type == '未使用' and status != '未使用':
                continue
            elif filter_type == '已绑定' and status != '已绑定':
                continue
            elif filter_type == '已过期' and status != '已过期':
                continue
            elif filter_type == '已禁用' and status != '已禁用':
                continue
            
            filtered[key] = info
        
        self.display_cards(filtered)
    
    def toggle_card(self, key):
        """启用/禁用卡密"""
        result, error = self.api_request('POST', f'/api/admin/card/{key}/toggle')
        if error:
            QMessageBox.warning(self, "错误", error)
            return
        if result and result.get('success'):
            self.load_cards()
            self.statusBar().showMessage(result.get('message', '操作成功'))
        else:
            QMessageBox.warning(self, "错误", result.get('message', '操作失败'))
    
    def unbind_card(self, key):
        """解绑卡密"""
        reply = QMessageBox.question(
            self, "确认解绑",
            f"确定要解绑卡密 {key} 吗？\n解绑后可以在其他设备使用。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            result, error = self.api_request('POST', f'/api/admin/card/{key}/unbind')
            if error:
                QMessageBox.warning(self, "错误", error)
                return
            if result and result.get('success'):
                self.load_cards()
                self.statusBar().showMessage("解绑成功")
            else:
                QMessageBox.warning(self, "错误", result.get('message', '解绑失败'))
    
    def edit_card(self, key, info):
        """编辑卡密"""
        dialog = EditCardDialog(self, key, info)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            result, error = self.api_request('POST', f'/api/admin/card/{key}/update', data)
            if error:
                QMessageBox.warning(self, "错误", error)
                return
            if result and result.get('success'):
                self.load_cards()
                self.statusBar().showMessage("更新成功")
            else:
                QMessageBox.warning(self, "错误", result.get('message', '更新失败'))
    
    def batch_adjust_time(self):
        """批量调整时间"""
        dialog = BatchTimeDialog(self, api_request_func=self.api_request)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data.get('hours', 0) == 0:
                QMessageBox.warning(self, "提示", "请输入要调整的小时数")
                return
            
            # 确认操作
            reply = QMessageBox.question(
                self, "确认操作",
                f"确定要对匹配的卡密调整 {data.get('hours')} 小时吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            
            result, error = self.api_request('POST', '/api/admin/cards/batch_time', data)
            if error:
                QMessageBox.warning(self, "错误", error)
                return
            if result and result.get('success'):
                self.load_cards()
                QMessageBox.information(self, "成功", result.get('message', '操作成功'))
            else:
                QMessageBox.warning(self, "错误", result.get('message', '操作失败'))
    
    def delete_selected(self):
        """删除选中的卡密"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的卡密")
            return
        
        keys_to_delete = []
        for row in selected_rows:
            key_item = self.table.item(row, 0)
            if key_item:
                keys_to_delete.append(key_item.text())
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 {len(keys_to_delete)} 个卡密吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            deleted = 0
            for key in keys_to_delete:
                result, error = self.api_request('DELETE', f'/api/admin/card/{key}')
                if result and result.get('success'):
                    deleted += 1
            
            self.load_cards()
            self.statusBar().showMessage(f"已删除 {deleted} 个卡密")
    
    def export_cards(self):
        """导出卡密"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出卡密", "cards_export.txt", "文本文件 (*.txt)"
        )
        
        if file_path:
            lines = [key for key in self.all_cards.keys()]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            self.statusBar().showMessage(f"已导出 {len(lines)} 个卡密到: {file_path}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = CardGeneratorWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
