import argparse
import os
from src.common.audio import AudioFileHandler
from src.musicbrainz.client import MusicBrainzClient

def main():
    parser = argparse.ArgumentParser(description="Music Tagger CLI")
    parser.add_argument("path", help="Path to the music file")
    args = parser.parse_args()

    filepath = args.path
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    # 1. Load File
    try:
        handler = AudioFileHandler(filepath)
        current_tags = handler.get_tags()
        print(f"Current Tags: {current_tags}")
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    # 2. Search MusicBrainz
    mb_client = MusicBrainzClient()
    print("\nSearching MusicBrainz...")
    
    # Use existing tags for search if available, otherwise ask user? 
    # For now, let's assume we use the filename if tags are empty, or just use what we have.
    title = current_tags.get('title')
    if not title:
        # Fallback to filename without extension
        title = os.path.splitext(os.path.basename(filepath))[0]
        print(f"No title tag found. Using filename: {title}")

    results = mb_client.search_recording(title, artist=current_tags.get('artist'), album=current_tags.get('album'))

    if not results:
        print("No results found on MusicBrainz.")
        return

    # 3. Display Results and Ask User
    print("\nFound matches:")
    for i, recording in enumerate(results):
        # Extract some useful info to show
        track_title = recording.get('title', 'Unknown')
        artist_credit = recording.get('artist-credit', [])
        artist_name = artist_credit[0]['artist']['name'] if artist_credit else "Unknown"
        releases = recording.get('release-list', [])
        album_name = releases[0]['title'] if releases else "Unknown"
        
        print(f"{i+1}. {track_title} - {artist_name} (Album: {album_name})")

    while True:
        choice = input("\nSelect a match (number) to preview, or 'q' to quit: ")
        if choice.lower() == 'q':
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(results):
                selected = results[index]
                
                # Prepare new tags
                new_tags = {
                    'title': selected.get('title'),
                    'musicbrainz_trackid': selected.get('id'),
                }
                
                # Get artist info
                artist_credit = selected.get('artist-credit', [])
                if artist_credit:
                     new_tags['artist'] = artist_credit[0]['artist']['name']
                     if 'artist' in artist_credit[0]:
                         new_tags['musicbrainz_artistid'] = artist_credit[0]['artist']['id']

                # Get album info
                releases = selected.get('release-list', [])
                if releases:
                    release = releases[0]
                    new_tags['album'] = release.get('title')
                    new_tags['date'] = release.get('date')
                    new_tags['musicbrainz_albumid'] = release.get('id')
                    
                    # Get Album Artist if available (often same as artist, but good to have)
                    # Search results might not have full artist-credit for release, check if present
                    # For now, we might need to fetch release info for full details if not in search result
                    # But let's check what's available in search result usually.
                    # Often release-list items have 'artist-credit' too.
                    
                    # Try to get disc number and track number if available in search result (often limited)
                    # If we want robust data, we should probably do a get_release_by_id call here
                    # But to keep it fast, let's see what we can get.
                    # If 'medium-list' is missing, we might skip discnumber for now or fetch it.
                    
                    # Let's do a quick fetch for the specific release to get detailed track info
                    # This ensures we get correct track number, disc number, and album artist
                    try:
                        release_info = mb_client.get_release_info(release.get('id'))
                        if release_info:
                            # Update album artist
                            rel_artist_credit = release_info.get('artist-credit', [])
                            if rel_artist_credit:
                                new_tags['albumartist'] = rel_artist_credit[0]['artist']['name']
                            
                            # Find our track in the release to get track/disc number
                            # This is a bit complex because a release has media -> tracks
                            # We match by recording ID
                            for medium in release_info.get('medium-list', []):
                                for track in medium.get('track-list', []):
                                    if track.get('recording', {}).get('id') == selected.get('id'):
                                        new_tags['tracknumber'] = track.get('number')
                                        new_tags['discnumber'] = str(medium.get('position'))
                                        break
                    except Exception as e:
                        print(f"Warning: Could not fetch detailed release info: {e}")

                # Get Genre (Tags)
                tags_list = selected.get('tag-list', [])
                if tags_list:
                    # Join top 3 tags or similar
                    genres = [t['name'] for t in tags_list[:3]]
                    new_tags['genre'] = ', '.join(genres)
                
                # Preview comparison
                print("\n--- Tag Preview ---")
                print(f"{'Tag':<20} {'Current':<30} {'New':<30}")
                print("-" * 80)
                
                # Merge keys from both current and new to show all relevant fields
                all_keys = set(current_tags.keys()) | set(new_tags.keys())
                # Filter for interesting keys
                interesting_keys = ['title', 'artist', 'album', 'albumartist', 'date', 'tracknumber', 'discnumber', 'genre', 'musicbrainz_trackid']
                
                for key in interesting_keys:
                    current_val = current_tags.get(key, '')
                    new_val = new_tags.get(key, '')
                    
                    # Only show if there's a value in either
                    if current_val or new_val:
                        # Highlight change if different
                        marker = "*" if current_val != new_val and new_val else " "
                        # Truncate long values
                        c_str = str(current_val)
                        n_str = str(new_val)
                        if len(c_str) > 28: c_str = c_str[:25] + "..."
                        if len(n_str) > 28: n_str = n_str[:25] + "..."
                        
                        print(f"{marker} {key.capitalize():<18} {c_str:<30} {n_str:<30}")
                
                print("-" * 80)
                print("* indicates change")

                confirm = input("\nApply these changes? (y/n/q): ")
                if confirm.lower() == 'y':
                    handler.update_tags(new_tags)
                    print("Done!")
                    return
                elif confirm.lower() == 'q':
                    return
                else:
                    print("Cancelled. Select another match.")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input.")

if __name__ == "__main__":
    main()
