import subprocess
from core.agent import OllamaClient
from tools.ytmusic_client import YTMusicClient

YTMUSIC_SYSTEM = """
Extract the YouTube Music action from the user query. Return JSON:
{"action": "play"|"pause"|"stop"|"resume"|"current", "query": "<song or artist or null>"}
Only output JSON.
"""

class YouTubeMusicAgent:
    def __init__(self, llm: OllamaClient = None):
        self.llm = llm or OllamaClient()
        self.yt = YTMusicClient()
        self.process = None
        self.playing = None

    def _stop_song(self):
        if self.process and self.process.poll() is None:  # Check if process is running
            self.process.terminate()
            self.process = None

    def play_song(self, song_name: str):
        stream_url, title, artist, video_id = self.yt.get_stream_url(song_name)
        # print(stream_url)
        if not stream_url:
            return f"Could not get stream URL for '{song_name}'."
        
        if self.process:
            self._stop_song()

        self.process = subprocess.Popen(
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

        self.playing = [title, artist, video_id]
        return f"Playing: {self.playing[0]} by {self.playing[1]}"
    
    def pause_song(self):
        self._stop_song()
        return "Song paused. Say 'resume' to continue playing."
    
    def resume_song(self):
        if self.playing:
            stream_url = self.yt.get_stream_url_with_video_id(self.playing[2])
            if not stream_url:
                return f"Could not get stream URL for '{self.playing[0]}'."
            self.process = subprocess.Popen(
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
            return f"Resuming: {self.playing[0]} by {self.playing[1]}"
        else:
            return "No song to resume. Please play a song first."
        
    def stop_song(self):
        self._stop_song()
        self.playing = None
        return "Song stopped. If you want to play another song, just tell me the name."

    def current_song(self):
        if self.playing:
            return f"Currently playing: {self.playing[0]} by {self.playing[1]}"
        else:
            return "No song is currently playing."

    

    def run(self, user_query: str) -> str:
        parsed = self.llm.structured_output(user_query, system=YTMUSIC_SYSTEM)
        action = parsed.get("action")
        query  = parsed.get("query")

        if action == "play" and query:
            return self.play_song(query)
        elif action == "pause":
            return self.pause_song()
        elif action == "resume":
            return self.resume_song()
        elif action == "stop":
            return self.stop_song()
        elif action == "current":
            return self.current_song()
        else:
            return "I didn't understand that. Please give me a clear commmand to make sure I can do what you want."

