"""音频文件处理模块"""

import os
from enum import Enum
from typing import Optional, Dict, Any, List

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCOM, TCOP, TEXT, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4


class AudioFormat(Enum):
    """支持的音频格式"""
    MP3 = '.mp3'
    FLAC = '.flac'
    M4A = '.m4a'
    MP4 = '.mp4'
    OGG = '.ogg'
    UNKNOWN = 'unknown'
    
    @classmethod
    def from_filename(cls, filename: str) -> 'AudioFormat':
        """从文件名识别音频格式"""
        ext = os.path.splitext(filename)[1].lower()
        try:
            return cls(ext)
        except ValueError:
            return cls.UNKNOWN
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """获取所有支持的扩展名"""
        return [fmt.value for fmt in cls if fmt != cls.UNKNOWN]


class AudioFileHandler:
    """音频文件处理器"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.audio = None
        self.format = AudioFormat.from_filename(filepath)
        self.load_file()
    
    def load_file(self):
        """加载音频文件"""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"文件未找到：{self.filepath}")
        
        try:
            # 自动检测文件类型
            self.audio = mutagen.File(self.filepath, easy=True)
            if self.audio is None:
                # 如果自动检测失败，则针对特定类型进行回退
                if self.format == AudioFormat.MP3:
                    self.audio = MP3(self.filepath, ID3=EasyID3)
                elif self.format == AudioFormat.FLAC:
                    self.audio = FLAC(self.filepath)
                elif self.format == AudioFormat.OGG:
                    self.audio = OggVorbis(self.filepath)
                else:
                    raise ValueError(f"不支持的文件格式：{self.format.value}")
        except Exception as e:
            raise ValueError(f"加载文件出错：{e}")
    
    def get_tags(self) -> Dict[str, str]:
        """返回通用标签字典"""
        if not self.audio:
            return {}
        
        # 辅助函数：安全获取第一项
        def get_first(key: str, default: str = '') -> str:
            value = self.audio.get(key, [default])
            return value[0] if value else default
        
        tags = {
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
        return tags
    
    def update_tags(self, metadata: Dict[str, Any]):
        """
        使用提供的元数据字典更新标签
        
        Args:
            metadata: 元数据字典，键应匹配标准标签名称
        """
        if not self.audio:
            return
        
        for key, value in metadata.items():
            if value:
                self.audio[key] = value
        
        self.audio.save()
    
    @staticmethod
    def read_full_metadata(file_path: str) -> Optional[Dict[str, str]]:
        """
        读取本地音频文件的详细元数据
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            元数据字典，如果读取失败则返回 None
        """
        if not os.path.exists(file_path):
            print(f"错误：文件不存在 -> {file_path}")
            return None
        
        meta = {
            'title': '', 'artist': '', 'album': '',
            'composer': '', 'lyricist': '', 'copyright': ''
        }
        
        try:
            # 使用 easy=True 接口读取通用标签
            audio = mutagen.File(file_path, easy=True)
            
            if audio:
                meta['title'] = audio.get('title', [''])[0]
                meta['artist'] = audio.get('artist', [''])[0]
                meta['album'] = audio.get('album', [''])[0]
                meta['composer'] = audio.get('composer', [''])[0]
                meta['copyright'] = audio.get('copyright', [''])[0]
                meta['lyricist'] = audio.get('lyricist', [''])[0]
            
            # 如果没有标题，回退到文件名
            if not meta['title']:
                meta['title'] = os.path.splitext(os.path.basename(file_path))[0]
                
            return meta
        except Exception as e:
            print(f"读取本地元数据出错：{e}")
            return meta
    
    @staticmethod
    def write_tags(file_path: str, meta: Dict[str, str]) -> bool:
        """
        写入标签（仅写入文本，不处理封面）
        
        Args:
            file_path: 音频文件路径
            meta: 元数据字典
            
        Returns:
            是否写入成功
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            # === MP3 (ID3v2.3) ===
            if ext == '.mp3':
                try:
                    tags = ID3(file_path)
                except ID3NoHeaderError:
                    tags = ID3()
                
                # 使用 v2.3 编码 (通常为 UTF-16)
                tags.add(TIT2(encoding=3, text=meta['title']))
                tags.add(TPE1(encoding=3, text=meta['artist']))
                tags.add(TALB(encoding=3, text=meta['album']))
                tags.add(TCOM(encoding=3, text=meta['composer']))
                tags.add(TEXT(encoding=3, text=meta['lyricist']))
                tags.add(TCOP(encoding=3, text=meta['copyright']))
                tags.save(file_path, v2_version=3)
            
            # === FLAC ===
            elif ext == '.flac':
                audio = FLAC(file_path)
                audio['title'] = meta['title']
                audio['artist'] = meta['artist']
                audio['album'] = meta['album']
                audio['composer'] = meta['composer']
                audio['lyricist'] = meta['lyricist']
                audio['copyright'] = meta['copyright']
                audio.save()
            
            # === M4A/MP4 ===
            elif ext in ['.m4a', '.mp4']:
                audio = MP4(file_path)
                audio['\xa9nam'] = meta['title']
                audio['\xa9ART'] = meta['artist']
                audio['\xa9alb'] = meta['album']
                audio['\xa9wrt'] = meta['composer']
                audio['cprt'] = meta['copyright']
                
                # 写入作词人到自定义原子 (兼容 Mp3tag)
                if meta['lyricist']:
                    try:
                        # Mutagen 要求自定义 tag 值为 bytes 列表
                        audio['----:com.apple.iTunes:LYRICIST'] = [meta['lyricist'].encode('utf-8')]
                    except Exception as e:
                        print(f" (M4A 作词人写入警告：{e})", end="")
                
                audio.save()
            
            else:
                print(f"暂不支持写入 {ext} 格式")
                return False
            
            return True
        except Exception as e:
            print(f"写入文件失败：{e}")
            return False
