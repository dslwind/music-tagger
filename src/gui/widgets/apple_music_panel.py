"""Apple Music 搜索面板"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.utils import get_logger, get_config
from src.applemusic.finder import (
    get_audio_metadata_full,
    search_apple_music,
    scrape_web_details_selenium,
    merge_metadata,
)
from src.common import TagWriterFactory
from .metadata_editor import MetadataEditor

logger = get_logger(__name__)


class SearchWorker(QThread):
    """搜索工作线程"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query_meta):
        super().__init__()
        self.query_meta = query_meta

    def run(self):
        try:
            results = search_apple_music(self.query_meta)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class ScrapeWorker(QThread):
    """抓取工作线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, track_url):
        super().__init__()
        self.track_url = track_url

    def run(self):
        try:
            details = scrape_web_details_selenium(self.track_url)
            self.finished.emit(details)
        except Exception as e:
            self.error.emit(str(e))


class AppleMusicPanel(QWidget):
    """Apple Music 搜索面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_file = ''
        self._search_results = []
        self._selected_result = None
        self._driver = None
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 文件选择
        file_group = QGroupBox("文件选择")
        file_layout = QHBoxLayout(file_group)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择音频文件...")
        self.file_path_edit.setReadOnly(True)
        file_layout.addWidget(self.file_path_edit)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(self.browse_btn)

        layout.addWidget(file_group)

        # 搜索区域
        search_group = QGroupBox("搜索")
        search_layout = QHBoxLayout(search_group)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入歌曲名称或艺术家...")
        self.search_edit.returnPressed.connect(self._on_search)
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_edit)

        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self._on_search)
        self.search_btn.setEnabled(False)
        search_layout.addWidget(self.search_btn)

        layout.addWidget(search_group)

        # 搜索结果列表
        result_group = QGroupBox("搜索结果")
        result_layout = QVBoxLayout(result_group)

        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self._on_result_double_clicked)
        self.result_list.currentRowChanged.connect(self._on_result_selected)
        result_layout.addWidget(self.result_list)

        layout.addWidget(result_group)

        # 元数据编辑器
        self.metadata_editor = MetadataEditor()
        self.metadata_editor.apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(self.metadata_editor)

        # 初始状态
        self._set_ui_enabled(False)

    def _set_ui_enabled(self, enabled: bool):
        """设置 UI 可用状态"""
        self.search_btn.setEnabled(enabled)
        self.search_edit.setEnabled(enabled)

    def _on_browse(self):
        """浏览文件"""
        config = get_config()
        supported = ' '.join(f'*{ext}' for ext in config.get('supported_formats', default=['.mp3', '.flac', '.m4a', '.mp4']))
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "",
            f"音频文件 ({supported});;所有文件 (*.*)"
        )

        if file_path:
            self._current_file = file_path
            self.file_path_edit.setText(file_path)
            self._load_local_metadata()
            self._set_ui_enabled(True)

    def _load_local_metadata(self):
        """加载本地文件元数据"""
        if not self._current_file:
            return

        local_meta = get_audio_metadata_full(self._current_file)
        if local_meta:
            self.metadata_editor.set_local_metadata(local_meta)
            self.search_edit.setText(f"{local_meta.get('title', '')} {local_meta.get('artist', '')}")
            self.search_edit.selectAll()
        else:
            self.metadata_editor.set_local_metadata({})
            filename = os.path.splitext(os.path.basename(self._current_file))[0]
            self.search_edit.setText(filename)

    def _on_search(self):
        """执行搜索"""
        if not self._current_file:
            QMessageBox.warning(self, "警告", "请先选择音频文件")
            return

        self.search_btn.setEnabled(False)
        self.search_btn.setText("搜索中...")
        self.result_list.clear()

        # 获取本地元数据用于搜索
        local_meta = get_audio_metadata_full(self._current_file) or {}
        query_meta = {
            'title': self.search_edit.text().strip(),
            'artist': local_meta.get('artist', '')
        }

        # 启动搜索线程
        self.search_worker = SearchWorker(query_meta)
        self.search_worker.finished.connect(self._on_search_finished)
        self.search_worker.error.connect(self._on_search_error)
        self.search_worker.start()

    def _on_search_finished(self, results):
        """搜索完成"""
        self._search_results = results
        self.search_btn.setEnabled(True)
        self.search_btn.setText("搜索")

        if not results:
            QMessageBox.information(self, "提示", "未找到相关结果")
            return

        for item in results:
            track_name = item.get('trackName', 'Unknown')
            artist_name = item.get('artistName', 'Unknown')
            album_name = item.get('collectionName', 'Unknown')
            list_item = QListWidgetItem(f"{track_name} - {artist_name} ({album_name})")
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.result_list.addItem(list_item)

    def _on_search_error(self, error_msg):
        """搜索出错"""
        self.search_btn.setEnabled(True)
        self.search_btn.setText("搜索")
        QMessageBox.critical(self, "错误", f"搜索失败: {error_msg}")

    def _on_result_selected(self, row):
        """选中搜索结果"""
        if row < 0 or row >= len(self._search_results):
            return

        self._selected_result = self._search_results[row]
        self._load_remote_metadata()

    def _on_result_double_clicked(self, item):
        """双击搜索结果"""
        self._on_result_selected(self.result_list.row(item))
        self._on_apply()

    def _load_remote_metadata(self):
        """加载远程元数据"""
        if not self._selected_result:
            return

        track_url = self._selected_result.get('trackViewUrl')
        if not track_url:
            return

        # 显示提示
        self.metadata_editor.setEnabled(False)
        self._update_status("正在获取详细信息...")

        # 启动抓取线程
        self.scrape_worker = ScrapeWorker(track_url)
        self.scrape_worker.finished.connect(self._on_scrape_finished)
        self.scrape_worker.error.connect(self._on_scrape_error)
        self.scrape_worker.start()

    def _on_scrape_finished(self, details):
        """抓取完成"""
        self._update_status("就绪")
        self.metadata_editor.setEnabled(True)

        if not self._selected_result:
            return

        # 构建远程元数据
        composer_str = "/".join(details.get('composers', []))
        lyricist_str = "/".join(details.get('lyricists', []))

        remote_meta = {
            'title': self._selected_result.get('trackName', ''),
            'artist': self._selected_result.get('artistName', ''),
            'album': self._selected_result.get('collectionName', ''),
            'composer': composer_str,
            'lyricist': lyricist_str,
            'copyright': details.get('copyright', ''),
        }

        self.metadata_editor.set_remote_metadata(remote_meta)

    def _on_scrape_error(self, error_msg):
        """抓取出错"""
        self._update_status(f"获取详情失败: {error_msg}")
        self.metadata_editor.setEnabled(True)
        logger.warning(f"抓取详情失败: {error_msg}")

        # 仍然使用基本数据
        remote_meta = {
            'title': self._selected_result.get('trackName', ''),
            'artist': self._selected_result.get('artistName', ''),
            'album': self._selected_result.get('collectionName', ''),
            'composer': '',
            'lyricist': '',
            'copyright': '',
        }
        self.metadata_editor.set_remote_metadata(remote_meta)

    def _on_apply(self):
        """应用标签"""
        if not self._current_file:
            return

        final_meta = self.metadata_editor.get_final_metadata()
        if not final_meta.get('title'):
            QMessageBox.warning(self, "警告", "没有有效的元数据可写入")
            return

        reply = QMessageBox.question(
            self, "确认",
            f"确定要写入标签到文件吗？\n{os.path.basename(self._current_file)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if TagWriterFactory.write_tags(self._current_file, final_meta):
                QMessageBox.information(self, "成功", "标签写入成功")
            else:
                QMessageBox.critical(self, "失败", "标签写入失败")

    def _update_status(self, message: str):
        """更新状态（通过主窗口）"""
        main_window = self.window()
        if hasattr(main_window, 'update_status'):
            main_window.update_status(message)