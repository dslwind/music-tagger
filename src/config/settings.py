"""应用配置设置"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Settings:
    """应用配置类"""
    
    # Apple Music 配置
    apple_music_country: str = "HK"  # 默认使用香港区
    apple_music_search_limit: int = 5
    
    # Selenium/浏览器配置
    browser_headless: bool = True
    browser_disable_gpu: bool = True
    browser_mute_audio: bool = True
    browser_disable_images: bool = True  # 禁用图片加载以加快速度
    browser_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    )
    
    # 支持的音频格式
    supported_formats: List[str] = field(default_factory=lambda: ['.mp3', '.flac', '.m4a', '.mp4', '.ogg'])
    
    # 日志配置
    log_level: str = "INFO"
    
    # MusicBrainz 配置
    musicbrainz_app_name: str = "MusicTagger"
    musicbrainz_version: str = "0.2.0"
    musicbrainz_contact: str = "user@example.com"
    
    @classmethod
    def get_default(cls) -> 'Settings':
        """获取默认配置实例"""
        return cls()
