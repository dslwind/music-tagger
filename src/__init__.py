"""
Music Tagger - Automatic metadata tagging for audio files.

Supports MusicBrainz and Apple Music as data sources.
"""
from src.config import apple_music, musicbrainz, formats, fields

__version__ = "0.2.0"
__all__ = ['apple_music', 'musicbrainz', 'formats', 'fields']
