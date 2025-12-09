import argparse
import os
from src.common.audio import AudioFileHandler
from src.musicbrainz.client import MusicBrainzClient

def main():
    parser = argparse.ArgumentParser(description="Music Tagger 命令行工具")
    parser.add_argument("path", help="音乐文件路径")
    args = parser.parse_args()

    filepath = args.path
    if not os.path.exists(filepath):
        print(f"文件未找到: {filepath}")
        return

    # 1. 加载文件
    try:
        handler = AudioFileHandler(filepath)
        current_tags = handler.get_tags()
        print(f"当前标签: {current_tags}")
    except Exception as e:
        print(f"加载文件出错: {e}")
        return

    # 2. 搜索 MusicBrainz
    mb_client = MusicBrainzClient()
    print("\n正在搜索 MusicBrainz...")
    
    # 如果可用，使用现有标签进行搜索，否则询问用户？
    # 目前，假设如果标签为空，我们使用文件名，或者直接使用我们拥有的信息。
    title = current_tags.get('title')
    if not title:
        # 回退到不带扩展名的文件名
        title = os.path.splitext(os.path.basename(filepath))[0]
        print(f"未找到标题标签。使用文件名: {title}")

    results = mb_client.search_recording(title, artist=current_tags.get('artist'), album=current_tags.get('album'))

    if not results:
        print("在 MusicBrainz 上未找到结果。")
        return

    # 3. 显示结果并询问用户
    print("\n找到匹配结果:")
    for i, recording in enumerate(results):
        # 提取一些有用的信息进行显示
        track_title = recording.get('title', 'Unknown')
        artist_credit = recording.get('artist-credit', [])
        artist_name = artist_credit[0]['artist']['name'] if artist_credit else "Unknown"
        releases = recording.get('release-list', [])
        album_name = releases[0]['title'] if releases else "Unknown"
        
        print(f"{i+1}. {track_title} - {artist_name} (Album: {album_name})")

    while True:
        choice = input("\n请选择匹配项 (序号) 进行预览，或输入 'q' 退出: ")
        if choice.lower() == 'q':
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(results):
                selected = results[index]
                
                # 准备新标签
                new_tags = {
                    'title': selected.get('title'),
                    'musicbrainz_trackid': selected.get('id'),
                }
                
                # 获取艺术家信息
                artist_credit = selected.get('artist-credit', [])
                if artist_credit:
                     new_tags['artist'] = artist_credit[0]['artist']['name']
                     if 'artist' in artist_credit[0]:
                         new_tags['musicbrainz_artistid'] = artist_credit[0]['artist']['id']

                # 获取专辑信息
                releases = selected.get('release-list', [])
                if releases:
                    release = releases[0]
                    new_tags['album'] = release.get('title')
                    new_tags['date'] = release.get('date')
                    new_tags['musicbrainz_albumid'] = release.get('id')
                    
                    # 如果可用，获取专辑艺术家（通常与艺术家相同，但最好有）
                    # 搜索结果可能没有完整的发行艺术家信用，检查是否存在
                    # 目前，如果搜索结果中没有，我们可能需要获取发行信息以获取详细信息
                    # 但让我们检查一下搜索结果中通常有什么。
                    # 通常 release-list 项目也有 'artist-credit'。
                    
                    # 尝试获取光盘编号和轨道编号（如果搜索结果中可用）（通常有限）
                    # 如果我们想要健壮的数据，我们可能应该在这里调用 get_release_by_id
                    # 但为了保持快速，让我们看看我们能得到什么。
                    # 如果缺少 'medium-list'，我们可能会暂时跳过光盘编号或获取它。
                    
                    # 让我们快速获取特定发行的详细轨道信息
                    # 这确保我们获得正确的轨道编号、光盘编号和专辑艺术家
                    try:
                        release_info = mb_client.get_release_info(release.get('id'))
                        if release_info:
                            # 更新专辑艺术家
                            rel_artist_credit = release_info.get('artist-credit', [])
                            if rel_artist_credit:
                                new_tags['albumartist'] = rel_artist_credit[0]['artist']['name']
                            
                            # 在发行中找到我们的轨道以获取轨道/光盘编号
                            # 这有点复杂，因为发行有媒体 -> 轨道
                            # 我们通过录音 ID 匹配
                            for medium in release_info.get('medium-list', []):
                                for track in medium.get('track-list', []):
                                    if track.get('recording', {}).get('id') == selected.get('id'):
                                        new_tags['tracknumber'] = track.get('number')
                                        new_tags['discnumber'] = str(medium.get('position'))
                                        break
                    except Exception as e:
                        print(f"警告: 无法获取详细发行信息: {e}")

                # 获取流派 (标签)
                tags_list = selected.get('tag-list', [])
                if tags_list:
                    # 连接前 3 个标签或类似标签
                    genres = [t['name'] for t in tags_list[:3]]
                    new_tags['genre'] = ', '.join(genres)
                
                # 预览比较
                print("\n--- 标签预览 ---")
                print(f"{'标签':<20} {'当前值':<30} {'新值':<30}")
                print("-" * 80)
                
                # 合并当前和新标签的键以显示所有相关字段
                all_keys = set(current_tags.keys()) | set(new_tags.keys())
                # 筛选感兴趣的键
                interesting_keys = ['title', 'artist', 'album', 'albumartist', 'date', 'tracknumber', 'discnumber', 'genre', 'musicbrainz_trackid']
                
                for key in interesting_keys:
                    current_val = current_tags.get(key, '')
                    new_val = new_tags.get(key, '')
                    
                    # 仅当其中一个有值时显示
                    if current_val or new_val:
                        # 如果不同则高亮显示更改
                        marker = "*" if current_val != new_val and new_val else " "
                        # 截断长值
                        c_str = str(current_val)
                        n_str = str(new_val)
                        if len(c_str) > 28: c_str = c_str[:25] + "..."
                        if len(n_str) > 28: n_str = n_str[:25] + "..."
                        
                        print(f"{marker} {key.capitalize():<18} {c_str:<30} {n_str:<30}")
                
                print("-" * 80)
                print("* 表示有变更")

                confirm = input("\n应用这些更改? (y/n/q): ")
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
