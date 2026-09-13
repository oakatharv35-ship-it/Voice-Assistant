from core.agent import OllamaClient

QA_SYSTEM = """
You are a helpful voice assistant like Alexa. Answer questions concisely and
conversationally. Keep responses under 3 sentences unless detail is needed.
"""

class QAAgent:
    def __init__(self, llm: OllamaClient = None):
        self.llm = llm or OllamaClient()

    def run(self, query: str) -> str:
        messages = [{"role": "user", "content": query}]
        return self.llm.chat(messages, system=QA_SYSTEM)
