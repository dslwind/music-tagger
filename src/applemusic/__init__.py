"""Apple Music integration for Music Tagger."""
from src.applemusic.finder import (
    get_audio_metadata_full,
    search_apple_music,
    scrape_web_details_selenium,
    merge_metadata,
    write_tags,
    display_diff,
)

__all__ = [
    'get_audio_metadata_full',
    'search_apple_music',
    'scrape_web_details_selenium',
    'merge_metadata',
    'write_tags',
    'display_diff',
]
