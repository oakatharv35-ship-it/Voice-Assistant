from core.agent import OllamaClient

ROUTER_SYSTEM = """
You are an intent classifier for a voice assistant. Given a user query,
classify it into exactly ONE of these intents:

- qa: general knowledge question, math, definitions, facts
- search: needs real-time/current info (news, weather, live prices)
- ytmusic: play/pause/skip music, control YouTube Music
- google: check email, calendar events, meetings

Respond ONLY with a JSON object like:
{"intent": "ytmusic", "query": "play lofi beats", "confidence": 0.95}
"""

class RouterAgent:
    def __init__(self, llm: OllamaClient = None):
        self.llm = llm or OllamaClient()

    def route(self, user_query: str) -> dict:
        """Returns {'intent': str, 'query': str, 'confidence': float}"""
        prompt = f'User said: "{user_query}"\n\nClassify this intent.'
        result = self.llm.structured_output(prompt, system=ROUTER_SYSTEM)
        return result