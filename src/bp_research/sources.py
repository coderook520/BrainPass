"""Source planner — picks URLs to fetch for a query.

Whitelist lane (safer): Wikipedia REST, arXiv, DuckDuckGo Instant Answer.
Open-web lane (broader): DuckDuckGo HTML Lite + top 3 results.

This module generates candidate URLs. Fetching + sanitizing happens
downstream. If WHITELIST_ONLY=true, only whitelist URLs are emitted.
"""
from __future__ import annotations
import urllib.parse

from . import WHITELIST, WHITELIST_ONLY


def _wikipedia_url(query: str) -> str:
    slug = urllib.parse.quote(query.strip().replace(" ", "_"))
    return f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"


def _arxiv_url(query: str) -> str:
    q = urllib.parse.quote(query.strip())
    return f"https://export.arxiv.org/api/query?search_query=all:{q}&max_results=3"


def _ddg_instant_url(query: str) -> str:
    q = urllib.parse.quote(query.strip())
    return f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1&no_redirect=1"


def _ddg_html_url(query: str) -> str:
    # Lite search — no JS required. Returns HTML of results.
    q = urllib.parse.quote(query.strip())
    return f"https://html.duckduckgo.com/html/?q={q}"


def plan_sources(query: str) -> list[str]:
    urls: list[str] = []
    if len(query) < 3:
        return urls
    urls.append(_wikipedia_url(query))
    urls.append(_ddg_instant_url(query))
    urls.append(_arxiv_url(query))
    if not WHITELIST_ONLY:
        urls.append(_ddg_html_url(query))
    return urls
