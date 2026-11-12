"""Data models for arxiv-radar."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Paper:
    """A single arXiv paper."""

    arxiv_id: str  # e.g. "2501.12345v2"
    title: str
    abstract: str
    authors: list[str]
    published: datetime  # aware UTC datetime of v1
    updated: datetime
    primary_category: str  # e.g. "cs.CL"
    categories: list[str]
    abs_url: str
    pdf_url: str

    @property
    def published_str(self) -> str:
        return self.published.strftime("%Y-%m-%d")

    @property
    def author_list(self) -> str:
        """Authors formatted for display: first 3 + et al. when long."""
        if len(self.authors) <= 4:
            return ", ".join(self.authors)
        return ", ".join(self.authors[:3]) + ", et al."


@dataclass
class ScoredPaper:
    """A paper with keyword relevance score and optional LLM enrichment."""

    paper: Paper
    raw_score: float
    score: int  # normalized 0-100 within one digest
    matched: list[str] = field(default_factory=list)
    llm_relevance: float | None = None  # 0-10 from the LLM pass
    llm_tldr: str | None = None
    llm_reason: str | None = None

    @property
    def tier(self) -> str:
        if self.score >= 70:
            return "high"
        if self.score >= 40:
            return "medium"
        return "low"


@dataclass
class Digest:
    """Everything needed to render one daily digest."""

    radar_name: str
    digest_date: date
    window_days: int
    fetched: int
    matched_count: int
    query: str
    llm_used: bool
    papers: list[ScoredPaper]
