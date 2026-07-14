import os
import re
import sys
import argparse
import requests
import mutagen
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlunparse

# --- Selenium 依赖 ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from src.utils import get_logger, get_config
from src.common import TagWriterFactory

logger = get_logger(__name__)

# ================= 工具函数 =================

def convert_to_song_url(url):
    """确保链接是单曲视图，以便获取详细 Credit"""
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if 'i' in query and '/album/' in parsed.path:
            song_id = query['i'][0]
            new_path = parsed.path.replace('/album/', '/song/')
            new_path = re.sub(r'/\d+$', f'/{song_id}', new_path)
            return urlunparse((parsed.scheme, parsed.netloc, new_path, '', '', ''))
    except:
        pass
    return url

# ================= 核心逻辑: 读取/搜索/抓取 =================

def get_audio_metadata_full(file_path):
    """
    读取本地音频文件的详细元数据，用于后续的'保留原值'逻辑
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在 -> {file_path}")
        print(f"错误: 文件不存在 -> {file_path}")
        return None
    
    meta = {
        'title': '', 'artist': '', 'album': '', 
        'composer': '', 'lyricist': '', 'copyright': ''
    }

    try:
        # 使用 easy=True 接口读取通用标签
        audio = mutagen.File(file_path, easy=True)
        
        if audio:
            meta['title'] = audio.get('title', [''])[0]
            meta['artist'] = audio.get('artist', [''])[0]
            meta['album'] = audio.get('album', [''])[0]
            meta['composer'] = audio.get('composer', [''])[0]
            meta['copyright'] = audio.get('copyright', [''])[0]
            # EasyID3 通常没有统一的 lyricist 键，这里暂且留空或后续处理
            # 某些格式可能支持 'lyricist'
            meta['lyricist'] = audio.get('lyricist', [''])[0]

        # 如果没有标题，回退到文件名
        if not meta['title']:
            meta['title'] = os.path.splitext(os.path.basename(file_path))[0]
            
        return meta
    except Exception as e:
        logger.error(f"读取本地元数据出错: {e}")
        # 出错时返回基础字典，避免程序崩溃
        return meta

def search_apple_music(query_meta):
    config = get_config()
    api_url = config.get('apple_music', 'api_url', default='https://itunes.apple.com/search')
    country = config.get('apple_music', 'country', default='HK')
    limit = config.get('apple_music', 'search_limit', default=5)

    search_term = f"{query_meta['title']} {query_meta['artist']}"
    params = {"term": search_term, "media": "music", "entity": "song", "limit": limit, "country": country}
    try:
        res = requests.get(api_url, params=params, timeout=10)
        res.raise_for_status()
        return res.json().get('results', [])
    except Exception as e:
        logger.error(f"搜索出错: {e}")
        return []

def scrape_web_details_selenium(track_url, driver=None):
    config = get_config()
    details = {'composers': [], 'lyricists': [], 'copyright': '', 'label': ''}
    target_url = convert_to_song_url(track_url)
    print(f"   -> 正在分析页面详情: {target_url}")

    should_quit_driver = False
    if driver is None:
        should_quit_driver = True
        chrome_options = Options()

        # 从配置读取 Selenium 选项
        if config.get('selenium', 'headless', default=True):
            chrome_options.add_argument("--headless")
        if config.get('selenium', 'disable_gpu', default=True):
            chrome_options.add_argument("--disable-gpu")
        if config.get('selenium', 'mute_audio', default=True):
            chrome_options.add_argument("--mute-audio")

        if config.get('selenium', 'disable_images', default=True):
            prefs = {"profile.managed_default_content_settings.images": 2}
            chrome_options.add_experimental_option("prefs", prefs)

        user_agent = config.get('selenium', 'user_agent')
        if user_agent:
            chrome_options.add_argument(f"user-agent={user_agent}")

        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        except Exception as e:
            logger.error(f"初始化 Selenium 失败: {e}")
            return details

    page_timeout = config.get('selenium', 'page_timeout', default=10)

    try:
        driver.get(target_url)
        try:
            WebDriverWait(driver, page_timeout).until(EC.presence_of_element_located((By.CLASS_NAME, "artist-metadata")))
        except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 提取人员
        metadata_divs = soup.find_all('div', class_=re.compile(r'artist-metadata'))
        for div in metadata_divs:
            name_tag = div.find(class_=re.compile(r'artist-name'))
            role_tag = div.find(class_=re.compile(r'artist-roles'))
            if name_tag and role_tag:
                name = name_tag.get_text(strip=True)
                role = role_tag.get_text(strip=True)
                
                if any(k in role for k in ['作曲', '作曲家', '音樂創作人', 'Composer', 'Written By', 'Music']):
                    if name not in details['composers']: details['composers'].append(name)
                
                if any(k in role for k in ['填詞', '作词', '作詞', '音樂創作人', 'Lyricist', 'Lyrics']):
                    if name not in details['lyricists']: details['lyricists'].append(name)

        # 提取版权
        footer = soup.find('div', class_='song-copyright')
        if footer: details['copyright'] = footer.get_text(strip=True)
            
    except Exception as e:
        logger.warning(f"Selenium 抓取警告: {e}")
    finally:
        if should_quit_driver and driver:
            driver.quit()
    return details

# ================= 核心逻辑: 数据合并与写入 =================

def merge_metadata(local, remote):
    """
    策略：
    1. 如果 Remote 有值，优先使用 Remote (更新)。
    2. 如果 Remote 为空，但 Local 有值，保留 Local (不覆盖为空)。
    3. 只有当 Remote 和 Local 都为空时，结果才为空。
    """
    final = {}
    keys = ['title', 'artist', 'album', 'composer', 'lyricist', 'copyright']
    
    for key in keys:
        r_val = remote.get(key, '').strip()
        l_val = local.get(key, '').strip()
        
        if r_val:
            final[key] = r_val
        elif l_val:
            final[key] = l_val
            # 调试用，如果想看哪些字段保留了原值
            # print(f"[保留原值] {key}: {l_val}")
        else:
            final[key] = ''
            
    return final

def display_diff(local, final):
    """展示变更对比"""
    print("\n" + "="*25 + " 修改预览 " + "="*25)
    print(f"{'字段':<12} | {'原值 (Local)':<25} | {'新值 (待写入)'}")
    print("-" * 80)
    
    keys = ['title', 'artist', 'album', 'composer', 'lyricist', 'copyright']
    for key in keys:
        old_val = local.get(key, '')
        new_val = final.get(key, '')
        
        # 格式化过长文本
        o_str = (old_val[:23] + '..') if len(old_val) > 23 else old_val
        n_str = (new_val[:35] + '..') if len(new_val) > 35 else new_val
        
        arrow = "->"
        if old_val != new_val:
            arrow = "=>" # 变动高亮
            
        print(f"{key.capitalize():<12} | {o_str:<25} {arrow} {n_str}")
    
    print("-" * 80)
    print(f"{'Cover':<12} | {'(Original)':<25} -> [保留原封面 (不做处理)]")
    print("="*80)

def write_tags(file_path, meta):
    """写入标签 (仅写入文本，不处理封面)"""
    return TagWriterFactory.write_tags(file_path, meta)

# ================= 主程序 =================

def main():
    parser = argparse.ArgumentParser(description="Apple Music 元数据抓取与写入工具 (保留本地值/不改封面)")
    parser.add_argument("file_path", help="音频文件路径")
    args = parser.parse_args()
    file_path = args.file_path.strip().strip("'").strip('"')

    # 1. 详细读取本地元数据
    local_meta = get_audio_metadata_full(file_path)
    if not local_meta: return

    # 2. 搜索
    print(f"正在搜索: {local_meta['title']} {local_meta['artist']} ...")
    results = search_apple_music(local_meta)
    
    if not results:
        print("未在 Apple Music 找到相关结果。将不进行任何修改。")
        return

    # 3. 选择列表
    print("\n" + "="*60)
    for i, item in enumerate(results, 1):
        print(f"[{i}] {item.get('trackName')} - {item.get('artistName')} ({item.get('collectionName')})")
    print("="*60)

    choice = input(f"请选择序号 (1-{len(results)}), 或输入 0 退出 [默认 1]: ")
    if choice.strip() == "": choice = "1"
    if not choice.isdigit() or int(choice) < 1: return
    selected = results[int(choice) - 1]

    # 4. 抓取详情
    track_url = selected.get('trackViewUrl')
    web_details = scrape_web_details_selenium(track_url)
    
    # 5. 构建远程数据对象 (Remote)
    composer_str = "/".join(web_details['composers']) if web_details['composers'] else ""
    lyricist_str = "/".join(web_details['lyricists']) if web_details['lyricists'] else ""
    
    remote_meta = {
        'title': selected.get('trackName'),
        'artist': selected.get('artistName'),
        'album': selected.get('collectionName'),
        'composer': composer_str,
        'lyricist': lyricist_str,
        'copyright': web_details['copyright']
    }

    # 6. 数据合并 (关键逻辑：Remote 为空时保留 Local)
    final_meta = merge_metadata(local_meta, remote_meta)

    # 7. 展示对比
    display_diff(local_meta, final_meta)

    # 8. 用户确认与写入
    confirm = input("\n是否根据'新值'更新文件标签? [y/N]: ").lower()
    if confirm == 'y':
        print("正在写入元数据...", end="")
        if write_tags(file_path, final_meta):
            print(" [成功]")
            print(f"文件已更新: {file_path}")
        else:
            print(" [失败]")
    else:
        print("操作已取消。")

if __name__ == "__main__":
    main()
