from langchain_core.agents import tool
from tools.web_search import fetch_page_text, build_context
from ddgs import DDGS

SEARCH_RESULTS_COUNT = 5

@tool
def search_web(query: str, num_results: int = SEARCH_RESULTS_COUNT) -> tuple[str, str]:
    """
    Search DuckDuckGo and return a list of results.
    Each result: {"title": str, "url": str, "snippet": str, "body": str}
    """
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=num_results):
            body = fetch_page_text(r.get("href", ""))
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "body": body,
                }
            )
    
    if not results:
        return None, None
    else:
        urls = [r["url"] for r in results]
        context = build_context(results)
        print(context)
        return context, urls