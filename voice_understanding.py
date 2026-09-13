import os
import tempfile
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import sounddevice as sd
import soundfile as sf
import pyttsx3
from faster_whisper import WhisperModel


class VoiceLayer:
    def __init__(
        self,
        whisper_model_size: str = "base",
        wake_word: str = "hey assistant",
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        sample_rate: int = 16000,
    ):
        self.wake_word         = wake_word.lower()
        self.silence_threshold = silence_threshold
        self.silence_duration  = silence_duration
        self.sample_rate       = sample_rate

        # STT
        print(f"[Voice] Loading Whisper '{whisper_model_size}'...")
        self.stt = WhisperModel(whisper_model_size, device="cpu", compute_type="int8")
        print("[Voice] Whisper ready. ✓")

        # TTS
        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", 175)
        self.tts.setProperty("volume", 0.9)

    def _record(self) -> np.ndarray:
        """Record from mic until silence."""
        print("[Voice] Listening...")
        chunks       = []
        silent       = 0
        chunk_size   = int(self.sample_rate * 0.1)        # 100ms
        silence_limit = int(self.silence_duration / 0.1)  # in chunks

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
            while True:
                chunk, _ = stream.read(chunk_size)
                chunks.append(chunk.copy())
                energy = np.sqrt(np.mean(chunk ** 2))
                silent = silent + 1 if energy < self.silence_threshold else 0
                if silent >= silence_limit and len(chunks) > silence_limit:
                    break

        return np.concatenate(chunks).flatten()

    def _transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio array to text via Whisper."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        sf.write(tmp, audio, self.sample_rate)
        segments, _ = self.stt.transcribe(tmp, beam_size=5, language="en")
        os.unlink(tmp)
        return " ".join(s.text.strip() for s in segments).strip()

    def listen_once(self) -> str:
        """Record one utterance and return transcribed text."""
        text = self._transcribe(self._record())
        print(f"[Voice] Heard: '{text}'")
        return text

    def listen_for_wake_word(self) -> str | None:
        """Block until wake word is detected, then return the command."""
        print(f"[Voice] Waiting for wake word: '{self.wake_word}'...")
        while True:
            text = self._transcribe(self._record()).lower().strip()
            if not text:
                continue
            print(f"[Voice] Detected: '{text}'")
            if self.wake_word in text:
                after = text.split(self.wake_word, 1)[-1].strip()
                if after:
                    return after
                self.speak("Yes?")
                return self.listen_once()

    def speak(self, text: str) -> None:
        """Speak text aloud."""
        if text:
            print(f"[Voice] Speaking: '{text}'")
            self.tts.say(text)
            self.tts.runAndWait()