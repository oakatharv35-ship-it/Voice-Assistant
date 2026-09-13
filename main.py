import argparse
from subagents.router import RouterAgent
from subagents.qa_agent import QAAgent
from subagents.search_agent import SearchAgent
from subagents.ytmusic_agent import YouTubeMusicAgent
from subagents.google_agent import GoogleAgent
from core.agent import OllamaClient
from core.voice import VoiceLayer


class AIAssistant:
    def __init__(self, use_voice: bool = False, wake_word: str = "google"):
        llm = OllamaClient()
        self.router = RouterAgent(llm)
        self.agents = {
            "qa":      QAAgent(llm),
            "search":  SearchAgent(llm),
            "ytmusic": YouTubeMusicAgent(llm),
            "google":  GoogleAgent(llm),
        }
        self.voice = VoiceLayer(wake_word=wake_word, tts_voice="en-US-JennyNeural") if use_voice else None

    def ask(self, query: str) -> str:
        route  = self.router.route(query)
        intent = route.get("intent", "qa")
        agent  = self.agents.get(intent, self.agents["qa"])
        print(f"[Router] Intent: {intent} (confidence: {route.get('confidence')})")
        return agent.run(query)

    def run_text_mode(self):
        print("Assistant ready (text mode). Ctrl+C to quit.\n")
        while True:
            try:
                query = input("You: ").strip()
                if not query:
                    continue
                response = self.ask(query)
                print(f"Assistant: {response}\n")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break

    def run_voice_mode(self, push_to_talk: bool = False):
        print("Assistant ready (voice mode). Ctrl+C to quit.\n")
        self.voice.speak("Assistant ready. How can I help?")
        while True:
            try:
                if push_to_talk:
                    input("[ Press Enter to speak ]")
                    query = self.voice.listen_once()
                else:
                    query = self.voice.listen_for_wake_word()

                if not query:
                    continue

                print(f"You: {query}")
                response = self.ask(query)
                print(f"Assistant: {response}")
                self.voice.speak(response)

            except KeyboardInterrupt:
                self.voice.speak("Goodbye!")
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"[Main] Error: {e}")
                self.voice.speak("Sorry, something went wrong.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Assistant")
    parser.add_argument("--voice",         action="store_true",         help="Enable voice mode")
    parser.add_argument("--push-to-talk",  action="store_true",         help="Press Enter to speak instead of wake word")
    parser.add_argument("--wake-word",     default="hey assistant",     help="Wake word phrase")
    parser.add_argument("--whisper",       default="base",              help="Whisper model size: tiny/base/small/medium")
    args = parser.parse_args()

    assistant = AIAssistant(
        use_voice=args.voice,
        wake_word=args.wake_word,
    )

    if args.voice:
        assistant.run_voice_mode(push_to_talk=args.push_to_talk)
    else:
        assistant.run_text_mode()