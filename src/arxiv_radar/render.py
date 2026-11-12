"""Render a Digest into Markdown, self-contained HTML, and RSS."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

from jinja2 import Environment, FileSystemLoader

from arxiv_radar.models import Digest

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# NOTE: autoescape is set explicitly rather than via select_autoescape(),
# because template files end in `.j2`, not `.html`.
_env_html = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
_env_md = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=False)


def render_markdown(digest: Digest) -> str:
    template = _env_md.get_template("digest.md.j2")
    return template.render(d=digest)


def render_html(digest: Digest) -> str:
    template = _env_html.get_template("digest.html.j2")
    return template.render(d=digest)


def render_rss(digest: Digest) -> str:
    build_date = format_datetime(
        datetime.combine(digest.digest_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    )
    items = []
    for sp in digest.papers:
        p = sp.paper
        tldr = f"<p><b>TL;DR:</b> {escape(sp.llm_tldr)}</p>" if sp.llm_tldr else ""
        description = f"{tldr}<p>{escape(p.abstract)}</p>"
        items.append(
            "  <item>\n"
            f"    <title>{escape(p.title)}</title>\n"
            f"    <link>{escape(p.abs_url)}</link>\n"
            f"    <guid isPermaLink=\"true\">{escape(p.abs_url)}</guid>\n"
            f"    <pubDate>{format_datetime(p.published)}</pubDate>\n"
            f"    <description>{escape(description)}</description>\n"
            "  </item>"
        )
    items_block = "\n".join(items)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{escape(digest.radar_name)}</title>\n"
        "    <link>https://arxiv.org</link>\n"
        f"    <description>arxiv-radar digest for {digest.digest_date.isoformat()} "
        f"(window: {digest.window_days} days)</description>\n"
        f"    <lastBuildDate>{build_date}</lastBuildDate>\n"
        f"{items_block}\n"
        "  </channel>\n"
        "</rss>\n"
    )


def write_digest(digest: Digest, output_dir: str, formats: list[str]) -> list[str]:
    """Write digest files named by date. Returns the written file paths."""
    os.makedirs(output_dir, exist_ok=True)
    stem = os.path.join(output_dir, digest.digest_date.isoformat())
    renderers = {"md": ("md", render_markdown), "html": ("html", render_html), "rss": ("xml", render_rss)}
    written: list[str] = []
    for fmt in formats:
        extension, renderer = renderers[fmt]
        path = f"{stem}.{extension}"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(renderer(digest))
        written.append(path)
    return written
