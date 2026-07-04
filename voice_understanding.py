import os
import sys
import time
import queue
import threading
import tempfile
import warnings
warnings.filterwarnings("ignore")  # suppress noisy model load warnings

# STT: faster-whisper (local, runs on CPU or GPU)
from faster_whisper import WhisperModel

# TTS options (in priority order):
#   1. pyttsx3  — offline, zero latency, robotic but reliable
#   2. kokoro   — high quality offline TTS (if installed)
# We try kokoro first, fall back to pyttsx3

TTS_ENGINE = None

try:
    from kokoro import KPipeline
    TTS_ENGINE = "kokoro"
except ImportError:
    pass

if TTS_ENGINE is None:
    try:
        import pyttsx3
        TTS_ENGINE = "pyttsx3"
    except ImportError:
        pass

# Audio playback
try:
    import sounddevice as sd
    import numpy as np
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False


class VoiceLayer:
    """
    Handles:
      - Wake word detection (simple keyword, no cloud needed)
      - Speech-to-text via faster-whisper (local)
      - Text-to-speech via kokoro or pyttsx3 (local)
      - Push-to-talk mode (spacebar) as an alternative to wake word
    """

    def __init__(
        self,
        whisper_model_size: str = "base",       # tiny | base | small | medium | large
        whisper_device: str = "cpu",            # cpu | cuda
        wake_word: str = "hey assistant",
        tts_voice: str = "af_heart",            # kokoro voice; ignored for pyttsx3
        silence_threshold: float = 0.01,        # audio energy below this = silence
        silence_duration: float = 1.5,          # seconds of silence to stop recording
        sample_rate: int = 16000,
    ):
        self.wake_word        = wake_word.lower()
        self.tts_voice        = tts_voice
        self.silence_threshold = silence_threshold
        self.silence_duration  = silence_duration
        self.sample_rate      = sample_rate

        # --- Load Whisper STT model ---
        print(f"[Voice] Loading Whisper '{whisper_model_size}' on {whisper_device}...")
        self.stt = WhisperModel(
            whisper_model_size,
            device=whisper_device,
            compute_type="int8",    # memory efficient; use float16 for GPU
        )
        print("[Voice] Whisper ready. ✓")

        # --- Load TTS engine ---
        self._init_tts()

    # ------------------------------------------------------------------
    # TTS setup
    # ------------------------------------------------------------------

    def _init_tts(self):
        if TTS_ENGINE == "kokoro":
            print("[Voice] Loading Kokoro TTS...")
            self.tts_pipeline = KPipeline(lang_code="a")   # "a" = American English
            print("[Voice] Kokoro TTS ready. ✓")

        elif TTS_ENGINE == "pyttsx3":
            print("[Voice] Loading pyttsx3 TTS...")
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty("rate", 175)        # words per minute
            self.tts_engine.setProperty("volume", 0.9)
            # Pick a female voice if available
            voices = self.tts_engine.getProperty("voices")
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    self.tts_engine.setProperty("voice", v.id)
                    break
            print("[Voice] pyttsx3 TTS ready. ✓")

        else:
            print("[Voice] WARNING: No TTS engine found. Install pyttsx3 or kokoro.")

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _record_until_silence(self) -> np.ndarray:
        """
        Record audio from the microphone, stopping automatically
        after `silence_duration` seconds of silence.
        Returns a float32 numpy array of audio samples.
        """
        if not HAS_SOUNDDEVICE:
            raise RuntimeError("sounddevice not installed. Run: pip install sounddevice")

        print("[Voice] Listening... (speak now)")
        audio_chunks  = []
        silent_chunks = 0
        chunk_size    = int(self.sample_rate * 0.1)   # 100ms chunks
        silence_limit = int(self.silence_duration / 0.1)

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
            while True:
                chunk, _ = stream.read(chunk_size)
                audio_chunks.append(chunk.copy())

                # Measure energy of this chunk
                energy = np.sqrt(np.mean(chunk ** 2))
                if energy < self.silence_threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0   # reset on sound

                if silent_chunks >= silence_limit and len(audio_chunks) > silence_limit:
                    break

        audio = np.concatenate(audio_chunks, axis=0).flatten()
        return audio

    def _transcribe(self, audio: "np.ndarray") -> str:
        """Run faster-whisper on a numpy audio array."""
        # faster-whisper needs a file path or numpy array
        # Write to a temp wav file for reliability
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        try:
            if HAS_SOUNDFILE:
                sf.write(tmp_path, audio, self.sample_rate)
            else:
                # Fallback: write raw PCM via wave module
                import wave, struct
                with wave.open(tmp_path, "w") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    pcm = (audio * 32767).astype("int16")
                    wf.writeframes(pcm.tobytes())

            segments, _ = self.stt.transcribe(tmp_path, beam_size=5, language="en")
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text
        finally:
            os.unlink(tmp_path)

    # ------------------------------------------------------------------
    # STT public methods
    # ------------------------------------------------------------------

    def listen_once(self) -> str:
        """
        Record one utterance and return the transcribed text.
        Use this for push-to-talk or single-shot listening.
        """
        audio = self._record_until_silence()
        text  = self._transcribe(audio)
        print(f"[Voice] Heard: '{text}'")
        return text

    def listen_for_wake_word(self) -> str | None:
        """
        Continuously listen until the wake word is detected.
        Returns the command portion after the wake word,
        or the full next utterance if the wake word was standalone.
        """
        print(f"[Voice] Waiting for wake word: '{self.wake_word}'...")
        while True:
            try:
                audio = self._record_until_silence()
                text  = self._transcribe(audio).lower().strip()

                if not text:
                    continue

                print(f"[Voice] Detected: '{text}'")

                if self.wake_word in text:
                    # Extract command after wake word
                    after = text.split(self.wake_word, 1)[-1].strip()
                    if after:
                        print(f"[Voice] Command: '{after}'")
                        return after
                    else:
                        # Wake word only — listen for the command next
                        self.speak("Yes?")
                        return self.listen_once()

            except KeyboardInterrupt:
                print("\n[Voice] Stopped.")
                return None
            except Exception as e:
                print(f"[Voice] Listen error: {e}")
                time.sleep(0.5)

    # ------------------------------------------------------------------
    # TTS public methods
    # ------------------------------------------------------------------

    def speak(self, text: str) -> None:
        """Convert text to speech and play it."""
        if not text or not text.strip():
            return

        print(f"[Voice] Speaking: '{text}'")

        if TTS_ENGINE == "kokoro":
            self._speak_kokoro(text)
        elif TTS_ENGINE == "pyttsx3":
            self._speak_pyttsx3(text)
        else:
            print(f"[Voice] (no TTS) {text}")

    def _speak_kokoro(self, text: str) -> None:
        if not HAS_SOUNDDEVICE:
            print(f"[Voice] sounddevice missing, can't play audio: {text}")
            return

        generator = self.tts_pipeline(text, voice=self.tts_voice)
        for _, _, audio in generator:
            sd.play(audio, samplerate=24000)
            sd.wait()

    def _speak_pyttsx3(self, text: str) -> None:
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def transcribe_file(self, filepath: str) -> str:
        """Transcribe an existing audio file directly."""
        segments, _ = self.stt.transcribe(filepath, beam_size=5, language="en")
        return " ".join(seg.text.strip() for seg in segments).strip()