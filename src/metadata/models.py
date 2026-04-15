"""元数据模型定义"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class MetadataField:
    """元数据字段定义"""
    name: str
    value: str = ""
    source: str = ""  # 数据来源：'local', 'remote', 'merged'
    
    def __bool__(self) -> bool:
        return bool(self.value.strip())


@dataclass
class AudioMetadata:
    """音频元数据容器"""
    
    # 基础信息
    title: MetadataField = field(default_factory=lambda: MetadataField(name='title'))
    artist: MetadataField = field(default_factory=lambda: MetadataField(name='artist'))
    album: MetadataField = field(default_factory=lambda: MetadataField(name='album'))
    
    # 创作人员
    composer: MetadataField = field(default_factory=lambda: MetadataField(name='composer'))
    lyricist: MetadataField = field(default_factory=lambda: MetadataField(name='lyricist'))
    
    # 其他信息
    copyright: MetadataField = field(default_factory=lambda: MetadataField(name='copyright'))
    label: MetadataField = field(default_factory=lambda: MetadataField(name='label'))
    genre: MetadataField = field(default_factory=lambda: MetadataField(name='genre'))
    date: MetadataField = field(default_factory=lambda: MetadataField(name='date'))
    
    # 编号信息
    tracknumber: MetadataField = field(default_factory=lambda: MetadataField(name='tracknumber'))
    discnumber: MetadataField = field(default_factory=lambda: MetadataField(name='discnumber'))
    albumartist: MetadataField = field(default_factory=lambda: MetadataField(name='albumartist'))
    
    # MusicBrainz IDs
    musicbrainz_trackid: MetadataField = field(default_factory=lambda: MetadataField(name='musicbrainz_trackid'))
    musicbrainz_artistid: MetadataField = field(default_factory=lambda: MetadataField(name='musicbrainz_artistid'))
    musicbrainz_albumid: MetadataField = field(default_factory=lambda: MetadataField(name='musicbrainz_albumid'))
    
    # 自定义字段
    custom_fields: Dict[str, MetadataField] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], source: str = 'local') -> 'AudioMetadata':
        """从字典创建元数据对象"""
        metadata = cls()
        
        field_names = [
            'title', 'artist', 'album', 'composer', 'lyricist',
            'copyright', 'label', 'genre', 'date',
            'tracknumber', 'discnumber', 'albumartist',
            'musicbrainz_trackid', 'musicbrainz_artistid', 'musicbrainz_albumid'
        ]
        
        for name in field_names:
            value = str(data.get(name, ''))
            field_obj = MetadataField(name=name, value=value, source=source)
            setattr(metadata, name, field_obj)
        
        return metadata
    
    def to_dict(self, include_empty: bool = False) -> Dict[str, str]:
        """转换为字典"""
        result = {}
        
        field_names = [
            'title', 'artist', 'album', 'composer', 'lyricist',
            'copyright', 'label', 'genre', 'date',
            'tracknumber', 'discnumber', 'albumartist',
            'musicbrainz_trackid', 'musicbrainz_artistid', 'musicbrainz_albumid'
        ]
        
        for name in field_names:
            field_obj = getattr(self, name)
            if include_empty or field_obj.value:
                result[name] = field_obj.value
        
        return result
    
    def is_empty(self) -> bool:
        """检查是否所有字段都为空"""
        field_names = [
            'title', 'artist', 'album', 'composer', 'lyricist',
            'copyright', 'label', 'genre', 'date',
            'tracknumber', 'discnumber', 'albumartist',
            'musicbrainz_trackid', 'musicbrainz_artistid', 'musicbrainz_albumid'
        ]
        
        return not any(getattr(self, name).value for name in field_names)
