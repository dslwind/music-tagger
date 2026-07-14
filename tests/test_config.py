"""测试配置模块"""
import pytest
from src.utils.config import Config, get_config, DEFAULT_CONFIG


class TestConfig:
    """测试配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        assert config.get('apple_music', 'country') == 'HK'
        assert config.get('apple_music', 'search_limit') == 5
        assert config.get('musicbrainz', 'app_name') == 'MusicTagger'

    def test_get_nested_value(self):
        """测试获取嵌套值"""
        config = Config()
        assert config.get('selenium', 'headless') == True
        assert config.get('selenium', 'page_timeout') == 10

    def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        config = Config()
        assert config.get('nonexistent') is None
        assert config.get('nonexistent', default='default') == 'default'

    def test_property_accessors(self):
        """测试属性访问器"""
        config = Config()
        assert isinstance(config.apple_music, dict)
        assert isinstance(config.musicbrainz, dict)
        assert isinstance(config.selenium, dict)
        assert isinstance(config.logging, dict)
        assert isinstance(config.supported_formats, list)

    def test_supported_formats(self):
        """测试支持的格式列表"""
        config = Config()
        formats = config.supported_formats
        assert '.mp3' in formats
        assert '.flac' in formats
        assert '.m4a' in formats
        assert '.mp4' in formats


class TestGetConfig:
    """测试获取配置实例"""

    def test_get_config_returns_config(self):
        """测试返回 Config 实例"""
        config = get_config()
        assert isinstance(config, Config)

    def test_get_config_singleton(self):
        """测试单例模式"""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2