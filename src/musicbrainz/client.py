import musicbrainzngs

class MusicBrainzClient:
    def __init__(self, app_name="MusicTagger", version="0.1", contact="user@example.com"):
        self.setup(app_name, version, contact)

    def setup(self, app_name, version, contact):
        musicbrainzngs.set_useragent(app_name, version, contact)

    def search_recording(self, title, artist=None, album=None, limit=5):
        """
        Search for recordings based on title, and optional artist/album.
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
            print(f"Error searching MusicBrainz: {e}")
            return []

    def get_release_info(self, release_id):
        """
        Get detailed info for a specific release.
        """
        try:
            result = musicbrainzngs.get_release_by_id(release_id, includes=['recordings', 'artists'])
            return result.get('release', {})
        except Exception as e:
            print(f"Error fetching release info: {e}")
            return None
