"""
MusicBrainz API client for retrieving music metadata.
"""
from typing import Dict, List, Optional, Any

import musicbrainzngs

from src.config import get_musicbrainz_config


class MusicBrainzClient:
    """Client for interacting with MusicBrainz API."""
    
    def __init__(
        self, 
        app_name: Optional[str] = None,
        version: Optional[str] = None, 
        contact: Optional[str] = None
    ):
        """
        Initialize MusicBrainz client.
        
        Args:
            app_name: Application name for user agent.
            version: Application version.
            contact: Contact information.
        """
        config = get_musicbrainz_config()
        self._setup(
            app_name or config.APP_NAME,
            version or config.VERSION,
            contact or config.CONTACT
        )
    
    def _setup(self, app_name: str, version: str, contact: str) -> None:
        """Configure MusicBrainz user agent."""
        musicbrainzngs.set_useragent(app_name, version, contact)
    
    def search_recording(
        self, 
        title: str, 
        artist: Optional[str] = None, 
        album: Optional[str] = None, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for recordings by title and optional filters.
        
        Args:
            title: Recording title to search.
            artist: Optional artist name filter.
            album: Optional album name filter.
            limit: Maximum number of results (default from config).
            
        Returns:
            List of recording dictionaries.
        """
        config = get_musicbrainz_config()
        search_limit = limit or config.SEARCH_LIMIT
        
        query_parts = [f'recording:"{title}"']
        if artist:
            query_parts.append(f'artist:"{artist}"')
        if album:
            query_parts.append(f'release:"{album}"')
        
        query = " AND ".join(query_parts)
        
        try:
            result = musicbrainzngs.search_recordings(query=query, limit=search_limit)
            return result.get('recording-list', [])
        except Exception as e:
            print(f"搜索 MusicBrainz 出错：{e}")
            return []
    
    def get_release_info(self, release_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific release.
        
        Args:
            release_id: MusicBrainz release ID.
            
        Returns:
            Release information dictionary or None if not found.
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
