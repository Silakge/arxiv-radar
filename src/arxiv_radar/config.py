"""Configuration loading, defaults and validation for arxiv-radar."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml

VALID_FORMATS = {"md", "html", "rss"}

# Built-in demo interests so that `arxiv-radar run` works with zero configuration.
DEMO_KEYWORDS = ["large language model", "LLM agents", "reinforcement learning"]
DEMO_CATEGORIES = ["cs.CL", "cs.LG"]

DEFAULT_API_KEY_ENV = "PAPER_RADAR_API_KEY"


class ConfigError(Exception):
    """Raised for any user-facing configuration problem."""


@dataclass
class LlmConfig:
    """Optional OpenAI-compatible LLM enrichment settings."""

    enabled: bool = False
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key_env: str = DEFAULT_API_KEY_ENV
    max_papers: int = 20
    batch_size: int = 8


@dataclass
class RadarConfig:
    name: str = "My Research Radar"
    days: int = 3
    max_papers: int = 20
    categories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    interests: dict[str, float] = field(default_factory=dict)
    llm: LlmConfig = field(default_factory=LlmConfig)
    output_dir: str = "digest"
    formats: list[str] = field(default_factory=lambda: ["md", "html", "rss"])

    def validated(self) -> "RadarConfig":
        if not (1 <= self.days <= 30):
            raise ConfigError(f"radar.days must be between 1 and 30, got {self.days}")
        if not (1 <= self.max_papers <= 100):
            raise ConfigError(
                f"radar.max_papers must be between 1 and 100, got {self.max_papers}"
            )
        if not self.keywords and not self.categories:
            raise ConfigError(
                "at least one of arxiv.keywords or arxiv.categories is required"
            )
        if not self.interests:
            self.interests = {k: 1.0 for k in self.keywords}
        bad = [f for f in self.formats if f not in VALID_FORMATS]
        if bad:
            raise ConfigError(
                f"unknown output formats: {bad}. Valid: {sorted(VALID_FORMATS)}"
            )
        if not self.formats:
            raise ConfigError("output.formats must contain at least one format")
        return self


def _clean_str_list(value: object, what: str) -> list[str]:
    """Normalize a YAML value into a cleaned, de-duplicated list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise ConfigError(f"{what} must be a list of strings")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(f"{what} must contain only strings, got: {item!r}")
        item = item.strip()
        if item and item not in out:
            out.append(item)
    return out


def parse_interests(value: object) -> dict[str, float]:
    """Parse `interests` into {term: weight}.

    Accepted forms:
        - plain strings                       -> weight 1.0
        - a dict {term: weight}
        - a list mixing both, e.g.
              interests:
                - "LLM agents": 3
                - reward model
    """
    if value is None:
        return {}
    result: dict[str, float] = {}

    def _add(term: object, weight: object) -> None:
        if not isinstance(term, str) or not term.strip():
            raise ConfigError(f"interests contain an invalid term: {term!r}")
        try:
            w = float(weight)
        except (TypeError, ValueError):
            raise ConfigError(
                f"interests weight for {term!r} must be a number, got {weight!r}"
            )
        if w <= 0:
            raise ConfigError(f"interests weight for {term!r} must be positive")
        result[term.strip()] = w

    if isinstance(value, dict):
        for term, weight in value.items():
            _add(term, weight)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                for term, weight in item.items():
                    _add(term, weight)
            elif isinstance(item, str):
                _add(item, 1.0)
            else:
                raise ConfigError(f"interests contain an invalid entry: {item!r}")
    else:
        raise ConfigError("interests must be a list or a dict")
    return result


def _as_int(value: object, what: str, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        raise ConfigError(f"{what} must be an integer, got {value!r}")


def _as_bool(value: object, what: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ConfigError(f"{what} must be true or false, got {value!r}")


def load_config(path: str) -> RadarConfig:
    """Load and validate a radar.yaml file."""
    if not os.path.exists(path):
        raise ConfigError(
            f"config file not found: {path}\n"
            "Run `arxiv-radar init` to create one, or `arxiv-radar run` without "
            "a config to try the built-in demo interests."
        )
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML:\n{exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping at the top level")

    radar = data.get("radar") or {}
    arxiv = data.get("arxiv") or {}
    llm_raw = data.get("llm") or {}
    output = data.get("output") or {}
    for section, val in (("radar", radar), ("arxiv", arxiv), ("llm", llm_raw), ("output", output)):
        if not isinstance(val, dict):
            raise ConfigError(f"section `{section}` must be a mapping in {path}")

    llm = LlmConfig(
        enabled=_as_bool(llm_raw.get("enabled"), "llm.enabled", False),
        base_url=str(llm_raw.get("base_url", LlmConfig.base_url)).rstrip("/"),
        model=str(llm_raw.get("model", LlmConfig.model)),
        api_key_env=str(llm_raw.get("api_key_env", DEFAULT_API_KEY_ENV)),
        max_papers=_as_int(llm_raw.get("max_papers"), "llm.max_papers", 20),
        batch_size=max(1, _as_int(llm_raw.get("batch_size"), "llm.batch_size", 8)),
    )

    formats_raw = output.get("formats")
    formats = (
        [str(f).strip().lower() for f in formats_raw]
        if formats_raw
        else ["md", "html", "rss"]
    )

    cfg = RadarConfig(
        name=str(radar.get("name", "My Research Radar")),
        days=_as_int(radar.get("days"), "radar.days", 3),
        max_papers=_as_int(radar.get("max_papers"), "radar.max_papers", 20),
        categories=_clean_str_list(arxiv.get("categories"), "arxiv.categories"),
        keywords=_clean_str_list(arxiv.get("keywords"), "arxiv.keywords"),
        exclude=_clean_str_list(arxiv.get("exclude"), "arxiv.exclude"),
        interests=parse_interests(data.get("interests")),
        llm=llm,
        output_dir=str(output.get("dir", "digest")),
        formats=formats,
    )
    return cfg.validated()


def zero_config() -> RadarConfig:
    """Demo configuration so the very first run needs no setup."""
    return RadarConfig(
        name="Demo Radar (no config found)",
        categories=list(DEMO_CATEGORIES),
        keywords=list(DEMO_KEYWORDS),
    ).validated()


CONFIG_TEMPLATE = """\
# 📡 arxiv-radar configuration
# Full reference: see the README (⚙️ Configuration).

radar:
  name: My Research Radar     # digest title
  days: 3                     # look-back window in days (1-30)
  max_papers: 20              # max papers shown per digest

arxiv:
  categories:                 # arXiv categories to watch (OR-joined). [] = any
    - cs.CL
    - cs.LG
  keywords:                   # used to fetch papers from arXiv (OR-joined)
    - large language model
    - LLM agents
    - reinforcement learning
  exclude: []                 # drop papers whose title+abstract contain any term

interests:                    # scoring weights; higher = more relevant.
  - "LLM agents": 3           # omit this section to score keywords with weight 1
  - "reward model": 2
  - "RLHF": 2

llm:                          # OPTIONAL - any OpenAI-compatible API.
  enabled: false              # false = pure keyword mode, no API key needed
  base_url: https://api.openai.com/v1
  model: gpt-4o-mini
  api_key_env: PAPER_RADAR_API_KEY   # API key is read from the environment
  max_papers: 20              # how many top candidates get an LLM pass

output:
  dir: digest
  formats: [md, html, rss]
"""
