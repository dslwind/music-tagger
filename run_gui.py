"""Music Tagger GUI 入口"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.gui.main_window import MainWindow


def main():
    """启动 GUI 应用"""
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置应用信息
    app.setApplicationName("Music Tagger")
    app.setApplicationDisplayName("Music Tagger - 音乐标签工具")
    app.setOrganizationName("Music Tagger")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()