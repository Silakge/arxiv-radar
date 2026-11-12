from arxiv_radar.scoring import score_paper, score_papers, sort_final
from arxiv_radar.models import Paper, ScoredPaper
from datetime import datetime, timezone


def mk_paper(arxiv_id="2611.00001v1", title="A Paper", abstract="Nothing special.",
             published=datetime(2026, 11, 10, tzinfo=timezone.utc)):
    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        abstract=abstract,
        authors=["A", "B"],
        published=published,
        updated=published,
        primary_category="cs.CL",
        categories=["cs.CL"],
        abs_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
    )


def test_title_hits_weighted_triple():
    interests = {"reward model": 2.0}
    paper = mk_paper(title="Reward Models for LLM Agents",
                     abstract="We study RLHF broadly.")
    scored = score_paper(paper, interests, [])
    assert scored is not None
    # "reward model" appears once in the title (x3), not in the abstract
    assert scored.raw_score == 2.0 * 3.0
    assert scored.matched == ["reward model"]


def test_abstract_hits_counted():
    interests = {"agents": 1.0}
    paper = mk_paper(title="Coordination", abstract="Autonomous agents coordinating with other agents.")
    scored = score_paper(paper, interests, [])
    assert scored is not None
    assert scored.raw_score == 2.0  # "agents" appears twice in the abstract
    assert scored.matched == ["agents"]


def test_no_match_returns_none():
    assert score_paper(mk_paper(), {"quantum": 1.0}, []) is None


def test_exclude_filters_paper():
    paper = mk_paper(title="LLM Survey", abstract="A survey of everything.")
    assert score_paper(paper, {"llm": 1.0}, ["survey"]) is None


def test_normalization_best_gets_100():
    best = mk_paper("id1", title="LLM Agents for LLM Agents", abstract="agents agents agents")
    weak = mk_paper("id2", title="Cooking", abstract="A dash of LLM.")
    scored = score_papers([weak, best], {"llm": 1.0, "agents": 2.0}, [])
    assert [s.paper.arxiv_id for s in scored] == ["id1", "id2"]  # sorted by raw score
    assert scored[0].score == 100
    assert 0 < scored[1].score < 100


def test_sort_final_prefers_llm_relevance():
    p1, p2 = mk_paper("a"), mk_paper("b")
    s1 = ScoredPaper(paper=p1, raw_score=10, score=100)
    s2 = ScoredPaper(paper=p2, raw_score=2, score=40, llm_relevance=9.5)
    assert [sp.paper.arxiv_id for sp in sort_final([s1, s2])] == ["b", "a"]


def test_tier_thresholds():
    assert ScoredPaper(paper=mk_paper(), raw_score=1, score=70).tier == "high"
    assert ScoredPaper(paper=mk_paper(), raw_score=1, score=40).tier == "medium"
    assert ScoredPaper(paper=mk_paper(), raw_score=1, score=10).tier == "low"
