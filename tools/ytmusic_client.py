import yt_dlp
from ytmusicapi import YTMusic

yt = YTMusic("browser.json")

process = None

class YTMusicClient:
    def __init__(self):
        self.yt = YTMusic("browser.json")
        self.ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
            }

    def search_song(self, song_name: str) -> dict | None:
        results = self.yt.search(song_name, filter="songs")
        if not results:
            results = self.yt.search(song_name)
        return results[0] if results else None

    def get_stream_url(self, song_name: str) -> str:
        """Search YouTube Music and return a direct audio stream URL."""
        song = self.search_song(song_name)

        if not song:
            raise ValueError(f"Song '{song_name}' not found on YouTube Music.")
        

        url = f"https://music.youtube.com/watch?v={song['videoId']}"
        print(f"[SpotifyAgent] Found song: {song['title']} by {song['artists'][0]['name']}")
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get("url"), song["title"], song["artists"][0]["name"], song["videoId"]
        except Exception as e:
            print(f"Error fetching stream URL: {e}")
            return None, None, None, None
        
    def get_stream_url_with_video_id(self, video_id: str) -> str:
        '''Get the stream URL without searching for the song again.'''
        url = f"https://music.youtube.com/watch?v={video_id}"
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get("url")
        except Exception as e:
            print(f"Error fetching stream URL: {e}")
            return None
