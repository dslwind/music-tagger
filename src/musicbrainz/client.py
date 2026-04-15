"""MusicBrainz API 客户端"""

import musicbrainzngs
from typing import Optional, List, Dict, Any

from src.config import Settings


class MusicBrainzClient:
    """MusicBrainz API 客户端封装"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.get_default()
        self.setup()
    
    def setup(self):
        """配置 MusicBrainz 用户代理"""
        musicbrainzngs.set_useragent(
            self.settings.musicbrainz_app_name,
            self.settings.musicbrainz_version,
            self.settings.musicbrainz_contact
        )
    
    def search_recording(
        self, 
        title: str, 
        artist: Optional[str] = None,
        album: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索录音
        
        Args:
            title: 歌曲标题
            artist: 艺术家名称（可选）
            album: 专辑名称（可选）
            limit: 返回结果数量限制
            
        Returns:
            录音列表
        """
        query_parts = [f'recording:"{title}"']
        if artist:
            query_parts.append(f'artist:"{artist}"')
        if album:
            query_parts.append(f'release:"{album}"')
        
        query = " AND ".join(query_parts)
        
        try:
            result = musicbrainzngs.search_recordings(query=query, limit=limit)
            return result.get('recording-list', [])
        except Exception as e:
            print(f"搜索 MusicBrainz 出错：{e}")
            return []
    
    def get_release_info(self, release_id: str) -> Optional[Dict[str, Any]]:
        """
        获取发行详细信息
        
        Args:
            release_id: 发行 ID
            
        Returns:
            发行信息字典
        """
        try:
            result = musicbrainzngs.get_release_by_id(
                release_id, 
                includes=['recordings', 'artists']
            )
            return result.get('release', {})
        except Exception as e:
            print(f"获取发行信息出错：{e}")
            return None
