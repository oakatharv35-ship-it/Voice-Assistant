from faster_whisper import WhisperModel
from gtts import gTTS


model = WhisperModel("base", compute_type="int8")


def speech_to_text(path: str) -> str:
    segments, _ = model.transcribe(path)
    text = " ".join(segment.text.strip() for segment in segments)
    return text.strip()

def text_to_speech(text: str, out_path: str = "reply.mp3") -> str:
    tts = gTTS(text=text)
    tts.save(out_path)
    return out_path

