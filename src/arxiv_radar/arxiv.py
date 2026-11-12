"""arXiv API client: build a query, fetch recent papers, parse the Atom feed."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from arxiv_radar.config import RadarConfig
from arxiv_radar.models import Paper

API_URL = "https://export.arxiv.org/api/query"
MAX_RESULTS = 200  # polite upper bound: one request per run
RETRIES = 3
RETRY_BACKOFF_SECONDS = 3.0
REQUEST_TIMEOUT = 40


class ArxivError(Exception):
    """Raised when the arXiv API cannot be reached or parsed."""


def build_query(categories: list[str], keywords: list[str]) -> str:
    """Build an arXiv API search query.

    Categories are OR-joined (`cat:cs.CL`), keywords are OR-joined quoted
    phrases (`all:"large language model"`), and the two groups are ANDed.
    """
    parts: list[str] = []
    if categories:
        cat_q = " OR ".join(f"cat:{c}" for c in categories)
        parts.append(f"({cat_q})" if len(categories) > 1 else cat_q)
    if keywords:
        clean = [k.replace('"', " ") for k in keywords]
        kw_q = " OR ".join(f'all:"{k}"' for k in clean)
        parts.append(f"({kw_q})" if len(keywords) > 1 else kw_q)
    return " AND ".join(parts)


def _parse_date(value: str | None, fallback: datetime | None = None) -> datetime:
    """Parse an arXiv Atom date string, tolerating format quirks."""
    if value:
        text = value.strip()
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(text, fmt)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    if fallback is not None:
        return fallback
    return datetime.now(timezone.utc)


def _normalize(text: str | None) -> str:
    return " ".join((text or "").split())


def parse_entry(entry: object) -> Paper | None:
    """Convert one feedparser entry into a Paper, skipping malformed entries."""
    entry_id = getattr(entry, "id", "") or ""
    if "/abs/" not in entry_id:
        return None
    abs_url = entry_id
    arxiv_id = entry_id.rsplit("/abs/", 1)[1]
    title = _normalize(getattr(entry, "title", ""))
    if not title:
        return None
    abstract = _normalize(getattr(entry, "summary", ""))

    authors: list[str] = []
    for author in getattr(entry, "authors", []) or []:
        name = _normalize(getattr(author, "name", ""))
        if not name and isinstance(author, str):
            name = _normalize(author)
        if name:
            authors.append(name)
    if not authors:
        authors = [_normalize(getattr(entry, "author", "")) or "Unknown"]

    published = _parse_date(getattr(entry, "published", None))
    updated = _parse_date(getattr(entry, "updated", None), fallback=published)

    categories = [t.get("term") for t in (getattr(entry, "tags", None) or []) if t.get("term")]
    primary = categories[0] if categories else ""

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    for link in getattr(entry, "links", None) or []:
        if link.get("rel") == "related" and "pdf" in (link.get("type") or ""):
            pdf_url = link["href"]
            break

    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        abstract=abstract,
        authors=authors,
        published=published,
        updated=updated,
        primary_category=primary,
        categories=categories,
        abs_url=abs_url,
        pdf_url=pdf_url,
    )


def _fetch_atom(query: str, max_results: int) -> bytes:
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    last_error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.content
            last_error = ArxivError(f"arXiv API returned HTTP {resp.status_code}")
        except requests.RequestException as exc:
            last_error = exc
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF_SECONDS)
    raise ArxivError(
        f"could not reach the arXiv API after {RETRIES} attempts: {last_error}"
    )


def fetch_recent(cfg: RadarConfig, max_results: int = MAX_RESULTS) -> tuple[str, list[Paper]]:
    """Fetch the most recent arXiv papers matching the config.

    Returns (query, papers) with the newest submissions first.
    """
    query = build_query(cfg.categories, cfg.keywords)
    if not query:
        raise ArxivError("empty arXiv query: configure arxiv.keywords/categories")
    content = _fetch_atom(query, max_results)
    feed = feedparser.parse(content)
    entries = getattr(feed, "entries", None) or []
    if not entries:
        bozo = getattr(feed, "bozo_exception", None)
        raise ArxivError(f"arXiv returned no entries{f' ({bozo})' if bozo else ''}")
    papers = []
    for entry in entries:
        paper = parse_entry(entry)
        if paper is not None:
            papers.append(paper)
    return query, papers


def filter_window(papers: list[Paper], days: int, now: datetime | None = None) -> list[Paper]:
    """Keep only papers published within the last `days` days (UTC)."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    return [p for p in papers if p.published.replace(tzinfo=timezone.utc) >= cutoff]
