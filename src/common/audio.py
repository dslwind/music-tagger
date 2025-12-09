import os
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis

class AudioFileHandler:
    def __init__(self, filepath):
        self.filepath = filepath
        self.audio = None
        self.load_file()

    def load_file(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"文件未找到: {self.filepath}")
        
        try:
            # 自动检测文件类型
            self.audio = mutagen.File(self.filepath, easy=True)
            if self.audio is None:
                # 如果自动检测失败或返回 None，则针对特定类型进行回退

                if self.filepath.lower().endswith('.mp3'):
                    self.audio = MP3(self.filepath, ID3=EasyID3)
                elif self.filepath.lower().endswith('.flac'):
                    self.audio = FLAC(self.filepath)
                elif self.filepath.lower().endswith('.ogg'):
                    self.audio = OggVorbis(self.filepath)
                else:
                    raise ValueError("不支持的文件格式")
        except Exception as e:
            raise ValueError(f"加载文件出错: {e}")

    def get_tags(self):
        """返回通用标签字典。"""
        if not self.audio:
            return {}
        
        # 辅助函数：安全获取第一项
        def get_first(key, default=''):
            return self.audio.get(key, [default])[0]

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

    def update_tags(self, metadata):
        """
        使用提供的元数据字典更新标签。
        metadata 键应匹配标准标签名称 (title, artist, album 等)
        """
        if not self.audio:
            return

        for key, value in metadata.items():
            if value:
                self.audio[key] = value
        
        self.audio.save()
        print(f"标签已更新: {self.filepath}")
