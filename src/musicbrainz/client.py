import musicbrainzngs

from src.utils import get_logger, get_config

logger = get_logger(__name__)


class MusicBrainzClient:
    def __init__(self, app_name=None, version=None, contact=None):
        config = get_config()
        self.setup(
            app_name=app_name or config.get('musicbrainz', 'app_name', default='MusicTagger'),
            version=version or config.get('musicbrainz', 'version', default='0.1'),
            contact=contact or config.get('musicbrainz', 'contact', default='user@example.com')
        )

    def setup(self, app_name, version, contact):
        musicbrainzngs.set_useragent(app_name, version, contact)

    def search_recording(self, title, artist=None, album=None, limit=5):
        """
        根据标题以及可选的艺术家/专辑搜索录音。
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
            logger.error(f"搜索 MusicBrainz 出错: {e}")
            return []

    def get_release_info(self, release_id):
        """
        获取特定发行的详细信息。
        """
        try:
            result = musicbrainzngs.get_release_by_id(release_id, includes=['recordings', 'artists'])
            return result.get('release', {})
        except Exception as e:
            logger.error(f"获取发行信息出错: {e}")
            return None
