"""
Configuration settings for Music Tagger.
Centralizes all magic strings, constants, and configuration values.
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AppleMusicConfig:
    """Apple Music API and scraping configuration."""
    COUNTRY: str = "HK"  # Default region (Hong Kong for Chinese support)
    SEARCH_LIMIT: int = 5
    API_BASE_URL: str = "https://itunes.apple.com/search"
    REQUEST_TIMEOUT: int = 10
    
    # Selenium options
    HEADLESS: bool = True
    DISABLE_GPU: bool = True
    MUTE_AUDIO: bool = True
    BLOCK_IMAGES: bool = True
    USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    )
    
    # Metadata field mappings
    COMPOSER_KEYWORDS: List[str] = None
    LYRICIST_KEYWORDS: List[str] = None
    
    def __post_init__(self):
        if self.COMPOSER_KEYWORDS is None:
            self.COMPOSER_KEYWORDS = [
                '作曲', '作曲家', '音樂創作人', 
                'Composer', 'Written By', 'Music'
            ]
        if self.LYRICIST_KEYWORDS is None:
            self.LYRICIST_KEYWORDS = [
                '填詞', '作词', '作詞', '音樂創作人', 
                'Lyricist', 'Lyrics'
            ]


@dataclass
class MusicBrainzConfig:
    """MusicBrainz API configuration."""
    APP_NAME: str = "MusicTagger"
    VERSION: str = "0.2.0"
    CONTACT: str = "user@example.com"
    SEARCH_LIMIT: int = 5


@dataclass
class SupportedFormats:
    """Supported audio file extensions."""
    APPLE_MUSIC: tuple = ('.mp3', '.flac', '.m4a', '.mp4')
    GENERAL: tuple = ('.mp3', '.flac', '.m4a', '.mp4', '.ogg')


@dataclass
class MetadataFields:
    """Standard metadata field names."""
    COMMON_FIELDS: List[str] = None
    INTERESTING_FIELDS: List[str] = None
    
    def __post_init__(self):
        if self.COMMON_FIELDS is None:
            self.COMMON_FIELDS = [
                'title', 'artist', 'album', 
                'composer', 'lyricist', 'copyright'
            ]
        if self.INTERESTING_FIELDS is None:
            self.INTERESTING_FIELDS = [
                'title', 'artist', 'album', 'albumartist', 
                'date', 'tracknumber', 'discnumber', 'genre',
                'musicbrainz_trackid'
            ]


# Global configuration instances
apple_music = AppleMusicConfig()
musicbrainz = MusicBrainzConfig()
formats = SupportedFormats()
fields = MetadataFields()


def get_apple_music_config() -> AppleMusicConfig:
    """Get Apple Music configuration."""
    return apple_music


def get_musicbrainz_config() -> MusicBrainzConfig:
    """Get MusicBrainz configuration."""
    return musicbrainz
