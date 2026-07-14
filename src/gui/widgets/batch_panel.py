"""批量处理面板"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QGroupBox, QProgressBar,
    QCheckBox, QComboBox
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

logger = get_logger(__name__)


class BatchWorker(QThread):
    """批量处理工作线程"""
    progress = pyqtSignal(int, int, str)
    file_done = pyqtSignal(str, bool, str)
    need_selection = pyqtSignal(list)  # 需要用户选择
    selection_made = pyqtSignal(object)  # 用户已选择
    finished = pyqtSignal(int, int)

    def __init__(self, folder_path, supported_formats):
        super().__init__()
        self.folder_path = folder_path
        self.supported_formats = supported_formats
        self._is_running = True
        self._current_collection_id = None
        self._pending_selection = None
        self._driver = None

    def stop(self):
        self._is_running = False

    def set_selection(self, selected):
        """设置用户选择"""
        self._pending_selection = selected

    def run(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        config = get_config()

        # 获取文件列表
        files = [f for f in os.listdir(self.folder_path)
                 if f.lower().endswith(tuple(self.supported_formats))]
        files.sort()

        total = len(files)
        done = 0
        success = 0

        if not files:
            self.emit_finished(0, 0)
            return

        # 初始化 Selenium
        chrome_options = Options()
        if config.get('selenium', 'headless', default=True):
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        try:
            self._driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
        except Exception as e:
            logger.error(f"Selenium 初始化失败: {e}")
            self.progress.emit(0, total, "初始化失败")
            self.finished.emit(0, total)
            return

        try:
            for i, filename in enumerate(files):
                if not self._is_running:
                    break

                file_path = os.path.join(self.folder_path, filename)
                self.progress.emit(i, total, f"处理: {filename}")

                try:
                    result = self._process_file(file_path)
                    if result:
                        success += 1
                        self.file_done.emit(filename, True, "")
                    else:
                        self.file_done.emit(filename, False, "未匹配")
                except Exception as e:
                    logger.warning(f"处理失败 {filename}: {e}")
                    self.file_done.emit(filename, False, str(e))

                done = i + 1

        finally:
            if self._driver:
                self._driver.quit()

        self.finished.emit(success, total)

    def _process_file(self, file_path):
        """处理单个文件"""
        filename = os.path.basename(file_path)
        local_meta = get_audio_metadata_full(file_path)

        if not local_meta:
            return False

        results = search_apple_music(local_meta)

        if not results:
            return False

        selected = None

        # 如果已有专辑ID，优先匹配
        if self._current_collection_id:
            matches = [r for r in results if r.get('collectionId') == self._current_collection_id]
            if len(matches) == 1:
                selected = matches[0]
            elif len(matches) > 1:
                # 多个匹配，使用第一个
                selected = matches[0]

        # 如果没有匹配，使用第一个结果
        if not selected:
            selected = results[0]

        # 抓取详情
        track_url = selected.get('trackViewUrl')
        if track_url:
            try:
                details = scrape_web_details_selenium(track_url, driver=self._driver)
                composer_str = "/".join(details.get('composers', []))
                lyricist_str = "/".join(details.get('lyricists', []))
            except:
                composer_str = ""
                lyricist_str = ""
        else:
            composer_str = ""
            lyricist_str = ""

        # 构建远程元数据
        remote_meta = {
            'title': selected.get('trackName', ''),
            'artist': selected.get('artistName', ''),
            'album': selected.get('collectionName', ''),
            'composer': composer_str,
            'lyricist': lyricist_str,
            'copyright': details.get('copyright', '') if track_url else '',
        }

        # 合并并写入
        final_meta = merge_metadata(local_meta, remote_meta)
        result = TagWriterFactory.write_tags(file_path, final_meta)

        # 记录专辑ID
        if result and self._current_collection_id is None:
            self._current_collection_id = selected.get('collectionId')

        return result


class BatchPanel(QWidget):
    """批量处理面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._folder_path = ''
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        #文件夹选择
        folder_group = QGroupBox("文件夹选择")
        folder_layout = QHBoxLayout(folder_group)

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("选择包含音频文件的文件夹...")
        self.folder_edit.setReadOnly(True)
        folder_layout.addWidget(self.folder_edit)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._on_browse)
        folder_layout.addWidget(self.browse_btn)

        layout.addWidget(folder_group)

        # 文件列表
        files_group = QGroupBox("文件列表")
        files_layout = QVBoxLayout(files_group)

        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        files_layout.addWidget(self.file_list)

        layout.addWidget(files_group)

        # 进度条
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("就绪")
        progress_layout.addWidget(self.progress_label)

        layout.addLayout(progress_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("开始批量处理")
        self.start_btn.clicked.connect(self._on_start)
        self.start_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_browse(self):
        """浏览文件夹"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "选择文件夹", "",
            QFileDialog.Option.ShowDirsOnly
        )

        if folder_path:
            self._folder_path = folder_path
            self.folder_edit.setText(folder_path)
            self._scan_folder()

    def _scan_folder(self):
        """扫描文件夹"""
        if not self._folder_path:
            return

        config = get_config()
        supported_formats = config.get('supported_formats', default=['.mp3', '.flac', '.m4a', '.mp4'])

        self.file_list.clear()
        files = [f for f in os.listdir(self._folder_path)
                 if f.lower().endswith(tuple(supported_formats))]
        files.sort()

        for filename in files:
            item = QListWidgetItem(f"⏳ {filename}")
            self.file_list.addItem(item)

        self.progress_bar.setMaximum(len(files))
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"共 {len(files)} 个文件")

        if files:
            self.start_btn.setEnabled(True)

    def _on_start(self):
        """开始批量处理"""
        if not self._folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹")
            return

        config = get_config()
        supported_formats = config.get('supported_formats', default=['.mp3', '.flac', '.m4a', '.mp4'])

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)

        # 启动工作线程
        self._worker = BatchWorker(self._folder_path, supported_formats)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_stop(self):
        """停止处理"""
        if self._worker:
            self._worker.stop()
            self.stop_btn.setEnabled(False)

    def _on_progress(self, current, total, message):
        """更新进度"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(message)
        self._update_status(message)

    def _on_file_done(self, filename, success, error_msg):
        """单个文件处理完成"""
        # 更新列表项状态
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if filename in item.text():
                if success:
                    item.setText(f"✓ {filename}")
                    item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    item.setText(f"✗ {filename} ({error_msg})")
                    item.setForeground(Qt.GlobalColor.red)
                break

    def _on_finished(self, success, total):
        """批量处理完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)

        self.progress_label.setText(f"完成: {success}/{total} 个文件成功")

        QMessageBox.information(
            self, "完成",
            f"批量处理完成\n成功: {success}/{total} 个文件"
        )

    def _update_status(self, message: str):
        """更新状态"""
        main_window = self.window()
        if hasattr(main_window, 'update_status'):
            main_window.update_status(message)