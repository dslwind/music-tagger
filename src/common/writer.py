"""统一的标签写入模块，支持多种音频格式"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCOM, TCOP, TEXT, ID3NoHeaderError
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from src.utils import get_logger

logger = get_logger(__name__)


class TagWriter(ABC):
    """标签写入器抽象基类"""

    @abstractmethod
    def write(self, filepath: str, metadata: Dict[str, str]) -> bool:
        """
        写入元数据到文件。

        Args:
            filepath: 文件路径
            metadata: 元数据字典，包含 title, artist, album, composer, lyricist, copyright 等

        Returns:
            写入是否成功
        """
        pass


class ID3Writer(TagWriter):
    """MP3 ID3v2.3 标签写入器"""

    def write(self, filepath: str, metadata: Dict[str, str]) -> bool:
        try:
            try:
                tags = ID3(filepath)
            except ID3NoHeaderError:
                tags = ID3()

            # 使用 v2.3 编码
            tags.add(TIT2(encoding=3, text=metadata.get('title', '')))
            tags.add(TPE1(encoding=3, text=metadata.get('artist', '')))
            tags.add(TALB(encoding=3, text=metadata.get('album', '')))
            tags.add(TCOM(encoding=3, text=metadata.get('composer', '')))
            tags.add(TEXT(encoding=3, text=metadata.get('lyricist', '')))
            tags.add(TCOP(encoding=3, text=metadata.get('copyright', '')))
            tags.save(filepath, v2_version=3)

            logger.debug(f"ID3 标签写入成功: {filepath}")
            return True
        except Exception as e:
            logger.error(f"ID3 标签写入失败: {e}")
            return False


class FLACWriter(TagWriter):
    """FLAC Vorbis 标签写入器"""

    def write(self, filepath: str, metadata: Dict[str, str]) -> bool:
        try:
            audio = FLAC(filepath)
            audio['title'] = metadata.get('title', '')
            audio['artist'] = metadata.get('artist', '')
            audio['album'] = metadata.get('album', '')
            audio['composer'] = metadata.get('composer', '')
            audio['lyricist'] = metadata.get('lyricist', '')
            audio['copyright'] = metadata.get('copyright', '')
            audio.save()

            logger.debug(f"FLAC 标签写入成功: {filepath}")
            return True
        except Exception as e:
            logger.error(f"FLAC 标签写入失败: {e}")
            return False


class MP4Writer(TagWriter):
    """M4A/MP4 标签写入器"""

    def write(self, filepath: str, metadata: Dict[str, str]) -> bool:
        try:
            audio = MP4(filepath)
            audio['\xa9nam'] = metadata.get('title', '')
            audio['\xa9ART'] = metadata.get('artist', '')
            audio['\xa9alb'] = metadata.get('album', '')
            audio['\xa9wrt'] = metadata.get('composer', '')
            audio['cprt'] = metadata.get('copyright', '')

            # 写入作词人到自定义原子
            lyricist = metadata.get('lyricist', '')
            if lyricist:
                audio['----:com.apple.iTunes:LYRICIST'] = [lyricist.encode('utf-8')]

            audio.save()

            logger.debug(f"MP4 标签写入成功: {filepath}")
            return True
        except Exception as e:
            logger.error(f"MP4 标签写入失败: {e}")
            return False


class TagWriterFactory:
    """标签写入器工厂"""

    _writers = {
        '.mp3': ID3Writer(),
        '.flac': FLACWriter(),
        '.m4a': MP4Writer(),
        '.mp4': MP4Writer(),
    }

    @classmethod
    def get_writer(cls, filepath: str) -> Optional[TagWriter]:
        """
        根据文件扩展名获取对应的写入器。

        Args:
            filepath: 文件路径

        Returns:
            对应的 TagWriter 实例，不支持的格式返回 None
        """
        ext = Path(filepath).suffix.lower()
        writer = cls._writers.get(ext)

        if writer is None:
            logger.warning(f"不支持的文件格式: {ext}")

        return writer

    @classmethod
    def write_tags(cls, filepath: str, metadata: Dict[str, str]) -> bool:
        """
        便捷方法：直接写入标签。

        Args:
            filepath: 文件路径
            metadata: 元数据字典

        Returns:
            写入是否成功
        """
        writer = cls.get_writer(filepath)
        if writer is None:
            return False

        return writer.write(filepath, metadata)

    @classmethod
    def supported_extensions(cls) -> tuple:
        """返回支持的文件扩展名"""
        return tuple(cls._writers.keys())