import os
import re
import sys
import argparse
import requests
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCOM, TCOP, TEXT, ID3NoHeaderError
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
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
        print(f"读取本地元数据出错: {e}")
        # 出错时返回基础字典，避免程序崩溃
        return meta

def search_apple_music(query_meta):
    base_url = "https://itunes.apple.com/search"
    search_term = f"{query_meta['title']} {query_meta['artist']}"
    # 优先搜索香港区 (HK) 以获得中文支持
    params = {"term": search_term, "media": "music", "entity": "song", "limit": 5, "country": "HK"}
    try:
        res = requests.get(base_url, params=params, timeout=10)
        res.raise_for_status()
        return res.json().get('results', [])
    except Exception as e:
        print(f"搜索出错: {e}")
        return []

def scrape_web_details_selenium(track_url, driver=None):
    details = {'composers': [], 'lyricists': [], 'copyright': '', 'label': ''}
    target_url = convert_to_song_url(track_url)
    print(f"   -> 正在分析页面详情: {target_url}")
    
    should_quit_driver = False
    if driver is None:
        should_quit_driver = True
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--mute-audio")
        # 禁用图片加载以加快速度
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        except Exception as e:
            print(f"初始化 Selenium 失败: {e}")
            return details

    try:
        driver.get(target_url)
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "artist-metadata")))
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
        print(f"Selenium 抓取警告: {e}")
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
    print(f"{'字段':<12} | {'原值 (Local)':<25} | {'新值 (Wait to Write)'}")
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
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        # === MP3 (ID3v2.3) ===
        if ext == '.mp3':
            try:
                tags = ID3(file_path)
            except ID3NoHeaderError:
                tags = ID3()
            
            # 使用 v2.3 编码 (UTF-16 usually)
            tags.add(TIT2(encoding=3, text=meta['title']))
            tags.add(TPE1(encoding=3, text=meta['artist']))
            tags.add(TALB(encoding=3, text=meta['album']))
            tags.add(TCOM(encoding=3, text=meta['composer'])) 
            tags.add(TEXT(encoding=3, text=meta['lyricist'])) 
            tags.add(TCOP(encoding=3, text=meta['copyright'])) 
            tags.save(file_path, v2_version=3)

        # === FLAC ===
        elif ext == '.flac':
            audio = FLAC(file_path)
            audio['title'] = meta['title']
            audio['artist'] = meta['artist']
            audio['album'] = meta['album']
            audio['composer'] = meta['composer']
            audio['lyricist'] = meta['lyricist']
            audio['copyright'] = meta['copyright']
            audio.save()

        # === M4A/MP4 (核心修改) ===
        elif ext in ['.m4a', '.mp4']:
            audio = MP4(file_path)
            audio['\xa9nam'] = meta['title']
            audio['\xa9ART'] = meta['artist']
            audio['\xa9alb'] = meta['album']
            audio['\xa9wrt'] = meta['composer']
            audio['cprt'] = meta['copyright']
            
            # 写入作词人到自定义原子 (兼容 Mp3tag)
            if meta['lyricist']:
                try:
                    # Mutagen 要求自定义 tag 值为 bytes 列表
                    audio['----:com.apple.iTunes:LYRICIST'] = [meta['lyricist'].encode('utf-8')]
                except Exception as e:
                    print(f" (M4A作词人写入警告: {e})", end="")

            audio.save()

        else:
            print(f"暂不支持写入 {ext} 格式")
            return False

        return True
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False

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
