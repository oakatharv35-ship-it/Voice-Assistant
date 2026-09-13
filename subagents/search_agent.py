from tools.web_search import search_web
from core.agent import OllamaClient


SEARCH_SYSTEM = """
You are a helpful assistant. You will be given a user query and search results.
Synthesize a concise, accurate answer from the search results. Be conversational.
This answer will be read aloud to the user, so keep it short and clear.
"""

class SearchAgent:
    def __init__(self, llm: OllamaClient = None):
        self.llm = llm or OllamaClient()

    def run(self, query: str) -> str:
        context, urls = search_web(query)
        print(f"[SearchAgent] Found {len(context)} results for query: '{query}'")
        if not context:
            return "I couldn't find anything on that. Try rephrasing?"

        prompt = f"User question: {query}\n\nSearch results:\n{context}\n\nAnswer the question."
        return self.llm.generate(prompt, system=SEARCH_SYSTEM)
