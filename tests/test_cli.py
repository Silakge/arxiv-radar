import argparse
import json
from datetime import datetime, timezone
from unittest.mock import Mock

import arxiv_radar.cli as cli
from arxiv_radar.models import Paper


def _args(config, force=False):
    return argparse.Namespace(config=config, force=force)


def test_init_writes_template_when_not_a_tty(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.sys, "stdin", type("FakeStdin", (), {"isatty": lambda self: False})())
    target = tmp_path / "radar.yaml"
    assert cli.cmd_init(_args(str(target))) == 0
    text = target.read_text(encoding="utf-8")
    assert "arxiv-radar configuration" in text
    assert "keywords" in text


def test_init_survives_eof_on_input(tmp_path, monkeypatch, capsys):
    """CI shells can report a tty yet deliver EOF on the first prompt."""
    monkeypatch.setattr(cli.sys, "stdin", type("FakeStdin", (), {"isatty": lambda self: True})())

    def fake_input(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", fake_input)
    target = tmp_path / "radar.yaml"
    assert cli.cmd_init(_args(str(target))) == 0
    assert "arxiv-radar configuration" in target.read_text(encoding="utf-8")
    assert "interactive terminal" in capsys.readouterr().out


def test_init_refuses_overwrite_without_force(tmp_path, capsys):
    target = tmp_path / "radar.yaml"
    target.write_text("existing: true\n", encoding="utf-8")
    assert cli.cmd_init(_args(str(target))) == 1
    assert target.read_text(encoding="utf-8") == "existing: true\n"


def test_init_force_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.sys, "stdin", type("FakeStdin", (), {"isatty": lambda self: False})())
    target = tmp_path / "radar.yaml"
    target.write_text("existing: true\n", encoding="utf-8")
    assert cli.cmd_init(_args(str(target), force=True)) == 0
    assert "arxiv-radar configuration" in target.read_text(encoding="utf-8")


def test_main_reports_config_errors(capsys):
    assert cli.main(["run", "--config", "no-such-file.yaml"]) == 2
    assert "Configuration problem" in capsys.readouterr().err


def test_run_with_llm_enriches_and_reranks_papers(tmp_path, monkeypatch):
    """Exercise the real LLM prompt and response handling without network calls."""
    config = tmp_path / "radar.yaml"
    config.write_text(
        "radar:\n  max_papers: 3\n"
        "arxiv:\n  keywords: [agents]\n"
        "llm:\n  enabled: true\n  max_papers: 2\n"
        "output:\n  formats: [md]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PAPER_RADAR_API_KEY", "test-key")
    published = datetime.now(timezone.utc)
    papers = [
        Paper(
            arxiv_id=f"2611.0000{i}v1",
            title=title,
            abstract="We study agents.",
            authors=["Alice"],
            published=published,
            updated=published,
            primary_category="cs.AI",
            categories=["cs.AI"],
            abs_url=f"https://arxiv.org/abs/2611.0000{i}v1",
            pdf_url=f"https://arxiv.org/pdf/2611.0000{i}v1",
        )
        for i, title in enumerate(
            ["Agents teaching agents", "Planning with agents", "Planning study"], 1
        )
    ]
    monkeypatch.setattr(cli, "fetch_recent", lambda cfg: ('all:"agents"', papers))
    verdicts = {
        papers[0].arxiv_id: {"relevance": 6, "tldr": "Teaching summary.", "reason": "Teaching."},
        papers[1].arxiv_id: {"relevance": 9, "tldr": "Planning summary.", "reason": "Planning."},
    }
    post = Mock()
    post.return_value.json.return_value = {
        "choices": [{"message": {"content": json.dumps(verdicts)}}]
    }
    monkeypatch.setattr("arxiv_radar.llm.requests.post", post)
    output = tmp_path / "digest"

    assert cli.main(["run", "--config", str(config), "--out", str(output)]) == 0

    post.assert_called_once()
    prompt = post.call_args.kwargs["json"]["messages"][1]["content"]
    for paper in papers[:2]:
        assert f"[{paper.arxiv_id}] {paper.title}" in prompt
        assert f"Abstract: {paper.abstract}" in prompt
    assert papers[2].arxiv_id not in prompt  # Respect llm.max_papers.
    digest_path, = output.glob("*.md")
    digest = digest_path.read_text(encoding="utf-8")
    assert "LLM-enhanced" in digest
    assert "Teaching summary." in digest
    assert "Planning summary." in digest
    assert "relevance 9.0/10" in digest
    assert digest.index(papers[1].title) < digest.index(papers[0].title)
    assert digest.index(papers[0].title) < digest.index(papers[2].title)
