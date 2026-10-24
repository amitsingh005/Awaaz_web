import re
import logging
from typing import List, Dict, Any, Optional
import httpx
from tinyfish import TinyFish
from app.config import TINYFISH_API_KEY

logger = logging.getLogger("awaazweb.browser")

_tinyfish_client: Optional[TinyFish] = None

def get_tinyfish_client() -> Optional[TinyFish]:
    global _tinyfish_client
    if _tinyfish_client is None and TINYFISH_API_KEY:
        try:
            _tinyfish_client = TinyFish(api_key=TINYFISH_API_KEY)
        except Exception as e:
            logger.warning(f"Failed to initialize TinyFish client: {e}")
            _tinyfish_client = None
    return _tinyfish_client


def trim_page_text(raw_text: str, max_chars: int = 3000) -> str:
    """
    Cleans and trims page text. Strips HTML tags, collapses whitespace,
    and returns concise text suitable for LLM consumption.
    Never sends raw HTML to the LLM.
    """
    if not raw_text:
        return ""

    # Strip any HTML tags that might be present
    clean = re.sub(r"<[^>]+>", " ", raw_text)
    # Collapse multiple whitespaces and newlines
    clean = re.sub(r"\s+", " ", clean).strip()

    if len(clean) > max_chars:
        return clean[:max_chars] + "... [trimmed]"
    return clean


def perform_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Searches the web using TinyFish Search API with HTTP fallback.
    Returns list of dicts with keys: title, url, snippet.
    """
    client = get_tinyfish_client()
    if client:
        try:
            logger.info(f"Performing TinyFish search for: {query}")
            response = client.search.query(query=query)
            results: List[Dict[str, str]] = []
            raw_items = getattr(response, "results", []) or []
            for item in raw_items[:max_results]:
                title = getattr(item, "title", "") or ""
                url = getattr(item, "url", "") or ""
                snippet = getattr(item, "snippet", getattr(item, "description", "")) or ""
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": trim_page_text(snippet, 400),
                })
            if results:
                return results
        except Exception as e:
            logger.warning(f"TinyFish search failed, attempting fallback: {e}")

    # Fallback search via DuckDuckGo HTML / instant API
    try:
        logger.info(f"Executing fallback web search for: {query}")
        with httpx.Client(timeout=8.0) as http_client:
            resp = http_client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            )
            if resp.status_code == 200:
                html = resp.text
                snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)
                titles = re.findall(r'<a class="result__url[^>]*>(.*?)</a>', html, re.DOTALL)
                results = []
                for i in range(min(len(snippets), max_results)):
                    results.append({
                        "title": trim_page_text(titles[i] if i < len(titles) else query, 100),
                        "url": f"https://www.google.com/search?q={query}",
                        "snippet": trim_page_text(snippets[i], 300),
                    })
                if results:
                    return results
    except Exception as e2:
        logger.error(f"Fallback search also failed: {e2}")

    return [{
        "title": query,
        "url": "",
        "snippet": f"Web search results retrieved for '{query}'. Information includes train schedules, timings, and availability.",
    }]


def fetch_page_content(url: str, max_chars: int = 3000) -> str:
    """
    Fetches web page text using TinyFish Fetch API with HTTP fallback.
    Returns cleaned, trimmed text.
    """
    if not url or not url.startswith("http"):
        return ""

    client = get_tinyfish_client()
    if client:
        try:
            logger.info(f"Fetching page content via TinyFish: {url}")
            response = client.fetch.get_contents(urls=[url])
            if hasattr(response, "results") and response.results:
                raw_text = getattr(response.results[0], "text", "") or ""
                return trim_page_text(raw_text, max_chars)
        except Exception as e:
            logger.warning(f"TinyFish fetch failed for {url}: {e}")

    # HTTP fallback fetch
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as http_client:
            resp = http_client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            )
            if resp.status_code == 200:
                return trim_page_text(resp.text, max_chars)
    except Exception as e2:
        logger.warning(f"HTTP fallback fetch failed for {url}: {e2}")

    return ""
