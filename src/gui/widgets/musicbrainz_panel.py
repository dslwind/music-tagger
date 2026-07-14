"""MusicBrainz 搜索面板"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.utils import get_logger, get_config
from src.musicbrainz.client import MusicBrainzClient
from src.common.audio import AudioFileHandler
from src.common import TagWriterFactory

logger = get_logger(__name__)


class MBSearchWorker(QThread):
    """MusicBrainz 搜索工作线程"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, client, title, artist=None, album=None):
        super().__init__()
        self.client = client
        self.title = title
        self.artist = artist
        self.album = album

    def run(self):
        try:
            results = self.client.search_recording(
                self.title,
                artist=self.artist,
                album=self.album,
                limit=10
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class MusicBrainzPanel(QWidget):
    """MusicBrainz 搜索面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_file = ''
        self._search_results = []
        self._selected_result = None
        self._mb_client = MusicBrainzClient()
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
        self.search_edit.setPlaceholderText("输入歌曲名称...")
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

        # 元数据显示
        self._setup_metadata_display(layout)

        # 应用按钮
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("应用标签")
        self.apply_btn.clicked.connect(self._on_apply)
        self.apply_btn.setEnabled(False)
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_btn)
        layout.addLayout(btn_layout)

        self._set_ui_enabled(False)

    def _setup_metadata_display(self, parent_layout):
        """设置元数据显示区域"""
        meta_group = QGroupBox("元数据预览")
        meta_layout = QVBoxLayout(meta_group)

        self.meta_labels = {}
        fields = [('title', '标题'), ('artist', '艺术家'), ('album', '专辑'),
                  ('date', '日期'), ('tracknumber', '曲目号'), ('genre', '流派')]

        for key, label in fields:
            row_layout = QHBoxLayout()
            row_layout.addWidget(QLabel(f"{label}:"))
            value_label = QLabel("-")
            value_label.setWordWrap(True)
            self.meta_labels[key] = value_label
            row_layout.addWidget(value_label)
            row_layout.addStretch()
            meta_layout.addLayout(row_layout)

        parent_layout.addWidget(meta_group)

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

        try:
            handler = AudioFileHandler(self._current_file)
            tags = handler.get_tags()
            self.search_edit.setText(tags.get('title', os.path.splitext(os.path.basename(self._current_file))[0]))
            self.search_edit.selectAll()
        except Exception as e:
            logger.error(f"加载文件失败: {e}")
            self.search_edit.setText(os.path.splitext(os.path.basename(self._current_file))[0])

    def _on_search(self):
        """执行搜索"""
        if not self._current_file:
            QMessageBox.warning(self, "警告", "请先选择音频文件")
            return

        self.search_btn.setEnabled(False)
        self.search_btn.setText("搜索中...")
        self.result_list.clear()

        # 获取本地元数据
        try:
            handler = AudioFileHandler(self._current_file)
            tags = handler.get_tags()
            artist = tags.get('artist', '')
        except:
            artist = ''

        # 启动搜索线程
        self.search_worker = MBSearchWorker(
            self._mb_client,
            self.search_edit.text().strip(),
            artist=artist
        )
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

        for recording in results:
            track_title = recording.get('title', 'Unknown')
            artist_credit = recording.get('artist-credit', [])
            artist_name = artist_credit[0]['artist']['name'] if artist_credit else "Unknown"
            releases = recording.get('release-list', [])
            album_name = releases[0]['title'] if releases else "Unknown"

            list_item = QListWidgetItem(f"{track_title} - {artist_name} ({album_name})")
            list_item.setData(Qt.ItemDataRole.UserRole, recording)
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
        self._display_metadata()

    def _on_result_double_clicked(self, item):
        """双击搜索结果"""
        self._on_result_selected(self.result_list.row(item))
        self._on_apply()

    def _display_metadata(self):
        """显示选中结果的元数据"""
        if not self._selected_result:
            return

        recording = self._selected_result

        # 基本信息
        self.meta_labels['title'].setText(recording.get('title', '-'))

        artist_credit = recording.get('artist-credit', [])
        artist_name = artist_credit[0]['artist']['name'] if artist_credit else "-"
        self.meta_labels['artist'].setText(artist_name)

        releases = recording.get('release-list', [])
        if releases:
            release = releases[0]
            self.meta_labels['album'].setText(release.get('title', '-'))
            self.meta_labels['date'].setText(release.get('date', '-'))
        else:
            self.meta_labels['album'].setText("-")
            self.meta_labels['date'].setText("-")

        # 流派
        tags_list = recording.get('tag-list', [])
        if tags_list:
            genres = ', '.join([t['name'] for t in tags_list[:3]])
            self.meta_labels['genre'].setText(genres)
        else:
            self.meta_labels['genre'].setText("-")

        self.meta_labels['tracknumber'].setText("-")

        self.apply_btn.setEnabled(True)

    def _on_apply(self):
        """应用标签"""
        if not self._current_file or not self._selected_result:
            return

        recording = self._selected_result

        reply = QMessageBox.question(
            self, "确认",
            f"确定要写入标签到文件吗？\n{os.path.basename(self._current_file)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 构建新标签
            new_tags = {
                'title': recording.get('title', ''),
                'musicbrainz_trackid': recording.get('id', ''),
            }

            artist_credit = recording.get('artist-credit', [])
            if artist_credit:
                new_tags['artist'] = artist_credit[0]['artist']['name']
                new_tags['musicbrainz_artistid'] = artist_credit[0]['artist'].get('id', '')

            releases = recording.get('release-list', [])
            if releases:
                release = releases[0]
                new_tags['album'] = release.get('title', '')
                new_tags['date'] = release.get('date', '')
                new_tags['musicbrainz_albumid'] = release.get('id', '')

            tags_list = recording.get('tag-list', [])
            if tags_list:
                new_tags['genre'] = ', '.join([t['name'] for t in tags_list[:3]])

            # 使用 AudioFileHandler 更新
            try:
                handler = AudioFileHandler(self._current_file)
                handler.update_tags(new_tags)
                QMessageBox.information(self, "成功", "标签写入成功")
            except Exception as e:
                logger.error(f"写入失败: {e}")
                QMessageBox.critical(self, "失败", f"标签写入失败: {e}")