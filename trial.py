'''
# 1. Search for the song
search_results = yt.search("Never Gonna Give You Up", filter="songs")

# 2. Extract the videoId from the top result
if search_results:
    video_id = search_results[0]['videoId']
    
    # 3. Create a playable URL
    playable_url = f"https://music.youtube.com/watch?v={video_id}"
    print(f"Play this URL in your browser or media player: {playable_url}")
else:
    print("Song not found.")
    
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # ytmsearch1 = search YouTube Music, take top result
        info = ydl.extract_info(f"ytmsearch1:{song_name}", download=False)
        track = info["entries"][0]
        print(f"Found: {track['title']} by {track['channel']}")
        return track["url"]
    
    
    
    
    '''


import subprocess
import yt_dlp
from ytmusicapi import YTMusic

yt = YTMusic("browser.json")

process = None

def search_song(song_name: str) -> dict | None:
    results = yt.search(song_name, filter="songs")
    if not results:
        results = yt.search(song_name)
    print(results)
    return results[0] if results else None

def get_stream_url(song_name: str) -> str:
    """Search YouTube Music and return a direct audio stream URL."""
    ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

    song = search_song(song_name)

    if not song:
        raise ValueError(f"Song '{song_name}' not found on YouTube Music.")
    

    url = f"https://music.youtube.com/watch?v={song['videoId']}"
    print(f"[SpotifyAgent] Found song: {song['title']} by {song['artists'][0]['name']}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("url")
    except Exception as e:
        print(f"Error fetching stream URL: {e}")
        return None


def play(song_name: str):
    global process
    stream_url = get_stream_url(song_name)
    print(stream_url)
    if not stream_url:
        print(f"Could not get stream URL for '{song_name}'.")
        return
    
    if process:
        stop_playback(process)

    process = subprocess.Popen(
        [
            "ffplay",
            "-nodisp",      # No video window
            "-autoexit",    # Exit when done
            "-loglevel", "quiet",  # Suppress output
            stream_url,
        ],
        stdout=subprocess.DEVNULL,      # Suppress stdout
        stderr=subprocess.DEVNULL       # Suppress stderr
    )

def stop_playback(process):
    if process and process.poll() is None:  # Check if process is running
        process.terminate()
        print("Playback stopped.")
    else:
        print("No playback to stop.")


    

# --- Run it ---

while True:
    song = input("Enter song name to play: ")

    if song == "EXIT":
        stop_playback(process)
        break
    play(song)