# Music Tagger (音乐标签工具)

自动化的音乐文件元数据 tagging 工具，支持从 **MusicBrainz** 和 **Apple Music** 获取详细的元数据信息。

## 功能特点

- **MusicBrainz Tagger**: 从 MusicBrainz 数据库获取标准元数据（标题、艺术家、专辑、MBID 等）
- **Apple Music Tagger**: 从 Apple Music (香港区) 抓取元数据，包括幕后制作人员（作曲、作词）
- **批量处理**: 支持对整个文件夹进行批量扫描和智能匹配
- **模块化设计**: 清晰的代码结构，易于扩展和维护

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 使用示例

#### 1. MusicBrainz 单曲标签

```bash
python run_mb.py "path/to/song.mp3"
```

#### 2. Apple Music 单曲标签

```bash
python run_am.py "path/to/song.mp3"
```

#### 3. Apple Music 批量标签

```bash
python run_am_batch.py "path/to/folder"
```

**批量模式工作流程：**
1. 扫描文件夹内所有支持的音频文件 (.mp3, .flac, .m4a, .mp4)
2. 第一个文件：用户选择正确的专辑/歌曲
3. 后续文件：自动匹配同一专辑内的歌曲
   - 唯一匹配：自动处理
   - 多个匹配：提示用户选择
   - 无匹配：回退到全局搜索

## 项目结构

```
tagger/
├── src/
│   ├── __init__.py          # 包初始化，导出配置
│   ├── config.py            # 集中配置管理
│   ├── common/
│   │   ├── __init__.py
│   │   └── audio.py         # 音频文件处理通用接口
│   ├── musicbrainz/
│   │   ├── __init__.py
│   │   ├── client.py        # MusicBrainz API 客户端
│   │   └── cli.py           # MusicBrainz CLI
│   └── applemusic/
│       ├── __init__.py
│       ├── finder.py        # Apple Music 搜索和抓取
│       └── batch.py         # 批量处理逻辑
├── run_mb.py                # MusicBrainz 入口
├── run_am.py                # Apple Music 单曲入口
├── run_am_batch.py          # Apple Music 批量入口
├── requirements.txt         # Python 依赖
└── README.md               # 文档
```

## 重构亮点

### 1. 配置集中化 (`src/config.py`)
- 使用 dataclass 管理所有配置项
- 统一的常量定义（API URL、关键词、文件格式等）
- 易于自定义和扩展

### 2. 类型注解
- 全面的类型提示，提高代码可读性
- 更好的 IDE 支持和错误检测

### 3. 模块化设计
- 清晰的职责分离
- 可复用的工具函数
- 便于单元测试

### 4. 代码质量改进
- 移除魔法字符串
- 统一的错误处理
- 详细的文档字符串

## 环境要求

- Python 3.8+
- Google Chrome 浏览器 (用于 Apple Music 抓取)

## 注意事项

- Apple Music 抓取依赖 Selenium 和 Chrome，首次运行会自动下载 ChromeDriver
- 批量处理时会复用 Selenium 实例以提高效率
- 所有脚本都支持 `--help` 查看使用说明

## License

MIT
