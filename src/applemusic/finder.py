"""
Apple Music metadata finder and tagger.
Searches Apple Music API and scrapes web pages for detailed metadata.
"""
import os
import re
import argparse
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCOM, TCOP, TEXT, ID3NoHeaderError
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from src.config import get_apple_music_config, fields


# ================= Utility Functions =================

def convert_to_song_url(url: str) -> str:
    """
    Convert album URL to song URL for detailed credits.
    
    Args:
        url: Apple Music URL (potentially album view).
        
    Returns:
        Song-specific URL if conversion successful, otherwise original URL.
    """
    from urllib.parse import urlparse, parse_qs, urlunparse
    
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if 'i' in query and '/album/' in parsed.path:
            song_id = query['i'][0]
            new_path = parsed.path.replace('/album/', '/song/')
            new_path = re.sub(r'/\d+$', f'/{song_id}', new_path)
            return urlunparse((parsed.scheme, parsed.netloc, new_path, '', '', ''))
    except Exception:
        pass
    return url


# ================= Metadata Reading =================

def get_audio_metadata_full(file_path: str) -> Optional[Dict[str, str]]:
    """
    Read comprehensive metadata from local audio file.
    
    Args:
        file_path: Path to audio file.
        
    Returns:
        Dictionary of metadata fields, or None if file doesn't exist.
    """
    import mutagen
    
    if not os.path.exists(file_path):
        print(f"错误：文件不存在 -> {file_path}")
        return None
    
    meta: Dict[str, str] = {
        'title': '', 'artist': '', 'album': '', 
        'composer': '', 'lyricist': '', 'copyright': ''
    }
    
    try:
        # Use easy interface for common tags
        audio = mutagen.File(file_path, easy=True)
        
        if audio:
            def get_first(key: str, default: str = '') -> str:
                value = audio.get(key, [default])
                return value[0] if value else default
            
            meta['title'] = get_first('title')
            meta['artist'] = get_first('artist')
            meta['album'] = get_first('album')
            meta['composer'] = get_first('composer')
            meta['copyright'] = get_first('copyright')
            meta['lyricist'] = get_first('lyricist')
        
        # Fallback to filename if no title
        if not meta['title']:
            meta['title'] = os.path.splitext(os.path.basename(file_path))[0]
            
        return meta
    except Exception as e:
        print(f"读取本地元数据出错：{e}")
        return meta


# ================= Apple Music Search =================

def search_apple_music(query_meta: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Search Apple Music iTunes API for matching tracks.
    
    Args:
        query_meta: Dictionary with 'title' and 'artist' keys.
        
    Returns:
        List of track results from API.
    """
    config = get_apple_music_config()
    
    search_term = f"{query_meta['title']} {query_meta['artist']}"
    params = {
        "term": search_term,
        "media": "music",
        "entity": "song",
        "limit": config.SEARCH_LIMIT,
        "country": config.COUNTRY
    }
    
    try:
        res = requests.get(
            config.API_BASE_URL, 
            params=params, 
            timeout=config.REQUEST_TIMEOUT
        )
        res.raise_for_status()
        return res.json().get('results', [])
    except Exception as e:
        print(f"搜索出错：{e}")
        return []


# ================= Web Scraping =================

def scrape_web_details_selenium(
    track_url: str, 
    driver: Optional[webdriver.Chrome] = None
) -> Dict[str, Any]:
    """
    Scrape detailed metadata from Apple Music web page using Selenium.
    
    Args:
        track_url: Apple Music track URL.
        driver: Optional existing Selenium driver instance.
        
    Returns:
        Dictionary with composers, lyricists, copyright, and label.
    """
    config = get_apple_music_config()
    details: Dict[str, Any] = {
        'composers': [], 
        'lyricists': [], 
        'copyright': '', 
        'label': ''
    }
    
    target_url = convert_to_song_url(track_url)
    print(f"   -> 正在分析页面详情：{target_url}")
    
    should_quit_driver = False
    if driver is None:
        should_quit_driver = True
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--mute-audio")
        
        if config.BLOCK_IMAGES:
            prefs = {"profile.managed_default_content_settings.images": 2}
            chrome_options.add_experimental_option("prefs", prefs)
        
        chrome_options.add_argument(f"user-agent={config.USER_AGENT}")
        
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), 
                options=chrome_options
            )
        except Exception as e:
            print(f"初始化 Selenium 失败：{e}")
            return details
    
    try:
        driver.get(target_url)
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "artist-metadata"))
            )
        except Exception:
            pass
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract personnel information
        metadata_divs = soup.find_all('div', class_=re.compile(r'artist-metadata'))
        for div in metadata_divs:
            name_tag = div.find(class_=re.compile(r'artist-name'))
            role_tag = div.find(class_=re.compile(r'artist-roles'))
            
            if name_tag and role_tag:
                name = name_tag.get_text(strip=True)
                role = role_tag.get_text(strip=True)
                
                if any(k in role for k in config.COMPOSER_KEYWORDS):
                    if name not in details['composers']:
                        details['composers'].append(name)
                
                if any(k in role for k in config.LYRICIST_KEYWORDS):
                    if name not in details['lyricists']:
                        details['lyricists'].append(name)
        
        # Extract copyright
        footer = soup.find('div', class_='song-copyright')
        if footer:
            details['copyright'] = footer.get_text(strip=True)
            
    except Exception as e:
        print(f"Selenium 抓取警告：{e}")
    finally:
        if should_quit_driver and driver:
            driver.quit()
    
    return details


# ================= Metadata Merging =================

def merge_metadata(
    local: Dict[str, str], 
    remote: Dict[str, str]
) -> Dict[str, str]:
    """
    Merge local and remote metadata with priority strategy.
    
    Strategy:
    1. Prefer remote values when available.
    2. Keep local values when remote is empty.
    3. Empty result only when both are empty.
    
    Args:
        local: Local metadata dictionary.
        remote: Remote metadata dictionary.
        
    Returns:
        Merged metadata dictionary.
    """
    final: Dict[str, str] = {}
    
    for key in fields.COMMON_FIELDS:
        r_val = remote.get(key, '').strip()
        l_val = local.get(key, '').strip()
        
        if r_val:
            final[key] = r_val
        elif l_val:
            final[key] = l_val
        else:
            final[key] = ''
            
    return final


# ================= Display =================

def display_diff(local: Dict[str, str], final: Dict[str, str]) -> None:
    """
    Display comparison between original and new metadata values.
    
    Args:
        local: Original metadata.
        final: New metadata to be written.
    """
    print("\n" + "="*25 + " 修改预览 " + "="*25)
    print(f"{'字段':<12} | {'原值 (Local)':<25} | {'新值 (待写入)'}")
    print("-" * 80)
    
    for key in fields.COMMON_FIELDS:
        old_val = local.get(key, '')
        new_val = final.get(key, '')
        
        # Truncate long text
        o_str = (old_val[:23] + '..') if len(old_val) > 23 else old_val
        n_str = (new_val[:35] + '..') if len(new_val) > 35 else new_val
        
        arrow = "=>" if old_val != new_val else "->"
        
        print(f"{key.capitalize():<12} | {o_str:<25} {arrow} {n_str}")
    
    print("-" * 80)
    print(f"{'Cover':<12} | {'(Original)':<25} -> [保留原封面 (不做处理)]")
    print("="*80)


# ================= Tag Writing =================

def write_tags(file_path: str, meta: Dict[str, str]) -> bool:
    """
    Write metadata tags to audio file (text only, no cover art).
    
    Args:
        file_path: Path to audio file.
        meta: Dictionary of metadata to write.
        
    Returns:
        True if successful, False otherwise.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.mp3':
            # MP3 (ID3v2.3)
            try:
                tags = ID3(file_path)
            except ID3NoHeaderError:
                tags = ID3()
            
            tags.add(TIT2(encoding=3, text=meta['title']))
            tags.add(TPE1(encoding=3, text=meta['artist']))
            tags.add(TALB(encoding=3, text=meta['album']))
            tags.add(TCOM(encoding=3, text=meta['composer'])) 
            tags.add(TEXT(encoding=3, text=meta['lyricist'])) 
            tags.add(TCOP(encoding=3, text=meta['copyright'])) 
            tags.save(file_path, v2_version=3)
        
        elif ext == '.flac':
            # FLAC
            audio = FLAC(file_path)
            audio['title'] = meta['title']
            audio['artist'] = meta['artist']
            audio['album'] = meta['album']
            audio['composer'] = meta['composer']
            audio['lyricist'] = meta['lyricist']
            audio['copyright'] = meta['copyright']
            audio.save()
        
        elif ext in ['.m4a', '.mp4']:
            # M4A/MP4
            audio = MP4(file_path)
            audio['\xa9nam'] = meta['title']
            audio['\xa9ART'] = meta['artist']
            audio['\xa9alb'] = meta['album']
            audio['\xa9wrt'] = meta['composer']
            audio['cprt'] = meta['copyright']
            
            # Write lyricist to custom atom
            if meta['lyricist']:
                try:
                    audio['----:com.apple.iTunes:LYRICIST'] = [
                        meta['lyricist'].encode('utf-8')
                    ]
                except Exception as e:
                    print(f" (M4A 作词人写入警告：{e})", end="")
            
            audio.save()
        
        else:
            print(f"暂不支持写入 {ext} 格式")
            return False
        
        return True
    except Exception as e:
        print(f"写入文件失败：{e}")
        return False


# ================= Main Program =================

def main() -> None:
    """Main entry point for Apple Music single file tagger."""
    parser = argparse.ArgumentParser(
        description="Apple Music 元数据抓取与写入工具 (保留本地值/不改封面)"
    )
    parser.add_argument("file_path", help="音频文件路径")
    args = parser.parse_args()
    
    file_path = args.file_path.strip().strip("'").strip('"')
    
    # 1. Read local metadata
    local_meta = get_audio_metadata_full(file_path)
    if not local_meta:
        return
    
    # 2. Search Apple Music
    print(f"正在搜索：{local_meta['title']} {local_meta['artist']} ...")
    results = search_apple_music(local_meta)
    
    if not results:
        print("未在 Apple Music 找到相关结果。将不进行任何修改。")
        return
    
    # 3. Display selection list
    print("\n" + "="*60)
    for i, item in enumerate(results, 1):
        print(f"[{i}] {item.get('trackName')} - {item.get('artistName')} "
              f"({item.get('collectionName')})")
    print("="*60)
    
    choice = input(f"请选择序号 (1-{len(results)}), 或输入 0 退出 [默认 1]: ")
    if choice.strip() == "":
        choice = "1"
    if not choice.isdigit() or int(choice) < 1:
        return
    
    selected = results[int(choice) - 1]
    
    # 4. Scrape detailed info
    track_url = selected.get('trackViewUrl')
    web_details = scrape_web_details_selenium(track_url)
    
    # 5. Build remote metadata object
    composer_str = "/".join(web_details['composers']) if web_details['composers'] else ""
    lyricist_str = "/".join(web_details['lyricists']) if web_details['lyricists'] else ""
    
    remote_meta: Dict[str, str] = {
        'title': selected.get('trackName', ''),
        'artist': selected.get('artistName', ''),
        'album': selected.get('collectionName', ''),
        'composer': composer_str,
        'lyricist': lyricist_str,
        'copyright': web_details['copyright']
    }
    
    # 6. Merge metadata (keep local when remote is empty)
    final_meta = merge_metadata(local_meta, remote_meta)
    
    # 7. Display comparison
    display_diff(local_meta, final_meta)
    
    # 8. User confirmation and write
    confirm = input("\n是否根据'新值'更新文件标签？[y/N]: ").lower()
    if confirm == 'y':
        print("正在写入元数据...", end="")
        if write_tags(file_path, final_meta):
            print(" [成功]")
            print(f"文件已更新：{file_path}")
        else:
            print(" [失败]")
    else:
        print("操作已取消。")


if __name__ == "__main__":
    main()
