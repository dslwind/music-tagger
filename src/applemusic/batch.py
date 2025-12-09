import os
import sys
import argparse
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 从 finder 模块导入
from src.applemusic.finder import (
    get_audio_metadata_full,
    search_apple_music,
    scrape_web_details_selenium,
    merge_metadata,
    write_tags,
    display_diff
)

def init_driver():
    """初始化共享的 Selenium 驱动。"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--mute-audio")
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        return driver
    except Exception as e:
        print(f"初始化 Selenium 驱动失败: {e}")
        return None

def process_file(file_path, driver, current_collection_id):
    """
    处理单个文件。
    返回: 选中曲目的 collectionId (如果有)，否则返回 None。
    """
    print(f"\n正在处理: {os.path.basename(file_path)}")
    
    # 1. 读取本地元数据
    local_meta = get_audio_metadata_full(file_path)
    if not local_meta:
        return None

    # 2. 搜索
    print(f"正在搜索: {local_meta['title']} {local_meta['artist']} ...")
    results = search_apple_music(local_meta)
    
    if not results:
        print("未找到结果。")
        return None

    selected = None
    
    # 3. 匹配逻辑
    if current_collection_id:
        # 按 collectionId 过滤结果
        matches = [r for r in results if r.get('collectionId') == current_collection_id]
        
        if len(matches) == 1:
            selected = matches[0]
            print(f"自动匹配: {selected.get('trackName')} (专辑: {selected.get('collectionName')})")
        elif len(matches) > 1:
            print(f"在同一专辑中找到多个匹配项 ({current_collection_id}):")
            for i, item in enumerate(matches, 1):
                print(f"[{i}] {item.get('trackName')} - {item.get('artistName')}")
            
            choice = input(f"请选择 (1-{len(matches)}) 或输入 0 跳过 [默认 1]: ")
            if choice.strip() == "": choice = "1"
            if choice.isdigit() and int(choice) > 0 and int(choice) <= len(matches):
                selected = matches[int(choice) - 1]
            else:
                print("已跳过。")
                return None
        else:
            print("当前专辑中未找到匹配项。显示所有结果:")
            # 回退到显示所有结果
            for i, item in enumerate(results, 1):
                print(f"[{i}] {item.get('trackName')} - {item.get('artistName')} ({item.get('collectionName')})")
            
            choice = input(f"请选择 (1-{len(results)}) 或输入 0 跳过 [默认 1]: ")
            if choice.strip() == "": choice = "1"
            if choice.isdigit() and int(choice) > 0 and int(choice) <= len(results):
                selected = results[int(choice) - 1]
            else:
                return None
    else:
        # 第一个文件 (或尚未设置专辑)
        print("请选择正确的歌曲/专辑:")
        for i, item in enumerate(results, 1):
            print(f"[{i}] {item.get('trackName')} - {item.get('artistName')} ({item.get('collectionName')})")
        
        choice = input(f"请选择 (1-{len(results)}) 或输入 0 跳过 [默认 1]: ")
        if choice.strip() == "": choice = "1"
        if choice.isdigit() and int(choice) > 0 and int(choice) <= len(results):
            selected = results[int(choice) - 1]
        else:
            return None

    if not selected:
        return None

    # 4. 抓取详情
    track_url = selected.get('trackViewUrl')
    web_details = scrape_web_details_selenium(track_url, driver=driver)
    
    # 5. 准备远程元数据
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

    # 6. 合并
    final_meta = merge_metadata(local_meta, remote_meta)
    
    # 7. 写入
    print("正在写入元数据...")
    if write_tags(file_path, final_meta):
        print("成功。")
    else:
        print("失败。")
        
    return selected.get('collectionId')

def main():
    parser = argparse.ArgumentParser(description="Apple Music 批量标签工具")
    parser.add_argument("folder_path", help="包含音频文件的文件夹")
    args = parser.parse_args()
    
    folder = args.folder_path.strip().strip("'").strip('"')
    if not os.path.exists(folder):
        print("文件夹未找到。")
        return

    files = [f for f in os.listdir(folder) if f.lower().endswith(('.mp3', '.flac', '.m4a', '.mp4'))]
    files.sort()
    
    if not files:
        print("未找到支持的音频文件。")
        return
        
    print(f"找到 {len(files)} 个文件。正在初始化 Selenium...")
    driver = init_driver()
    if not driver:
        return

    current_collection_id = None
    
    try:
        for i, filename in enumerate(files):
            file_path = os.path.join(folder, filename)
            print(f"\n[{i+1}/{len(files)}] 正在处理 {filename}...")
            
            # 如果尚未设置专辑，此文件将决定专辑。
            # 如果已设置，我们尝试匹配它。
            
            result_collection_id = process_file(file_path, driver, current_collection_id)
            
            if result_collection_id and current_collection_id is None:
                current_collection_id = result_collection_id
                print(f"\n>>> 专辑 ID 已设置为: {current_collection_id}")
                
    except KeyboardInterrupt:
        print("\n批量处理已中断。")
    finally:
        print("正在关闭驱动...")
        driver.quit()

if __name__ == "__main__":
    main()
