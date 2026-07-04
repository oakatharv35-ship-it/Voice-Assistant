import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

SEARCH_RESULTS_COUNT = 5
SNIPPET_CHAR_LIMIT = 500

def fetch_page_text(url: str, char_limit: int = SNIPPET_CHAR_LIMIT) -> str:
    """Fetch and return plain text from a URL, truncated to char_limit."""
    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove script/style noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:char_limit]
    except Exception:
        return ""
 
def build_context(results: list[dict]) -> str:
    """Format search results into a readable context block for the LLM."""
    parts = []
    for i, r in enumerate(results, 1):
        text = r["body"] if r["body"] else r["snippet"]
        parts.append(
            f"[Source {i}] {r['title']}\nURL: {r['url']}\n{text}"
        )
    return "\n\n---\n\n".join(parts)
 
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