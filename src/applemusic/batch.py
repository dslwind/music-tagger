"""Apple Music 批量标签处理器"""

import os
import argparse
from typing import Optional, List

from src.common.audio import AudioFileHandler
from src.config import Settings
from src.drivers.browser import BrowserDriver, DriverFactory
from src.applemusic.finder import AppleMusicTagger, AppleMusicSearcher


class BatchProcessor:
    """批量处理处理器"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.get_default()
        self.driver: Optional[BrowserDriver] = None
        self.tagger: Optional[AppleMusicTagger] = None
    
    def _get_supported_files(self, folder: str) -> List[str]:
        """获取文件夹中所有支持的音频文件"""
        extensions = {'.mp3', '.flac', '.m4a', '.mp4', '.ogg'}
        files = []
        
        for filename in os.listdir(folder):
            ext = os.path.splitext(filename)[1].lower()
            if ext in extensions:
                files.append(os.path.join(folder, filename))
        
        return sorted(files)
    
    def process_folder(self, folder_path: str) -> int:
        """
        处理整个文件夹
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            成功处理的文件数量
        """
        if not os.path.exists(folder_path):
            print("文件夹未找到。")
            return 0
        
        files = self._get_supported_files(folder_path)
        
        if not files:
            print("未找到支持的音频文件。")
            return 0
        
        print(f"找到 {len(files)} 个文件。正在初始化 Selenium...")
        
        # 初始化共享驱动
        try:
            self.driver = DriverFactory.create_default()
            self.tagger = AppleMusicTagger(self.settings)
            self.tagger.set_driver(self.driver)
        except Exception as e:
            print(f"初始化失败：{e}")
            return 0
        
        current_collection_id = None
        success_count = 0
        
        try:
            for i, file_path in enumerate(files, 1):
                filename = os.path.basename(file_path)
                print(f"\n[{i}/{len(files)}] 正在处理 {filename}...")
                
                collection_id = self._process_file_with_album(
                    file_path, 
                    current_collection_id
                )
                
                if collection_id and current_collection_id is None:
                    current_collection_id = collection_id
                    print(f"\n>>> 专辑 ID 已设置为：{current_collection_id}")
                
                if collection_id:
                    success_count += 1
                    
        except KeyboardInterrupt:
            print("\n批量处理已中断。")
        finally:
            print("正在关闭驱动...")
            if self.driver:
                self.driver.quit()
        
        print(f"\n完成！成功处理 {success_count}/{len(files)} 个文件。")
        return success_count
    
    def _process_file_with_album(
        self, 
        file_path: str, 
        current_collection_id: Optional[str] = None
    ) -> Optional[str]:
        """
        处理单个文件，支持专辑匹配逻辑
        
        Args:
            file_path: 文件路径
            current_collection_id: 当前专辑 ID（如果有）
            
        Returns:
            选中曲目的 collectionId（如果有），否则返回 None
        """
        # 读取本地元数据
        local_meta = AudioFileHandler.read_full_metadata(file_path)
        if not local_meta:
            return None
        
        # 搜索
        searcher = AppleMusicSearcher(self.settings)
        print(f"正在搜索：{local_meta['title']} {local_meta['artist']} ...")
        results = searcher.search(local_meta['title'], local_meta['artist'])
        
        if not results:
            print("未找到结果。")
            return None
        
        selected = None
        
        # 匹配逻辑
        if current_collection_id:
            # 按 collectionId 过滤结果
            matches = [r for r in results if r.get('collectionId') == current_collection_id]
            
            if len(matches) == 1:
                selected = matches[0]
                print(f"自动匹配：{selected.get('trackName')} (专辑：{selected.get('collectionName')})")
            elif len(matches) > 1:
                print(f"在同一专辑中找到多个匹配项 ({current_collection_id}):")
                for i, item in enumerate(matches, 1):
                    print(f"[{i}] {item.get('trackName')} - {item.get('artistName')}")
                
                choice = input(f"请选择 (1-{len(matches)}) 或输入 0 跳过 [默认 1]: ")
                if choice.strip() == "":
                    choice = "1"
                if choice.isdigit() and 0 < int(choice) <= len(matches):
                    selected = matches[int(choice) - 1]
                else:
                    print("已跳过。")
                    return None
            else:
                print("当前专辑中未找到匹配项。显示所有结果:")
                for i, item in enumerate(results, 1):
                    print(f"[{i}] {item.get('trackName')} - {item.get('artistName')} ({item.get('collectionName')})")
                
                choice = input(f"请选择 (1-{len(results)}) 或输入 0 跳过 [默认 1]: ")
                if choice.strip() == "":
                    choice = "1"
                if choice.isdigit() and 0 < int(choice) <= len(results):
                    selected = results[int(choice) - 1]
                else:
                    return None
        else:
            # 第一个文件（或尚未设置专辑）
            print("请选择正确的歌曲/专辑:")
            for i, item in enumerate(results, 1):
                print(f"[{i}] {item.get('trackName')} - {item.get('artistName')} ({item.get('collectionName')})")
            
            choice = input(f"请选择 (1-{len(results)}) 或输入 0 跳过 [默认 1]: ")
            if choice.strip() == "":
                choice = "1"
            if choice.isdigit() and 0 < int(choice) <= len(results):
                selected = results[int(choice) - 1]
            else:
                return None
        
        if not selected:
            return None
        
        # 使用 tagger 处理剩余步骤
        if not self.tagger:
            self.tagger = AppleMusicTagger(self.settings)
            if self.driver:
                self.tagger.set_driver(self.driver)
        
        # 抓取详情
        track_url = selected.get('trackViewUrl')
        web_details = self.tagger.scraper.scrape_track_details(track_url)
        
        # 准备远程元数据
        from src.common.utils import StringUtils
        composer_str = StringUtils.join_list(web_details['composers'])
        lyricist_str = StringUtils.join_list(web_details['lyricists'])
        
        remote_meta = {
            'title': selected.get('trackName', ''),
            'artist': selected.get('artistName', ''),
            'album': selected.get('collectionName', ''),
            'composer': composer_str,
            'lyricist': lyricist_str,
            'copyright': web_details.get('copyright', '')
        }
        
        # 合并
        final_meta = self.tagger._merge_metadata(local_meta, remote_meta)
        
        # 写入
        print("正在写入元数据...", end="")
        if AudioFileHandler.write_tags(file_path, final_meta):
            print("成功。")
        else:
            print("失败。")
        
        return selected.get('collectionId')


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="Apple Music 批量标签工具")
    parser.add_argument("folder_path", help="包含音频文件的文件夹")
    args = parser.parse_args()
    
    folder = args.folder_path.strip().strip("'").strip('"')
    
    processor = BatchProcessor()
    processor.process_folder(folder)


if __name__ == "__main__":
    main()
