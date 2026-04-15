"""元数据合并策略"""

from typing import Dict, Any
from .models import AudioMetadata, MetadataField


class MetadataMerger:
    """
    元数据合并器
    
    合并策略：
    1. 如果 Remote 有值，优先使用 Remote (更新)
    2. 如果 Remote 为空，但 Local 有值，保留 Local (不覆盖为空)
    3. 只有当 Remote 和 Local 都为空时，结果才为空
    """
    
    def __init__(self, prefer_remote: bool = True):
        """
        初始化合并器
        
        Args:
            prefer_remote: 是否优先使用远程数据，默认为 True
        """
        self.prefer_remote = prefer_remote
    
    def merge(self, local: AudioMetadata, remote: AudioMetadata) -> AudioMetadata:
        """
        合并两个元数据对象
        
        Args:
            local: 本地元数据
            remote: 远程元数据
            
        Returns:
            合并后的元数据对象
        """
        result = AudioMetadata()
        
        field_names = [
            'title', 'artist', 'album', 'composer', 'lyricist',
            'copyright', 'label', 'genre', 'date',
            'tracknumber', 'discnumber', 'albumartist',
            'musicbrainz_trackid', 'musicbrainz_artistid', 'musicbrainz_albumid'
        ]
        
        for name in field_names:
            local_field = getattr(local, name)
            remote_field = getattr(remote, name)
            
            if self.prefer_remote and remote_field.value:
                # 优先使用远程数据
                merged_field = MetadataField(
                    name=name,
                    value=remote_field.value,
                    source='remote'
                )
            elif local_field.value:
                # 保留本地数据
                merged_field = MetadataField(
                    name=name,
                    value=local_field.value,
                    source='local'
                )
            else:
                # 两者都为空
                merged_field = MetadataField(
                    name=name,
                    value='',
                    source='merged'
                )
            
            setattr(result, name, merged_field)
        
        return result
    
    @staticmethod
    def merge_dicts(local: Dict[str, Any], remote: Dict[str, Any]) -> Dict[str, str]:
        """
        合并两个字典形式的元数据（向后兼容）
        
        Args:
            local: 本地元数据字典
            remote: 远程元数据字典
            
        Returns:
            合并后的字典
        """
        final = {}
        keys = ['title', 'artist', 'album', 'composer', 'lyricist', 'copyright']
        
        for key in keys:
            r_val = remote.get(key, '').strip()
            l_val = local.get(key, '').strip()
            
            if r_val:
                final[key] = r_val
            elif l_val:
                final[key] = l_val
            else:
                final[key] = ''
        
        return final
