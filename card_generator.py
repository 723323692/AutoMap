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
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 140)
        self.table.setColumnWidth(5, 130)
        self.table.setColumnWidth(6, 70)
        self.table.setColumnWidth(7, 130)
        self.table.setColumnWidth(8, 80)
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
            self.table.setItem(row, 6, QTableWidgetItem(f"{unbind_count}/3"))
            
            # 最后使用
            last_use = info.get('last_use', '') or ''
            self.table.setItem(row, 7, QTableWidgetItem(last_use))
            
            # 备注
            remark = info.get('remark', '') or ''
            self.table.setItem(row, 8, QTableWidgetItem(remark))
            
            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(2)
            
            if info.get('disabled'):
                enable_btn = QPushButton("启用")
                enable_btn.setFixedSize(45, 24)
                enable_btn.clicked.connect(lambda _, k=key: self.toggle_card(k))
                btn_layout.addWidget(enable_btn)
            else:
                disable_btn = QPushButton("禁用")
                disable_btn.setFixedSize(45, 24)
                disable_btn.clicked.connect(lambda _, k=key: self.toggle_card(k))
                btn_layout.addWidget(disable_btn)
            
            if info.get('machine_code'):
                unbind_btn = QPushButton("解绑")
                unbind_btn.setFixedSize(45, 24)
                unbind_btn.clicked.connect(lambda _, k=key: self.unbind_card(k))
                btn_layout.addWidget(unbind_btn)
            
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
