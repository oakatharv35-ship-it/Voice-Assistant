from agents.router import RouterAgent
from agents.qa_agent import QAAgent
from agents.search_agent import SearchAgent
from agents.ytmusic_agent import YouTubeMusicAgent
from agents.google_agent import GoogleAgent
from core.agent import OllamaClient

class AIAssistant:
    def __init__(self):
        llm = OllamaClient()
        self.router  = RouterAgent(llm)
        self.agents  = {
            "qa":      QAAgent(llm),
            "search":  SearchAgent(llm),
            "ytmusic": YouTubeMusicAgent(llm),
            "google":  GoogleAgent(llm),
        }

    def ask(self, query: str) -> str:
        route = self.router.route(query)
        intent = route.get("intent", "qa")
        agent = self.agents.get(intent, self.agents["qa"])
        print(f"[Router] Intent: {intent} (confidence: {route.get('confidence')})")
        return agent.run(query)

if __name__ == "__main__":
    assistant = AIAssistant()
    print("Assistant ready. Type your query (Ctrl+C to quit).\n")
    while True:
        try:
            query = input("You: ").strip()
            if not query:
                continue
            response = assistant.ask(query)
            print(f"Assistant: {response}\n")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break