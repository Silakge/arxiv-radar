"""Optional LLM enrichment via any OpenAI-compatible chat completions API.

Works with OpenAI, DeepSeek, Zhipu GLM, Moonshot, OpenRouter, Together,
vLLM / Ollama (local), ... anything that speaks /chat/completions.
Deliberately dependency-free: plain `requests`.
"""

from __future__ import annotations

import json
import os
import re
import time

import requests

from arxiv_radar.config import LlmConfig
from arxiv_radar.models import Paper

TIMEOUT_SECONDS = 120
FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

SYSTEM_PROMPT = (
    "You are a research assistant screening new arXiv papers for one researcher. "
    "You judge relevance strictly against the researcher's stated interests and "
    "reply with JSON only."
)


def _user_prompt(interests: dict[str, float], papers: list[Paper]) -> str:
    interest_lines = "\n".join(f"- {term} (weight {w:g})" for term, w in interests.items())
    paper_lines = []
    for p in papers:
        paper_lines.append(
            f'[{p.arxiv_id}] {p.title}\nAbstract: {p.abstract[:1200]}'
        )
    joined = "\n\n".join(paper_lines)
    return (
        f"Research interests (with weights):\n{interest_lines}\n\n"
        f"Papers:\n{joined}\n\n"
        "For EVERY paper id, judge how relevant it is to the interests and reply "
        "with a single JSON object and nothing else:\n"
        '{"<arxiv_id>": {"relevance": <number 0-10>, '
        '"tldr": "<one-sentence summary, max 25 words>", '
        '"reason": "<why it matters for these interests, max 15 words>"}}\n'
        "Rules: relevance 0 = unrelated, 7+ = clearly relevant. Keep tldr/reason "
        "in English. Include every id exactly once."
    )


def _extract_json(text: str) -> dict | None:
    """Tolerant JSON extraction: strip code fences, then find the outer object."""
    text = FENCE_RE.sub("", text.strip())
    for candidate in (text, text[text.find("{"): text.rfind("}") + 1] if "{" in text else ""):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return None


def _call(llm: LlmConfig, api_key: str, papers: list[Paper], interests: dict[str, float]) -> dict:
    resp = requests.post(
        f"{llm.base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": llm.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(interests, papers)},
            ],
        },
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    data = _extract_json(content)
    if data is None:
        raise ValueError(f"model did not return valid JSON: {content[:200]!r}")
    return data


def _normalize_entry(entry: object) -> dict | None:
    """Validate one LLM verdict; returns {relevance, tldr, reason} or None."""
    if not isinstance(entry, dict):
        return None
    relevance = entry.get("relevance")
    try:
        relevance = max(0.0, min(10.0, float(relevance)))
    except (TypeError, ValueError):
        return None
    tldr = str(entry.get("tldr", "")).strip()
    reason = str(entry.get("reason", "")).strip()
    return {"relevance": relevance, "tldr": tldr, "reason": reason}


def enrich(papers: list[Paper], llm: LlmConfig, interests: dict[str, float]) -> dict[str, dict]:
    """Score papers with the LLM in small batches.

    Returns {arxiv_id: {relevance, tldr, reason}}. Papers whose batch failed
    are simply absent - keyword scores remain the fallback. Prints warnings
    instead of raising so a digest is never lost because of the LLM.
    """
    api_key = os.environ.get(llm.api_key_env, "")
    if not api_key:
        print(
            f"⚠️  llm.enabled is true but environment variable "
            f"{llm.api_key_env} is not set - skipping the LLM pass "
            f"(keyword scores will still be computed)."
        )
        return {}

    results: dict[str, dict] = {}
    batches = [papers[i: i + llm.batch_size] for i in range(0, len(papers), llm.batch_size)]
    for index, batch in enumerate(batches, 1):
        print(f"🤖 LLM pass: batch {index}/{len(batches)} ({len(batch)} papers, model={llm.model})")
        data = None
        for attempt in (1, 2):
            try:
                data = _call(llm, api_key, batch, interests)
                break
            except (requests.RequestException, KeyError, ValueError) as exc:
                print(f"   attempt {attempt} failed: {exc}")
                if attempt == 1:
                    time.sleep(2)
        if data is None:
            print("   ⚠️  batch skipped (LLM unavailable) - falling back to keyword scores")
            continue
        for paper in batch:
            entry = _normalize_entry(data.get(paper.arxiv_id))
            if entry:
                results[paper.arxiv_id] = entry
    return results
