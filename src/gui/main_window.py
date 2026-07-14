"""主窗口模块"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QStatusBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from src.gui.widgets.apple_music_panel import AppleMusicPanel
from src.gui.widgets.musicbrainz_panel import MusicBrainzPanel
from src.gui.widgets.batch_panel import BatchPanel


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Tagger - 音乐标签工具")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        self._setup_ui()
        self._setup_status_bar()

    def _setup_ui(self):
        """设置界面布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        # Apple Music 单曲
        self.apple_music_panel = AppleMusicPanel()
        self.tab_widget.addTab(self.apple_music_panel, "Apple Music")

        # MusicBrainz
        self.musicbrainz_panel = MusicBrainzPanel()
        self.tab_widget.addTab(self.musicbrainz_panel, "MusicBrainz")

        # 批量处理
        self.batch_panel = BatchPanel()
        self.tab_widget.addTab(self.batch_panel, "批量处理")

        layout.addWidget(self.tab_widget)

    def _setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def update_status(self, message: str):
        """更新状态栏"""
        self.status_bar.showMessage(message)