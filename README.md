# Music Tagger (音乐标签工具)

这是一个用于自动抓取和写入音乐文件元数据的工具。支持从 **MusicBrainz** 和 **Apple Music** 获取数据。

## 功能特点

- **MusicBrainz Tagger**: 从 MusicBrainz 数据库搜索并获取详细的元数据（标题、艺术家、专辑、Track ID 等）。
- **Apple Music Tagger**: 从 Apple Music (香港区) 抓取元数据，支持获取详细的幕后制作人员信息（作曲、作词）。
- **批量处理**: 支持对整个文件夹进行批量扫描和自动匹配（基于 Apple Music）。
- **智能匹配**: 批量模式下，首个文件确认专辑后，后续文件会自动尝试匹配同一专辑内的歌曲。

## 环境要求

- Python 3.8+
- Google Chrome 浏览器 (用于 Apple Music 抓取)

### 安装依赖

请确保安装了以下 Python 库：

```bash
pip install mutagen musicbrainzngs requests beautifulsoup4 selenium webdriver-manager
```

## 使用说明

### GUI 图形界面（推荐）

启动图形界面：

```bash
pip install PyQt6
python run_gui.py
```

GUI 功能：
- **Apple Music 标签页**: 单曲搜索和标签写入
- **MusicBrainz 标签页**: MusicBrainz 数据库搜索
- **批量处理标签页**: 文件夹批量处理

### 命令行界面

本项目包含三个主要的命令行入口脚本：

### 1. MusicBrainz 单曲标签

使用 MusicBrainz 数据库搜索并标记单个文件。

```bash
python run_mb.py "文件路径"
```

### 2. Apple Music 单曲标签

使用 Apple Music 搜索并标记单个文件。

```bash
python run_am.py "文件路径"
```

### 3. Apple Music 批量标签

批量处理一个文件夹内的所有音频文件。

```bash
python run_am_batch.py "文件夹路径"
```

**批量模式逻辑：**
1.  程序会扫描文件夹内的所有支持文件 (.mp3, .flac, .m4a, .mp4)。
2.  **第一个文件**：程序会进行搜索，并要求用户从结果中选择正确的专辑/歌曲。
3.  **后续文件**：程序会自动在已确认的专辑中查找匹配的歌曲。
    -   如果找到唯一匹配，自动处理。
    -   如果找到多个匹配（例如同名歌曲），会提示用户选择。
    -   如果未找到匹配，会回退到全局搜索并提示用户。
4.  **默认选择**：在选择列表时，直接按回车键默认选择第 1 项。

## 项目结构

```
tagger/
├── src/
│   ├── common/          # 通用模块 (音频文件处理)
│   ├── musicbrainz/     # MusicBrainz 相关逻辑
│   └── applemusic/      # Apple Music 相关逻辑 (含 Selenium 爬虫)
├── run_mb.py            # MusicBrainz 入口
├── run_am.py            # Apple Music 单曲入口
├── run_am_batch.py      # Apple Music 批量入口
└── README.md            # 说明文档
```

## 注意事项

- Apple Music 抓取依赖于 Selenium 和 Chrome 浏览器，运行时会启动一个无头 (Headless) Chrome 实例。
- 首次运行可能需要下载 ChromeDriver，请保持网络连接。
- 批量处理时，Selenium 实例会被复用以提高速度。

## 配置

项目支持通过 `config.yaml` 进行配置。主要配置项：

- `apple_music.country`: 搜索区域（默认 HK）
- `apple_music.search_limit`: 搜索结果数量（默认 5）
- `selenium.headless`: 是否无头模式（默认 true）
- `logging.level`: 日志级别（默认 INFO）

## 开发

### 运行测试

```bash
pytest
```

### 项目结构

```
src/
├── common/
│   ├── audio.py        # 音频文件处理器
│   └── writer.py       # 统一标签写入器
├── musicbrainz/
│   ├── client.py       # MusicBrainz API 客户端
│   └── cli.py          # 命令行交互
├── applemusic/
│   ├── finder.py       # Apple Music 搜索与抓取
│   └── batch.py        # 批量处理
├── gui/
│   ├── main_window.py  # 主窗口
│   └── widgets/        # GUI 组件
│       ├── apple_music_panel.py
│       ├── musicbrainz_panel.py
│       ├── batch_panel.py
│       └── metadata_editor.py
└── utils/
    ├── logger.py       # 日志模块
    └── config.py       # 配置模块
tests/                   # 单元测试
run_gui.py              # GUI 入口
run_mb.py               # MusicBrainz 命令行入口
run_am.py               # Apple Music 命令行入口
run_am_batch.py         # 批量处理命令行入口
```
