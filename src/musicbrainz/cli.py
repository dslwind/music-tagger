"""
MusicBrainz command-line interface for tagging audio files.
"""
import argparse
import os
from typing import Dict, Any, List

from src.common.audio import AudioFileHandler
from src.musicbrainz.client import MusicBrainzClient
from src.config import fields


def display_tag_preview(current_tags: Dict[str, str], new_tags: Dict[str, str]) -> None:
    """Display a comparison table of current vs new tag values."""
    print("\n--- 标签预览 ---")
    print(f"{'标签':<20} {'当前值':<30} {'新值':<30}")
    print("-" * 80)
    
    for key in fields.INTERESTING_FIELDS:
        current_val = current_tags.get(key, '')
        new_val = new_tags.get(key, '')
        
        # Only display if at least one has a value
        if current_val or new_val:
            marker = "*" if current_val != new_val and new_val else " "
            c_str = str(current_val)[:25] + "..." if len(str(current_val)) > 28 else str(current_val)
            n_str = str(new_val)[:25] + "..." if len(str(new_val)) > 28 else str(new_val)
            
            print(f"{marker} {key.capitalize():<18} {c_str:<30} {n_str:<30}")
    
    print("-" * 80)
    print("* 表示有变更")


def extract_recording_info(selected: Dict[str, Any], mb_client: MusicBrainzClient) -> Dict[str, str]:
    """
    Extract metadata from selected MusicBrainz recording.
    
    Args:
        selected: Selected recording dictionary from search results.
        mb_client: MusicBrainz client instance.
        
    Returns:
        Dictionary of extracted metadata tags.
    """
    new_tags: Dict[str, str] = {
        'title': selected.get('title', ''),
        'musicbrainz_trackid': selected.get('id', ''),
    }
    
    # Extract artist information
    artist_credit = selected.get('artist-credit', [])
    if artist_credit:
        new_tags['artist'] = artist_credit[0]['artist']['name']
        if 'artist' in artist_credit[0]:
            new_tags['musicbrainz_artistid'] = artist_credit[0]['artist']['id']
    
    # Extract album/release information
    releases = selected.get('release-list', [])
    if releases:
        release = releases[0]
        new_tags['album'] = release.get('title', '')
        new_tags['date'] = release.get('date', '')
        new_tags['musicbrainz_albumid'] = release.get('id', '')
        
        # Get detailed release info for album artist and track/disc numbers
        try:
            release_info = mb_client.get_release_info(release.get('id'))
            if release_info:
                # Album artist
                rel_artist_credit = release_info.get('artist-credit', [])
                if rel_artist_credit:
                    new_tags['albumartist'] = rel_artist_credit[0]['artist']['name']
                
                # Find track to get track/disc numbers
                for medium in release_info.get('medium-list', []):
                    for track in medium.get('track-list', []):
                        if track.get('recording', {}).get('id') == selected.get('id'):
                            new_tags['tracknumber'] = track.get('number', '')
                            new_tags['discnumber'] = str(medium.get('position', ''))
                            break
        except Exception as e:
            print(f"警告：无法获取详细发行信息：{e}")
    
    # Extract genres/tags
    tags_list = selected.get('tag-list', [])
    if tags_list:
        genres = [t['name'] for t in tags_list[:3]]
        new_tags['genre'] = ', '.join(genres)
    
    return new_tags


def main() -> None:
    """Main entry point for MusicBrainz CLI."""
    parser = argparse.ArgumentParser(description="Music Tagger 命令行工具")
    parser.add_argument("path", help="音乐文件路径")
    args = parser.parse_args()
    
    filepath = args.path
    if not os.path.exists(filepath):
        print(f"文件未找到：{filepath}")
        return
    
    # Load file and get current tags
    try:
        handler = AudioFileHandler(filepath)
        current_tags = handler.get_tags()
        print(f"当前标签：{current_tags}")
    except Exception as e:
        print(f"加载文件出错：{e}")
        return
    
    # Search MusicBrainz
    mb_client = MusicBrainzClient()
    print("\n正在搜索 MusicBrainz...")
    
    # Use existing tags or fallback to filename
    title = current_tags.get('title')
    if not title:
        title = os.path.splitext(os.path.basename(filepath))[0]
        print(f"未找到标题标签。使用文件名：{title}")
    
    results = mb_client.search_recording(
        title, 
        artist=current_tags.get('artist'), 
        album=current_tags.get('album')
    )
    
    if not results:
        print("在 MusicBrainz 上未找到结果。")
        return
    
    # Display search results
    print("\n找到匹配结果:")
    for i, recording in enumerate(results):
        track_title = recording.get('title', 'Unknown')
        artist_credit = recording.get('artist-credit', [])
        artist_name = artist_credit[0]['artist']['name'] if artist_credit else "Unknown"
        releases = recording.get('release-list', [])
        album_name = releases[0]['title'] if releases else "Unknown"
        
        print(f"{i+1}. {track_title} - {artist_name} (Album: {album_name})")
    
    # User selection loop
    while True:
        choice = input("\n请选择匹配项 (序号) 进行预览，或输入 'q' 退出：")
        if choice.lower() == 'q':
            return
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(results):
                selected = results[index]
                new_tags = extract_recording_info(selected, mb_client)
                
                # Display preview
                display_tag_preview(current_tags, new_tags)
                
                confirm = input("\n应用这些更改？(y/n/q): ")
                if confirm.lower() == 'y':
                    handler.update_tags(new_tags)
                    print("完成!")
                    return
                elif confirm.lower() == 'q':
                    return
                else:
                    print("已取消。请选择其他匹配项。")
            else:
                print("无效的选择。")
        except ValueError:
            print("无效的输入。")


if __name__ == "__main__":
    main()
