"""Apple Music 元数据抓取器"""

import os
import re
import argparse
from typing import Optional, Dict, List, Any
from bs4 import BeautifulSoup
import requests

from src.common.audio import AudioFileHandler
from src.common.utils import URLUtils, StringUtils
from src.config import Settings
from src.drivers.browser import BrowserDriver, DriverFactory
from src.metadata.models import AudioMetadata


class AppleMusicSearcher:
    """Apple Music 搜索器"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.get_default()
        self.base_url = "https://itunes.apple.com/search"
    
    def search(self, title: str, artist: str = "", limit: int = None) -> List[Dict[str, Any]]:
        """
        搜索 Apple Music
        
        Args:
            title: 歌曲标题
            artist: 艺术家名称
            limit: 返回结果数量限制
            
        Returns:
            搜索结果列表
        """
        if limit is None:
            limit = self.settings.apple_music_search_limit
        
        search_term = f"{title} {artist}".strip()
        params = {
            "term": search_term,
            "media": "music",
            "entity": "song",
            "limit": limit,
            "country": self.settings.apple_music_country
        }
        
        try:
            res = requests.get(self.base_url, params=params, timeout=10)
            res.raise_for_status()
            return res.json().get('results', [])
        except Exception as e:
            print(f"搜索出错：{e}")
            return []


class AppleMusicScraper:
    """Apple Music 网页信息抓取器"""
    
    def __init__(self, driver: Optional[BrowserDriver] = None):
        self._driver = driver
        self._owns_driver = False
    
    def _ensure_driver(self):
        """确保有可用的驱动"""
        if self._driver is None:
            self._driver = DriverFactory.create_default()
            self._owns_driver = True
    
    def scrape_track_details(self, track_url: str) -> Dict[str, Any]:
        """
        抓取歌曲详情页面信息
        
        Args:
            track_url: Apple Music 歌曲 URL
            
        Returns:
            包含作曲、作词、版权等信息的字典
        """
        details = {'composers': [], 'lyricists': [], 'copyright': '', 'label': ''}
        target_url = URLUtils.convert_to_song_url(track_url)
        print(f"   -> 正在分析页面详情：{target_url}")
        
        should_quit_driver = False
        if self._driver is None:
            self._ensure_driver()
            should_quit_driver = True
        
        try:
            self._driver.get(target_url)
            
            # 等待页面加载（简单等待）
            import time
            time.sleep(2)
            
            soup = BeautifulSoup(self._driver.page_source, 'html.parser')
            
            # 提取人员信息
            metadata_divs = soup.find_all('div', class_=re.compile(r'artist-metadata'))
            for div in metadata_divs:
                name_tag = div.find(class_=re.compile(r'artist-name'))
                role_tag = div.find(class_=re.compile(r'artist-roles'))
                if name_tag and role_tag:
                    name = name_tag.get_text(strip=True)
                    role = role_tag.get_text(strip=True)
                    
                    if any(k in role for k in ['作曲', '作曲家', '音樂創作人', 'Composer', 'Written By', 'Music']):
                        if name not in details['composers']:
                            details['composers'].append(name)
                    
                    if any(k in role for k in ['填詞', '作词', '作詞', '音樂創作人', 'Lyricist', 'Lyrics']):
                        if name not in details['lyricists']:
                            details['lyricists'].append(name)
            
            # 提取版权信息
            footer = soup.find('div', class_='song-copyright')
            if footer:
                details['copyright'] = footer.get_text(strip=True)
                
        except Exception as e:
            print(f"Selenium 抓取警告：{e}")
        finally:
            if should_quit_driver and self._driver:
                self._driver.quit()
                self._driver = None
                self._owns_driver = False
        
        return details


class AppleMusicTagger:
    """Apple Music 标签处理器"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.get_default()
        self.searcher = AppleMusicSearcher(self.settings)
        self.scraper: Optional[AppleMusicScraper] = None
    
    def set_driver(self, driver: BrowserDriver):
        """设置共享的浏览器驱动"""
        self.scraper = AppleMusicScraper(driver)
    
    def process_file(self, file_path: str, auto_confirm: bool = False) -> bool:
        """
        处理单个文件
        
        Args:
            file_path: 音频文件路径
            auto_confirm: 是否自动确认写入
            
        Returns:
            是否成功处理
        """
        # 1. 读取本地元数据
        local_meta = AudioFileHandler.read_full_metadata(file_path)
        if not local_meta:
            return False
        
        # 2. 搜索
        print(f"正在搜索：{local_meta['title']} {local_meta['artist']} ...")
        results = self.searcher.search(local_meta['title'], local_meta['artist'])
        
        if not results:
            print("未在 Apple Music 找到相关结果。将不进行任何修改。")
            return False
        
        # 3. 选择结果
        print("\n" + "="*60)
        for i, item in enumerate(results, 1):
            print(f"[{i}] {item.get('trackName')} - {item.get('artistName')} ({item.get('collectionName')})")
        print("="*60)
        
        if not auto_confirm:
            choice = input(f"请选择序号 (1-{len(results)}), 或输入 0 退出 [默认 1]: ")
            if choice.strip() == "":
                choice = "1"
            if not choice.isdigit() or int(choice) < 1:
                return False
            selected = results[int(choice) - 1]
        else:
            selected = results[0]
        
        # 4. 抓取详情
        track_url = selected.get('trackViewUrl')
        if not self.scraper:
            self.scraper = AppleMusicScraper()
        web_details = self.scraper.scrape_track_details(track_url)
        
        # 5. 构建远程元数据
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
        
        # 6. 合并元数据
        final_meta = self._merge_metadata(local_meta, remote_meta)
        
        # 7. 展示对比
        self._display_diff(local_meta, final_meta)
        
        # 8. 确认并写入
        if not auto_confirm:
            confirm = input("\n是否根据'新值'更新文件标签？[y/N]: ").lower()
            if confirm != 'y':
                print("操作已取消。")
                return False
        
        print("正在写入元数据...", end="")
        if AudioFileHandler.write_tags(file_path, final_meta):
            print(" [成功]")
            print(f"文件已更新：{file_path}")
            return True
        else:
            print(" [失败]")
            return False
    
    def _merge_metadata(self, local: Dict[str, str], remote: Dict[str, str]) -> Dict[str, str]:
        """合并本地和远程元数据"""
        final = {}
        keys = ['title', 'artist', 'album', 'composer', 'lyricist', 'copyright']
        
        for key in keys:
            r_val = remote.get(key, '').strip()
            l_val = local.get(key, '').strip()
            
            if r_val:
                final[key] = r_val
            elif l_val:
                final[key] = l_val
            else:
                final[key] = ''
        
        return final
    
    def _display_diff(self, local: Dict[str, str], final: Dict[str, str]):
        """展示变更对比"""
        print("\n" + "="*25 + " 修改预览 " + "="*25)
        print(f"{'字段':<12} | {'原值 (Local)':<25} | {'新值 (待写入)'}")
        print("-" * 80)
        
        keys = ['title', 'artist', 'album', 'composer', 'lyricist', 'copyright']
        for key in keys:
            old_val = local.get(key, '')
            new_val = final.get(key, '')
            
            o_str = StringUtils.truncate(old_val, 25)
            n_str = StringUtils.truncate(new_val, 35)
            
            arrow = "=>" if old_val != new_val else "->"
            print(f"{key.capitalize():<12} | {o_str:<25} {arrow} {n_str}")
        
        print("-" * 80)
        print(f"{'Cover':<12} | {'(Original)':<25} -> [保留原封面 (不做处理)]")
        print("="*80)


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="Apple Music 元数据抓取与写入工具")
    parser.add_argument("file_path", help="音频文件路径")
    parser.add_argument("--auto", action="store_true", help="自动确认，不询问用户")
    args = parser.parse_args()
    
    file_path = args.file_path.strip().strip("'").strip('"')
    
    tagger = AppleMusicTagger()
    tagger.process_file(file_path, auto_confirm=args.auto)


if __name__ == "__main__":
    main()
