"""配置加载模块"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from src.utils import get_logger

logger = get_logger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    'apple_music': {
        'country': 'HK',
        'search_limit': 5,
        'api_url': 'https://itunes.apple.com/search',
    },
    'musicbrainz': {
        'app_name': 'MusicTagger',
        'version': '0.1',
        'contact': 'user@example.com',
    },
    'selenium': {
        'headless': True,
        'disable_gpu': True,
        'mute_audio': True,
        'disable_images': True,
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'page_timeout': 10,
    },
    'logging': {
        'level': 'INFO',
        'file_enabled': False,
        'file_path': 'logs/music_tagger.log',
    },
    'supported_formats': ['.mp3', '.flac', '.m4a', '.mp4'],
}

# 全局配置实例
_config: Optional['Config'] = None


class Config:
    """配置管理类"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置。

        Args:
            config_path: 配置文件路径，如果为 None 则使用默认配置
        """
        self._data = DEFAULT_CONFIG.copy()

        if config_path:
            self._load_from_file(config_path)

    def _load_from_file(self, config_path: str) -> bool:
        """
        从 YAML 文件加载配置。

        Args:
            config_path: 配置文件路径

        Returns:
            是否加载成功
        """
        if not HAS_YAML:
            logger.warning("PyYAML 未安装，无法加载配置文件")
            return False

        path = Path(config_path)
        if not path.exists():
            logger.warning(f"配置文件不存在: {config_path}")
            return False

        try:
            with open(path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    self._merge_config(self._data, user_config)
                    logger.info(f"已加载配置文件: {config_path}")
                    return True
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")

        return False

    def _merge_config(self, base: Dict, override: Dict):
        """递归合并配置"""
        for key, value in override.items():
            if key in base and isinstance(base[key], Dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get(self, *keys, default: Any = None) -> Any:
        """
        获取配置值。

        Args:
            *keys: 配置键路径，如 get('apple_music', 'country')
            default: 默认值

        Returns:
            配置值
        """
        value = self._data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default

            if value is None:
                return default

        return value

    @property
    def apple_music(self) -> Dict:
        """Apple Music 配置"""
        return self._data.get('apple_music', {})

    @property
    def musicbrainz(self) -> Dict:
        """MusicBrainz 配置"""
        return self._data.get('musicbrainz', {})

    @property
    def selenium(self) -> Dict:
        """Selenium 配置"""
        return self._data.get('selenium', {})

    @property
    def logging(self) -> Dict:
        """日志配置"""
        return self._data.get('logging', {})

    @property
    def supported_formats(self) -> list:
        """支持的音频格式"""
        return self._data.get('supported_formats', [])


def get_config(config_path: Optional[str] = None) -> Config:
    """
    获取配置实例 (单例模式)。

    Args:
        config_path: 配置文件路径

    Returns:
        Config 实例
    """
    global _config

    if _config is None:
        # 如果未指定路径，尝试查找默认配置文件
        if config_path is None:
            # 查找项目根目录的 config.yaml
            project_root = Path(__file__).parent.parent.parent
            default_path = project_root / 'config.yaml'
            if default_path.exists():
                config_path = str(default_path)

        _config = Config(config_path)

    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """
    重新加载配置。

    Args:
        config_path: 配置文件路径

    Returns:
        新的 Config 实例
    """
    global _config
    _config = Config(config_path)
    return _config