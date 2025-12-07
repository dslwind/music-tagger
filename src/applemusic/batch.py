import os
import sys
import argparse
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Import from the finder module
from src.applemusic.finder import (
    get_audio_metadata_full,
    search_apple_music,
    scrape_web_details_selenium,
    merge_metadata,
    write_tags,
    display_diff
)

def init_driver():
    """Initialize a shared Selenium driver."""
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
        print(f"Failed to initialize Selenium driver: {e}")
        return None

def process_file(file_path, driver, current_collection_id):
    """
    Process a single file.
    Returns: The collectionId of the selected track (if any), or None.
    """
    print(f"\nProcessing: {os.path.basename(file_path)}")
    
    # 1. Read local metadata
    local_meta = get_audio_metadata_full(file_path)
    if not local_meta:
        return None

    # 2. Search
    print(f"Searching: {local_meta['title']} {local_meta['artist']} ...")
    results = search_apple_music(local_meta)
    
    if not results:
        print("No results found.")
        return None

    selected = None
    
    # 3. Match Logic
    if current_collection_id:
        # Filter results by collectionId
        matches = [r for r in results if r.get('collectionId') == current_collection_id]
        
        if len(matches) == 1:
            selected = matches[0]
            print(f"Auto-matched: {selected.get('trackName')} (Album: {selected.get('collectionName')})")
        elif len(matches) > 1:
            print(f"Multiple matches found in the same album ({current_collection_id}):")
            for i, item in enumerate(matches, 1):
                print(f"[{i}] {item.get('trackName')} - {item.get('artistName')}")
            
            choice = input(f"Select (1-{len(matches)}) or 0 to skip [Default: 1]: ")
            if choice.strip() == "": choice = "1"
            if choice.isdigit() and int(choice) > 0 and int(choice) <= len(matches):
                selected = matches[int(choice) - 1]
            else:
                print("Skipped.")
                return None
        else:
            print("No match found in the current album. Showing all results:")
            # Fallback to showing all results
            for i, item in enumerate(results, 1):
                print(f"[{i}] {item.get('trackName')} - {item.get('artistName')} ({item.get('collectionName')})")
            
            choice = input(f"Select (1-{len(results)}) or 0 to skip [Default: 1]: ")
            if choice.strip() == "": choice = "1"
            if choice.isdigit() and int(choice) > 0 and int(choice) <= len(results):
                selected = results[int(choice) - 1]
            else:
                return None
    else:
        # First file (or no album set yet)
        print("Please select the correct track/album:")
        for i, item in enumerate(results, 1):
            print(f"[{i}] {item.get('trackName')} - {item.get('artistName')} ({item.get('collectionName')})")
        
        choice = input(f"Select (1-{len(results)}) or 0 to skip [Default: 1]: ")
        if choice.strip() == "": choice = "1"
        if choice.isdigit() and int(choice) > 0 and int(choice) <= len(results):
            selected = results[int(choice) - 1]
        else:
            return None

    if not selected:
        return None

    # 4. Scrape details
    track_url = selected.get('trackViewUrl')
    web_details = scrape_web_details_selenium(track_url, driver=driver)
    
    # 5. Prepare remote meta
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

    # 6. Merge
    final_meta = merge_metadata(local_meta, remote_meta)
    
    # 7. Write
    print("Writing metadata...")
    if write_tags(file_path, final_meta):
        print("Success.")
    else:
        print("Failed.")
        
    return selected.get('collectionId')

def main():
    parser = argparse.ArgumentParser(description="Batch Apple Music Tagger")
    parser.add_argument("folder_path", help="Folder containing audio files")
    args = parser.parse_args()
    
    folder = args.folder_path.strip().strip("'").strip('"')
    if not os.path.exists(folder):
        print("Folder not found.")
        return

    files = [f for f in os.listdir(folder) if f.lower().endswith(('.mp3', '.flac', '.m4a', '.mp4'))]
    files.sort()
    
    if not files:
        print("No supported audio files found.")
        return
        
    print(f"Found {len(files)} files. Initializing Selenium...")
    driver = init_driver()
    if not driver:
        return

    current_collection_id = None
    
    try:
        for i, filename in enumerate(files):
            file_path = os.path.join(folder, filename)
            print(f"\n[{i+1}/{len(files)}] Processing {filename}...")
            
            # If we haven't set an album yet, this file will determine it.
            # If we have, we try to match against it.
            
            result_collection_id = process_file(file_path, driver, current_collection_id)
            
            if result_collection_id and current_collection_id is None:
                current_collection_id = result_collection_id
                print(f"\n>>> Album set to ID: {current_collection_id}")
                
    except KeyboardInterrupt:
        print("\nBatch processing interrupted.")
    finally:
        print("Closing driver...")
        driver.quit()

if __name__ == "__main__":
    main()
