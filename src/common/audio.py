"""
Audio file handling utilities for Music Tagger.
Provides unified interface for reading and writing metadata across different audio formats.
"""
import os
from typing import Dict, Optional, Any

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4

from src.config import formats


class AudioFileHandler:
    """Handles loading, reading, and writing metadata for audio files."""
    
    SUPPORTED_EXTENSIONS = formats.GENERAL
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.audio: Optional[Any] = None
        self._load_file()
    
    def _load_file(self) -> None:
        """Load audio file and detect format."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"文件未找到：{self.filepath}")
        
        try:
            # Auto-detect file type
            self.audio = mutagen.File(self.filepath, easy=True)
            
            if self.audio is None:
                # Fallback for specific formats
                ext = self.filepath.lower()[-4:]
                fallback_handlers = {
                    '.mp3': lambda: MP3(self.filepath, ID3=EasyID3),
                    '.flac': lambda: FLAC(self.filepath),
                    '.ogg': lambda: OggVorbis(self.filepath),
                }
                
                handler = fallback_handlers.get(ext)
                if handler:
                    self.audio = handler()
                else:
                    raise ValueError(f"不支持的文件格式：{ext}")
                    
        except Exception as e:
            raise ValueError(f"加载文件出错：{e}")
    
    def get_tags(self) -> Dict[str, str]:
        """
        Extract common metadata tags from audio file.
        
        Returns:
            Dictionary of metadata fields with string values.
        """
        if not self.audio:
            return {}
        
        def get_first(key: str, default: str = '') -> str:
            """Safely get first value from tag list."""
            value = self.audio.get(key, [default])
            return value[0] if value else default
        
        return {
            'title': get_first('title'),
            'artist': get_first('artist'),
            'album': get_first('album'),
            'date': get_first('date'),
            'tracknumber': get_first('tracknumber'),
            'albumartist': get_first('albumartist'),
            'discnumber': get_first('discnumber'),
            'genre': get_first('genre'),
            'musicbrainz_trackid': get_first('musicbrainz_trackid'),
            'musicbrainz_artistid': get_first('musicbrainz_artistid'),
            'musicbrainz_albumid': get_first('musicbrainz_albumid'),
        }
    
    def update_tags(self, metadata: Dict[str, str]) -> None:
        """
        Update audio file metadata with provided values.
        
        Args:
            metadata: Dictionary of tag names to values.
        """
        if not self.audio:
            return
        
        for key, value in metadata.items():
            if value:
                self.audio[key] = str(value)
        
        self.audio.save()
        print(f"标签已更新：{self.filepath}")
    
    @classmethod
    def is_supported(cls, filename: str) -> bool:
        """Check if file extension is supported."""
        return filename.lower().endswith(cls.SUPPORTED_EXTENSIONS)
