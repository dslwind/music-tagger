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
            raise FileNotFoundError(f"File not found: {self.filepath}")
        
        try:
            # Auto-detect file type
            self.audio = mutagen.File(self.filepath, easy=True)
            if self.audio is None:
                # Fallback for specific types if auto-detect fails or returns None
                if self.filepath.lower().endswith('.mp3'):
                    self.audio = MP3(self.filepath, ID3=EasyID3)
                elif self.filepath.lower().endswith('.flac'):
                    self.audio = FLAC(self.filepath)
                elif self.filepath.lower().endswith('.ogg'):
                    self.audio = OggVorbis(self.filepath)
                else:
                    raise ValueError("Unsupported file format")
        except Exception as e:
            raise ValueError(f"Error loading file: {e}")

    def get_tags(self):
        """Returns a dictionary of common tags."""
        if not self.audio:
            return {}
        
        # Helper to safely get first item
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
        Updates tags with the provided metadata dictionary.
        metadata keys should match standard tag names (title, artist, album, etc.)
        """
        if not self.audio:
            return

        for key, value in metadata.items():
            if value:
                self.audio[key] = value
        
        self.audio.save()
        print(f"Tags updated for {self.filepath}")
