import musicbrainzngs

class MusicBrainzClient:
    def __init__(self, app_name="MusicTagger", version="0.1", contact="user@example.com"):
        self.setup(app_name, version, contact)

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
            print(f"搜索 MusicBrainz 出错: {e}")
            return []

    def get_release_info(self, release_id):
        """
        获取特定发行的详细信息。
        """
        try:
            result = musicbrainzngs.get_release_by_id(release_id, includes=['recordings', 'artists'])
            return result.get('release', {})
        except Exception as e:
            print(f"获取发行信息出错: {e}")
            return None
