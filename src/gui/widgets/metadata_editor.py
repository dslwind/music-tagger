"""元数据编辑器组件"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
    QGroupBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class MetadataEditor(QWidget):
    """元数据编辑器：显示和编辑音频标签"""

    tags_changed = pyqtSignal(dict)

    # 标签字段定义
    FIELDS = [
        ('title', '标题'),
        ('artist', '艺术家'),
        ('album', '专辑'),
        ('composer', '作曲'),
        ('lyricist', '作词'),
        ('copyright', '版权'),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._local_meta = {}
        self._remote_meta = {}
        self._final_meta = {}
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标签对比表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['字段', '原值', '新值', '最终值'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 80)
        self.table.setRowCount(len(self.FIELDS))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        # 填充表格
        for row, (key, label) in enumerate(self.FIELDS):
            item_field = QTableWidgetItem(label)
            item_field.setFlags(item_field.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, item_field)

            for col in range(1, 4):
                item = QTableWidgetItem('')
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

        layout.addWidget(self.table)

        # 操作按钮
        btn_layout = QHBoxLayout()

        self.preview_btn = QPushButton("预览更改")
        self.preview_btn.clicked.connect(self._on_preview)
        btn_layout.addWidget(self.preview_btn)

        self.apply_btn = QPushButton("应用标签")
        self.apply_btn.setEnabled(False)
        btn_layout.addWidget(self.apply_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def set_local_metadata(self, metadata: dict):
        """设置本地元数据"""
        self._local_meta = metadata or {}
        self._update_table()

    def set_remote_metadata(self, metadata: dict):
        """设置远程元数据"""
        self._remote_meta = metadata or {}
        self._update_table()

    def get_final_metadata(self) -> dict:
        """获取最终元数据（合并后）"""
        return self._final_meta

    def _update_table(self):
        """更新表格显示"""
        for row, (key, label) in enumerate(self.FIELDS):
            local_val = self._local_meta.get(key, '')
            remote_val = self._remote_meta.get(key, '')

            # 最终值：远程优先，本地兜底
            final_val = remote_val.strip() if remote_val.strip() else local_val.strip()

            self.table.item(row, 1).setText(str(local_val)[:50])
            self.table.item(row, 2).setText(str(remote_val)[:50])
            self.table.item(row, 3).setText(str(final_val)[:50])

            # 高亮变化的字段
            if remote_val.strip() and remote_val.strip() != local_val.strip():
                self.table.item(row, 2).setBackground(QColor(200, 255, 200))
                self.table.item(row, 3).setBackground(QColor(200, 255, 200))
            elif remote_val.strip() == '' and local_val.strip():
                # 保持原值
                self.table.item(row, 3).setBackground(QColor(255, 255, 200))

        # 生成最终元数据
        self._final_meta = {}
        for key, _ in self.FIELDS:
            local_val = self._local_meta.get(key, '').strip()
            remote_val = self._remote_meta.get(key, '').strip()
            self._final_meta[key] = remote_val if remote_val else local_val

        self.apply_btn.setEnabled(bool(self._final_meta.get('title')))

    def _on_preview(self):
        """预览更改"""
        # 显示差异对话框
        self.apply_btn.setEnabled(True)

    def clear(self):
        """清空编辑器"""
        self._local_meta = {}
        self._remote_meta = {}
        self._final_meta = {}
        for row in range(len(self.FIELDS)):
           for col in range(1, 4):
                self.table.item(row, col).setText('')
                self.table.item(row, col).setBackground(QColor(255, 255, 255))
        self.apply_btn.setEnabled(False)