import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

from arxiv_radar.models import Digest, Paper, ScoredPaper
from arxiv_radar.render import render_html, render_markdown, render_rss


def mk_scored(arxiv_id="2611.00001v1", title="Reward Models & <Script> Study",
              abstract="We study reward models.", llm=True):
    published = datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc)
    paper = Paper(
        arxiv_id=arxiv_id, title=title, abstract=abstract, authors=["Alice Chen", "Bob Doe", "C", "D", "E"],
        published=published, updated=published, primary_category="cs.CL",
        categories=["cs.CL", "cs.LG"], abs_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
    )
    return ScoredPaper(
        paper=paper, raw_score=6, score=86, matched=["reward model", "RLHF"],
        llm_relevance=8.4 if llm else None,
        llm_tldr="A solid step for alignment research." if llm else None,
        llm_reason="Directly on reward modeling." if llm else None,
    )


def mk_digest(papers, llm_used=True):
    return Digest(
        radar_name="Test Radar", digest_date=date(2026, 11, 12), window_days=3,
        fetched=137, matched_count=42, query='(cat:cs.CL) AND (all:"RLHF")',
        llm_used=llm_used, papers=papers,
    )


def test_html_renders_and_escapes():
    html = render_html(mk_digest([mk_scored()]))
    assert "Test Radar" in html
    assert "Reward Models" in html
    assert "&lt;Script&gt;" in html  # HTML-escaped title
    assert "<Script>" not in html
    assert "&amp;" in html
    assert "TL;DR" in html
    assert "A solid step for alignment research." in html
    assert "score 86" in html
    assert "tier-high" in html
    assert "Alice Chen, Bob Doe, C, et al." in html
    assert "relevance 8.4/10" in html


def test_html_empty_state():
    html = render_html(mk_digest([], llm_used=False))
    assert "No new papers matched" in html
    assert "keyword mode" in html


def test_markdown_renders():
    md = render_markdown(mk_digest([mk_scored(llm=False)], llm_used=False))
    assert "# 📡 Test Radar" in md
    assert "[Reward Models" in md
    assert "`score 86`" in md
    assert "**Matched**: reward model`, `RLHF" in md
    assert "<details>" in md
    assert "keyword mode" in md  # llm_used False → keyword mode notice


def test_rss_is_valid_xml():
    rss = render_rss(mk_digest([mk_scored(), mk_scored("2611.00002v1", llm=False)]))
    root = ET.fromstring(rss)
    items = root.findall("./channel/item")
    assert len(items) == 2
    assert "Reward Models" in items[0].findtext("title")
    assert items[0].findtext("link") == "https://arxiv.org/abs/2611.00001v1"
