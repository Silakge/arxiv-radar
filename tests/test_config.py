import pytest

from arxiv_radar.config import (
    CONFIG_TEMPLATE,
    ConfigError,
    load_config,
    parse_interests,
    zero_config,
)


def test_full_config_roundtrip(tmp_path):
    path = tmp_path / "radar.yaml"
    path.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    cfg = load_config(str(path))
    assert cfg.name == "My Research Radar"
    assert cfg.days == 3
    assert cfg.max_papers == 20
    assert cfg.categories == ["cs.CL", "cs.LG"]
    assert "large language model" in cfg.keywords
    assert cfg.interests["LLM agents"] == 3
    assert cfg.interests["reward model"] == 2
    assert cfg.llm.enabled is False
    assert cfg.llm.base_url == "https://api.openai.com/v1"
    assert cfg.llm.api_key_env == "PAPER_RADAR_API_KEY"
    assert cfg.output_dir == "digest"
    assert cfg.formats == ["md", "html", "rss"]


def test_interests_forms():
    assert parse_interests(["a", "b"]) == {"a": 1.0, "b": 1.0}
    assert parse_interests({"a": 2}) == {"a": 2.0}
    assert parse_interests([{"a": 3}, "b"]) == {"a": 3.0, "b": 1.0}
    assert parse_interests(None) == {}


def test_interests_validation():
    with pytest.raises(ConfigError):
        parse_interests([{"a": -1}])
    with pytest.raises(ConfigError):
        parse_interests([{"a": "high"}])
    with pytest.raises(ConfigError):
        parse_interests([42])


def test_keywords_alone_is_valid(tmp_path):
    path = tmp_path / "radar.yaml"
    path.write_text(
        "radar:\n  days: 5\narxiv:\n  keywords: [RLHF]\n"
        "output:\n  formats: [md]\n",
        encoding="utf-8",
    )
    cfg = load_config(str(path))
    assert cfg.days == 5
    assert cfg.max_papers == 20  # default
    assert cfg.interests == {"RLHF": 1.0}  # derived from keywords
    assert cfg.formats == ["md"]


def test_empty_arxiv_section_rejected(tmp_path):
    path = tmp_path / "radar.yaml"
    path.write_text("radar:\n  days: 3\narxiv: {}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="keywords or arxiv.categories"):
        load_config(str(path))


def test_out_of_range_days_rejected(tmp_path):
    path = tmp_path / "radar.yaml"
    path.write_text("radar:\n  days: 99\narxiv:\n  keywords: [x]\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="days"):
        load_config(str(path))


def test_bad_format_rejected(tmp_path):
    path = tmp_path / "radar.yaml"
    path.write_text("arxiv:\n  keywords: [x]\noutput:\n  formats: [docx]\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="docx"):
        load_config(str(path))


def test_missing_file_is_friendly():
    with pytest.raises(ConfigError, match="arxiv-radar init"):
        load_config("no-such-radar.yaml")


def test_invalid_yaml_is_friendly(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("radar: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid YAML"):
        load_config(str(path))


def test_zero_config_is_valid():
    cfg = zero_config()
    assert cfg.keywords and cfg.categories
    assert cfg.interests  # derived from keywords


def test_base_url_trailing_slash_stripped(tmp_path):
    path = tmp_path / "radar.yaml"
    path.write_text(
        "arxiv:\n  keywords: [x]\n"
        "llm:\n  enabled: true\n  base_url: https://api.deepseek.com/v1/\n",
        encoding="utf-8",
    )
    cfg = load_config(str(path))
    assert cfg.llm.base_url == "https://api.deepseek.com/v1"
    assert cfg.llm.enabled is True
