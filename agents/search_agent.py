from tools.web_search import search_web
from core.agent import OllamaClient


SEARCH_SYSTEM = """
You are a helpful assistant. You will be given a user query and search results.
Synthesize a concise, accurate answer from the search results. Be conversational.
"""

class SearchAgent:
    def __init__(self, llm: OllamaClient = None):
        self.llm = llm or OllamaClient()

    def run(self, query: str) -> str:
        results, urls = search_web(query)
        print(f"[SearchAgent] Found {len(results)} results for query: '{query}'")
        if not results:
            return "I couldn't find anything on that. Try rephrasing?"

        context = results
        
        prompt = f"User question: {query}\n\nSearch results:\n{context}\n\nAnswer the question."
        return self.llm.generate(prompt, system=SEARCH_SYSTEM)
