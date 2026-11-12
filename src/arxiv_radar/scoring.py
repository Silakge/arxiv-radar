"""Transparent keyword relevance scoring - the mode that needs no API key."""

from __future__ import annotations

from arxiv_radar.models import Paper, ScoredPaper

TITLE_WEIGHT = 3.0  # a term hit in the title counts triple vs. the abstract


def score_paper(paper: Paper, interests: dict[str, float], exclude: list[str]) -> ScoredPaper | None:
    """Score one paper against weighted interest terms.

    Returns None when the paper is excluded by `exclude` or matches nothing.
    """
    title = paper.title.lower()
    abstract = paper.abstract.lower()

    for term in exclude:
        if term.lower() in title or term.lower() in abstract:
            return None

    raw = 0.0
    matched: list[str] = []
    for term, weight in interests.items():
        needle = term.lower()
        hits_title = title.count(needle)
        hits_abstract = abstract.count(needle)
        if hits_title or hits_abstract:
            matched.append(term)
            raw += weight * (TITLE_WEIGHT * hits_title + hits_abstract)

    if raw <= 0:
        return None
    return ScoredPaper(paper=paper, raw_score=raw, score=0, matched=matched)


def score_papers(
    papers: list[Paper], interests: dict[str, float], exclude: list[str]
) -> list[ScoredPaper]:
    """Score a batch and normalize the raw scores to 0-100 within the batch.

    The best-matching paper of the batch gets 100; the rest scale relative to
    it. Ties are broken by publication date (newer first).
    """
    scored = [s for s in (score_paper(p, interests, exclude) for p in papers) if s]
    scored.sort(key=lambda s: (s.raw_score, s.paper.published.timestamp()), reverse=True)
    best = scored[0].raw_score if scored else 0.0
    for s in scored:
        s.score = round(100 * s.raw_score / best) if best else 0
    return scored


def sort_final(scored: list[ScoredPaper]) -> list[ScoredPaper]:
    """Final digest order: LLM relevance (if present) beats keyword score."""
    def key(s: ScoredPaper):
        llm = s.llm_relevance if s.llm_relevance is not None else -1.0
        return (llm, s.raw_score, s.paper.published.timestamp())

    return sorted(scored, key=key, reverse=True)
