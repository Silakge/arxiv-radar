from datetime import datetime, timezone

import feedparser

from arxiv_radar.arxiv import build_query, filter_window, parse_entry
from arxiv_radar.config import zero_config

FIXTURE = "tests/fixtures/sample_feed.xml"


def _entries():
    with open(FIXTURE, "rb") as fh:
        feed = feedparser.parse(fh.read())
    return feed.entries


def test_parse_fixture_entries():
    papers = [p for p in (parse_entry(e) for e in _entries()) if p]
    assert len(papers) == 3

    first = papers[0]
    assert first.arxiv_id == "2611.00001v1"
    assert first.title == "Reward Models for LLM Agents"  # whitespace normalized
    assert first.abstract.startswith("We study reward models for LLM agents & alignment.")
    assert first.authors == ["Alice Chen", "Bob Doe"]
    assert first.primary_category == "cs.CL"
    assert "cs.LG" in first.categories
    assert first.pdf_url == "http://arxiv.org/pdf/2611.00001v1"
    assert first.published.year == 2026 and first.published.month == 11
    assert first.published.tzinfo is not None


def test_pdf_link_fallback_when_missing():
    papers = [p for p in (parse_entry(e) for e in _entries()) if p]
    second = papers[1]
    assert second.pdf_url == "https://arxiv.org/pdf/2611.00002v2"  # constructed from id
    assert second.arxiv_id == "2611.00002v2"


def test_filter_window_drops_old_crosslists():
    papers = [p for p in (parse_entry(e) for e in _entries()) if p]
    now = datetime(2026, 11, 12, tzinfo=timezone.utc)

    within_5 = filter_window(papers, days=5, now=now)
    assert [p.arxiv_id for p in within_5] == ["2611.00001v1", "2611.00002v2"]

    within_30 = filter_window(papers, days=30, now=now)
    assert len(within_30) == 3


def test_build_query_groups_and_quotes():
    query = build_query(["cs.CL", "cs.LG"], ["large language model", "RLHF"])
    assert query == '(cat:cs.CL OR cat:cs.LG) AND (all:"large language model" OR all:"RLHF")'

    assert build_query(["cs.RO"], []) == "cat:cs.RO"
    assert build_query([], ["agents"]) == 'all:"agents"'
    assert build_query([], []) == ""
    # internal quotes are stripped so the query cannot be broken
    assert '" "' not in build_query([], ['a"b OR cat:cs'])


def test_zero_config_builds_query():
    cfg = zero_config()
    query = build_query(cfg.categories, cfg.keywords)
    assert query.startswith("(cat:cs.CL OR cat:cs.LG) AND (")
