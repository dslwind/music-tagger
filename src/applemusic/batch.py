"""
Apple Music batch tagging utility.
Processes multiple audio files in a folder with album-aware matching.
"""
import os
import argparse
from typing import Optional, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from src.applemusic.finder import (
    get_audio_metadata_full,
    search_apple_music,
    scrape_web_details_selenium,
    merge_metadata,
    write_tags,
)
from src.config import get_apple_music_config, formats


def init_driver() -> Optional[webdriver.Chrome]:
    """
    Initialize shared Selenium driver with optimized settings.
    
    Returns:
        Chrome WebDriver instance or None if initialization fails.
    """
    config = get_apple_music_config()
    
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
        return driver
    except Exception as e:
        print(f"初始化 Selenium 驱动失败：{e}")
        return None


def select_from_results(
    results: list,
    prompt: str = "请选择",
    auto_select_first: bool = False
) -> Optional[dict]:
    """
    Display results and get user selection.
    
    Args:
        results: List of search result items.
        prompt: Custom prompt message.
        auto_select_first: If True and only one result, auto-select it.
        
    Returns:
        Selected item dictionary or None if skipped/cancelled.
    """
    if not results:
        return None
    
    if auto_select_first and len(results) == 1:
        return results[0]
    
    print(f"{prompt}:")
    for i, item in enumerate(results, 1):
        print(f"[{i}] {item.get('trackName')} - {item.get('artistName')} "
              f"({item.get('collectionName')})")
    
    choice = input(f"请选择 (1-{len(results)}) 或输入 0 跳过 [默认 1]: ")
    if choice.strip() == "":
        choice = "1"
    
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(results):
        if choice.isdigit() and int(choice) == 0:
            print("已跳过。")
        else:
            print("无效选择。")
        return None
    
    return results[int(choice) - 1]


def process_file(
    file_path: str, 
    driver: webdriver.Chrome,
    current_collection_id: Optional[str] = None
) -> Optional[str]:
    """
    Process single audio file for metadata tagging.
    
    Args:
        file_path: Path to audio file.
        driver: Selenium WebDriver instance.
        current_collection_id: Optional album ID for matching.
        
    Returns:
        Collection ID of selected track, or None if processing failed.
    """
    print(f"\n正在处理：{os.path.basename(file_path)}")
    
    # 1. Read local metadata
    local_meta = get_audio_metadata_full(file_path)
    if not local_meta:
        return None
    
    # 2. Search Apple Music
    print(f"正在搜索：{local_meta['title']} {local_meta['artist']} ...")
    results = search_apple_music(local_meta)
    
    if not results:
        print("未找到结果。")
        return None
    
    selected = None
    
    # 3. Matching logic
    if current_collection_id:
        # Filter by collection ID
        matches = [r for r in results if r.get('collectionId') == current_collection_id]
        
        if len(matches) == 1:
            selected = matches[0]
            print(f"自动匹配：{selected.get('trackName')} "
                  f"(专辑：{selected.get('collectionName')})")
        elif len(matches) > 1:
            print(f"在同一专辑中找到多个匹配项 ({current_collection_id}):")
            selected = select_from_results(matches, "请选择")
        else:
            print("当前专辑中未找到匹配项。显示所有结果:")
            selected = select_from_results(results, "请选择")
    else:
        # First file or no album set yet
        selected = select_from_results(results, "请选择正确的歌曲/专辑")
    
    if not selected:
        return None
    
    # 4. Scrape detailed info
    track_url = selected.get('trackViewUrl')
    web_details = scrape_web_details_selenium(track_url, driver=driver)
    
    # 5. Prepare remote metadata
    composer_str = "/".join(web_details['composers']) if web_details['composers'] else ""
    lyricist_str = "/".join(web_details['lyricists']) if web_details['lyricists'] else ""
    
    remote_meta = {
        'title': selected.get('trackName', ''),
        'artist': selected.get('artistName', ''),
        'album': selected.get('collectionName', ''),
        'composer': composer_str,
        'lyricist': lyricist_str,
        'copyright': web_details['copyright']
    }
    
    # 6. Merge metadata
    final_meta = merge_metadata(local_meta, remote_meta)
    
    # 7. Write tags
    print("正在写入元数据...", end="")
    if write_tags(file_path, final_meta):
        print("成功。")
    else:
        print("失败。")
    
    return selected.get('collectionId')


def main() -> None:
    """Main entry point for Apple Music batch tagger."""
    parser = argparse.ArgumentParser(description="Apple Music 批量标签工具")
    parser.add_argument("folder_path", help="包含音频文件的文件夹")
    args = parser.parse_args()
    
    folder = args.folder_path.strip().strip("'").strip('"')
    if not os.path.exists(folder):
        print("文件夹未找到。")
        return
    
    # Find supported audio files
    files = [
        f for f in os.listdir(folder) 
        if f.lower().endswith(formats.APPLE_MUSIC)
    ]
    files.sort()
    
    if not files:
        print("未找到支持的音频文件。")
        return
    
    print(f"找到 {len(files)} 个文件。正在初始化 Selenium...")
    driver = init_driver()
    if not driver:
        return
    
    current_collection_id: Optional[str] = None
    
    try:
        for i, filename in enumerate(files):
            file_path = os.path.join(folder, filename)
            print(f"\n[{i+1}/{len(files)}] 正在处理 {filename}...")
            
            result_collection_id = process_file(
                file_path, 
                driver, 
                current_collection_id
            )
            
            if result_collection_id and current_collection_id is None:
                current_collection_id = result_collection_id
                print(f"\n>>> 专辑 ID 已设置为：{current_collection_id}")
                
    except KeyboardInterrupt:
        print("\n批量处理已中断。")
    finally:
        print("正在关闭驱动...")
        driver.quit()


if __name__ == "__main__":
    main()
