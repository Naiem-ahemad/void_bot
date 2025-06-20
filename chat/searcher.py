# search/searcher.py
from duckduckgo_search import DDGS

def web_search(query: str, num_results: int = 5) -> str:
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append(f"- {r['title']}\n{r['href']}")
        return "\n\n".join(results) if results else "❌ No results found."
    except Exception as e:
        return f"❌ Search failed: {e}"
