"""MusicBrainz 命令行标签工具"""

import argparse
import os
from typing import Dict, Any, Optional, Set

from src.common.audio import AudioFileHandler
from src.musicbrainz.client import MusicBrainzClient


class MusicBrainzTagger:
    """MusicBrainz 标签处理器"""
    
    def __init__(self):
        self.mb_client = MusicBrainzClient()
    
    def process_file(self, filepath: str) -> bool:
        """
        处理单个文件
        
        Args:
            filepath: 音频文件路径
            
        Returns:
            是否成功处理
        """
        if not os.path.exists(filepath):
            print(f"文件未找到：{filepath}")
            return False
        
        # 1. 加载文件
        try:
            handler = AudioFileHandler(filepath)
            current_tags = handler.get_tags()
            print(f"当前标签：{current_tags}")
        except Exception as e:
            print(f"加载文件出错：{e}")
            return False
        
        # 2. 搜索 MusicBrainz
        print("\n正在搜索 MusicBrainz...")
        
        title = current_tags.get('title')
        if not title:
            title = os.path.splitext(os.path.basename(filepath))[0]
            print(f"未找到标题标签。使用文件名：{title}")
        
        results = self.mb_client.search_recording(
            title, 
            artist=current_tags.get('artist'),
            album=current_tags.get('album')
        )
        
        if not results:
            print("在 MusicBrainz 上未找到结果。")
            return False
        
        # 3. 显示结果并询问用户
        print("\n找到匹配结果:")
        for i, recording in enumerate(results):
            track_title = recording.get('title', 'Unknown')
            artist_credit = recording.get('artist-credit', [])
            artist_name = artist_credit[0]['artist']['name'] if artist_credit else "Unknown"
            releases = recording.get('release-list', [])
            album_name = releases[0]['title'] if releases else "Unknown"
            
            print(f"{i+1}. {track_title} - {artist_name} (Album: {album_name})")
        
        while True:
            choice = input("\n请选择匹配项 (序号) 进行预览，或输入 'q' 退出：")
            if choice.lower() == 'q':
                return False
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(results):
                    selected = results[index]
                    
                    # 准备新标签
                    new_tags = self._prepare_tags(selected)
                    
                    # 预览比较
                    self._display_preview(current_tags, new_tags)
                    
                    confirm = input("\n应用这些更改？(y/n/q): ")
                    if confirm.lower() == 'y':
                        handler.update_tags(new_tags)
                        print("完成!")
                        return True
                    elif confirm.lower() == 'q':
                        return False
                    else:
                        print("已取消。请选择其他匹配项。")
                else:
                    print("无效的选择。")
            except ValueError:
                print("无效的输入。")
        
        return False
    
    def _prepare_tags(self, recording: Dict[str, Any]) -> Dict[str, str]:
        """从录音记录准备标签"""
        new_tags = {
            'title': recording.get('title', ''),
            'musicbrainz_trackid': recording.get('id', ''),
        }
        
        # 获取艺术家信息
        artist_credit = recording.get('artist-credit', [])
        if artist_credit:
            new_tags['artist'] = artist_credit[0]['artist']['name']
            if 'artist' in artist_credit[0]:
                new_tags['musicbrainz_artistid'] = artist_credit[0]['artist']['id']
        
        # 获取专辑信息
        releases = recording.get('release-list', [])
        if releases:
            release = releases[0]
            new_tags['album'] = release.get('title', '')
            new_tags['date'] = release.get('date', '')
            new_tags['musicbrainz_albumid'] = release.get('id', '')
            
            # 获取详细发行信息
            try:
                release_info = self.mb_client.get_release_info(release.get('id'))
                if release_info:
                    # 更新专辑艺术家
                    rel_artist_credit = release_info.get('artist-credit', [])
                    if rel_artist_credit:
                        new_tags['albumartist'] = rel_artist_credit[0]['artist']['name']
                    
                    # 获取轨道编号和光盘编号
                    for medium in release_info.get('medium-list', []):
                        for track in medium.get('track-list', []):
                            if track.get('recording', {}).get('id') == recording.get('id'):
                                new_tags['tracknumber'] = track.get('number', '')
                                new_tags['discnumber'] = str(medium.get('position', ''))
                                break
            except Exception as e:
                print(f"警告：无法获取详细发行信息：{e}")
        
        # 获取流派
        tags_list = recording.get('tag-list', [])
        if tags_list:
            genres = [t['name'] for t in tags_list[:3]]
            new_tags['genre'] = ', '.join(genres)
        
        return new_tags
    
    def _display_preview(self, current: Dict[str, str], new: Dict[str, str]):
        """显示标签预览对比"""
        print("\n--- 标签预览 ---")
        print(f"{'标签':<20} {'当前值':<30} {'新值':<30}")
        print("-" * 80)
        
        interesting_keys = [
            'title', 'artist', 'album', 'albumartist', 'date',
            'tracknumber', 'discnumber', 'genre', 'musicbrainz_trackid'
        ]
        
        for key in interesting_keys:
            current_val = current.get(key, '')
            new_val = new.get(key, '')
            
            if current_val or new_val:
                marker = "*" if current_val != new_val and new_val else " "
                c_str = str(current_val)[:28]
                n_str = str(new_val)[:28]
                
                if len(str(current_val)) > 28:
                    c_str = c_str[:25] + "..."
                if len(str(new_val)) > 28:
                    n_str = n_str[:25] + "..."
                
                print(f"{marker} {key.capitalize():<18} {c_str:<30} {n_str:<30}")
        
        print("-" * 80)
        print("* 表示有变更")


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="Music Tagger 命令行工具")
    parser.add_argument("path", help="音乐文件路径")
    args = parser.parse_args()
    
    tagger = MusicBrainzTagger()
    tagger.process_file(args.path)


if __name__ == "__main__":
    main()
