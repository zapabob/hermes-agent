"""Scrapling-based web content extraction provider.

Uses Scrapling's Fetcher for HTTP-first extraction with automatic
markdown conversion. No API key required — runs entirely locally.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from agent.web_search_provider import WebSearchProvider
from tools.url_safety import is_safe_url
from tools.website_policy import check_website_access

logger = logging.getLogger(__name__)


class ScraplingWebProvider(WebSearchProvider):
    """Local web extraction via Scrapling."""

    @property
    def name(self) -> str:
        return "scrapling"

    @property
    def display_name(self) -> str:
        return "Scrapling"

    def is_available(self) -> bool:
        try:
            import scrapling  # noqa: F401
            return True
        except ImportError:
            return False

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        from tools.interrupt import is_interrupted
        import urllib.parse
        from urllib.parse import parse_qs, unquote

        if is_interrupted():
            return {"success": False, "error": "Interrupted"}

        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        logger.info("Scrapling search: '%s' (limit=%d)", query, limit)

        from scrapling.fetchers import Fetcher

        page = Fetcher.get(url, timeout=30)

        results = []
        for i, result_block in enumerate(list(page.css(".result"))[:limit]):
            # title: .result__a の ::text
            title = ""
            title_link_sel = result_block.css(".result__a")
            href = ""
            if title_link_sel:
                title_link = list(title_link_sel)[0]
                title = (title_link.css("::text").get() or "").strip()
                href = title_link.attrib.get("href") or ""

            # 実際のURL: DuckDuckGoのリダイレクトURLから uddg パラメータをデコード
            actual_url = ""
            if href.startswith("//duckduckgo.com/l/") or href.startswith("/l/"):
                parsed = urllib.parse.urlparse(href)
                qs = parse_qs(parsed.query)
                uddg = qs.get("uddg", [None])[0]
                if uddg:
                    actual_url = unquote(uddg)
            if not actual_url:
                # fallback: .result__url のテキスト
                url_sel = result_block.css(".result__url")
                if url_sel:
                    url_elem = list(url_sel)[0]
                    actual_url = url_elem.get_all_text().strip()
            if not actual_url:
                actual_url = href

            # description: .result__snippet
            snippet = ""
            snippet_sel = result_block.css(".result__snippet")
            if snippet_sel:
                snippet_elem = list(snippet_sel)[0]
                snippet = snippet_elem.get_all_text().strip()

            results.append(
                {
                    "title": title,
                    "url": actual_url,
                    "description": snippet,
                    "position": i + 1,
                }
            )

        return {"success": True, "data": {"web": results}}

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        from tools.interrupt import is_interrupted

        if is_interrupted():
            return [{"url": u, "error": "Interrupted", "title": ""} for u in urls]

        _format = kwargs.get("format", "markdown")

        from scrapling.fetchers import Fetcher
        from markdownify import markdownify

        results: List[Dict[str, Any]] = []
        for url in urls:
            if is_interrupted():
                results.append({"url": url, "error": "Interrupted", "title": ""})
                continue

            blocked = check_website_access(url)
            if blocked:
                logger.info(
                    "Blocked web_extract for %s by rule %s",
                    blocked["host"],
                    blocked["rule"],
                )
                results.append(
                    {
                        "url": url,
                        "title": "",
                        "content": "",
                        "error": blocked["message"],
                        "blocked_by_policy": {
                            "host": blocked["host"],
                            "rule": blocked["rule"],
                            "source": blocked["source"],
                        },
                    }
                )
                continue

            if not is_safe_url(url):
                results.append(
                    {
                        "url": url,
                        "title": "",
                        "content": "",
                        "error": f"URL blocked by safety policy: {url}",
                    }
                )
                continue

            try:
                logger.info("Scrapling extracting: %s", url)
                page = Fetcher.get(url, timeout=30)
                raw_html = page.html_content
                title = (
                    page.css("h1::text").get()
                    or page.xpath("//title/text()").get()
                    or ""
                )
                content = markdownify(raw_html)
                results.append(
                    {
                        "url": url,
                        "title": title,
                        "content": content,
                        "raw_content": raw_html,
                        "metadata": {"backend": "scrapling"},
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Scrapling extract error for %s: %s", url, exc)
                results.append(
                    {"url": url, "title": "", "content": "", "error": str(exc)}
                )

        return results
