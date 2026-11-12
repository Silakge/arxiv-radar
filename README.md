<div align="center">

# 📡 arxiv-radar

**Track your research field on autopilot.**
One tiny CLI + one GitHub Action: every day, arxiv-radar fetches fresh arXiv
submissions, ranks them against *your* interests, and renders a beautiful
digest you actually want to read.

[![CI](https://github.com/YOUR_USERNAME/arxiv-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/arxiv-radar/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-contributing)

**English** · [简体中文](README.zh-CN.md)

</div>

---

## The problem

arXiv publishes **~400 new papers a day** in cs.CL alone. You check the
listings once, get overwhelmed, and stop checking. Then a reviewer asks
"why didn't you cite [the one paper that matters]?"

**arxiv-radar fixes the reading list, not the papers.** It does the boring
part — fetch → filter → rank → format — every single morning, using either
transparent keyword scoring (no API key, no cost) or an optional LLM pass
(OpenAI / DeepSeek / GLM / Ollama / anything OpenAI-compatible).

```text
$ arxiv-radar run
📡 My Research Radar · 2026-11-12 · window: last 3 days
   fetched 200 recent submissions · 187 within window
   23 match your interests (keyword scoring)
   11 already in previous digests (seen.json)

✅ Digest ready · showing 12 papers (top score 100/100):
   digest/2026-11-12.md
   digest/2026-11-12.html
   digest/2026-11-12.xml
💡 Open digest/2026-11-12.html in a browser for the full experience.
```

<!-- Drop a screenshot/GIF of digest.html here — the dark mode card view is the money shot. -->

🖼 **See a real one**: [`examples/sample-digest/`](examples/sample-digest/) contains a
digest generated against the live arXiv API in keyword mode — open
[`2026-11-12.html`](examples/sample-digest/2026-11-12.html) in a browser.

## Why arxiv-radar

| | |
|---|---|
| 🙈 **Zero-config demo** | `arxiv-radar run` works *before* any configuration, with built-in demo interests |
| 🔑 **No API key required** | Transparent keyword scoring is fully offline. Add an LLM pass only if you want TL;DRs |
| 🍴 **Fork-and-forget** | Ships with a GitHub Action: fork, add `radar.yaml`, done. Digests are committed daily |
| 📤 **Three output formats** | Self-contained HTML (dark mode), Markdown (README/issues-friendly), RSS 2.0 |
| 🧠 **Any LLM** | One `base_url` away from OpenAI, DeepSeek, Zhipu GLM, Moonshot, OpenRouter, or local Ollama/vLLM |
| 🧹 **Dedup built-in** | A tiny `seen.json` tracks what you already received across runs |
| 📦 **4 dependencies** | `requests`, `PyYAML`, `Jinja2`, `feedparser`. That's it |

## 🚀 Quickstart

### Option A — GitHub Actions (zero local setup, recommended)

1. **Use this template** (or fork) this repository.
2. In your fork, copy [`examples/radar.example.yaml`](examples/radar.example.yaml)
   to `radar.yaml` (repo root) and edit your keywords/categories/interests.
3. `Settings → Secrets and variables → Actions` → *(only if you enabled `llm:`)*
   add a secret named `PAPER_RADAR_API_KEY`.
4. Go to the **Actions** tab → **Radar** → **Run workflow** to test right now.
5. Done. A fresh digest lands in `digest/` every day at 08:00 UTC
   (edit the cron in [`.github/workflows/radar.yml`](.github/workflows/radar.yml)).

> 💡 Want digests as GitHub issues (watchable, commentable, notification-friendly)?
> Add a repository variable `RADAR_PUBLISH_ISSUE=true`.

### Option B — local CLI

```bash
pip install git+https://github.com/YOUR_USERNAME/arxiv-radar.git

arxiv-radar init    # creates radar.yaml interactively
arxiv-radar run     # generates today's digest
arxiv-radar check   # validates config, shows the exact arXiv query
```

No config at all? `arxiv-radar run` uses built-in demo interests — perfect
for a first look. Once published to PyPI, `uvx arxiv-radar run` will be a
true one-liner.

Python ≥ 3.9. Windows / macOS / Linux.

## ⚙️ Configuration (`radar.yaml`)

```yaml
radar:
  name: My Research Radar     # digest title
  days: 3                     # look-back window (1-30)
  max_papers: 20              # max papers per digest

arxiv:
  categories: [cs.CL, cs.LG]  # arXiv categories to watch ([] = any)
  keywords:                   # fetch query, OR-joined (multi-word OK)
    - large language model
    - LLM agents
  exclude: []                 # hard-drop papers containing any term

interests:                    # scoring weights (omit → keywords @ weight 1)
  - "LLM agents": 3
  - "reward model": 2

llm:                          # optional, any OpenAI-compatible API
  enabled: false              # false = pure keyword mode
  base_url: https://api.openai.com/v1
  model: gpt-4o-mini
  api_key_env: PAPER_RADAR_API_KEY
  max_papers: 20              # candidates sent to the LLM per run

output:
  dir: digest
  formats: [md, html, rss]
```

| Key | Default | Notes |
|---|---|---|
| `radar.days` | `3` | Window for `published` date of v1 submissions |
| `radar.max_papers` | `20` | Digest length cap (1-100) |
| `arxiv.categories` | *(any)* | e.g. `cs.CL`, `cs.LG`, `stat.ML`, `eess.SP` |
| `arxiv.keywords` | — | OR-joined into the arXiv query; quoted as phrases |
| `arxiv.exclude` | *(none)* | Substring match on title+abstract, case-insensitive |
| `interests` | keywords ×1 | `{term: weight}`; title hits count 3× abstract hits |
| `llm.*` | disabled | See provider table below |
| `output.formats` | all three | Any subset of `md`, `html`, `rss` |

## 🔍 How scoring works

For each paper, over title + abstract (case-insensitive):

```text
raw = Σ  weight(term) × (3 × hits_in_title + hits_in_abstract)
```

- The best paper of the batch is normalized to **100**; others scale relative to it.
- **🔥 high ≥ 70 · ● medium ≥ 40 · ○ low** tiers.
- With `llm.enabled`, the top candidates also get a 0-10 **relevance** judgment
  plus a one-sentence TL;DR; the digest re-ranks by LLM relevance. TL;DRs are
  model-generated — always verify against the abstract (which is always included).

## 🤖 LLM providers (all optional)

Any OpenAI-compatible `/chat/completions` endpoint works — change two lines:

| Provider | `base_url` | `model` example |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Zhipu GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| OpenRouter | `https://openrouter.ai/api/v1` | `google/gemini-2.0-flash-001` |
| Ollama (local) | `http://localhost:11434/v1` | `llama3.1` |
| vLLM (local) | `http://localhost:8000/v1` | your served model |

The key is read from the environment variable named by `api_key_env`
(default `PAPER_RADAR_API_KEY`) — never stored in the config file.
Costs stay bounded: at most `llm.max_papers` abstracts per run, batched 8 per call.

## 📤 Outputs

- **`digest/YYYY-MM-DD.html`** — self-contained single file, system fonts, dark
  mode via `prefers-color-scheme`. Open it, print it, share it.
- **`digest/YYYY-MM-DD.md`** — GitHub-flavored Markdown with `<details>`
  abstracts; perfect for issues, Slack snippets, or your repo's README.
- **`digest/YYYY-MM-DD.xml`** — RSS 2.0; point any feed reader at the raw URL
  (e.g. `https://raw.githubusercontent.com/<you>/<fork>/main/digest/latest.xml`
  via a redirect service, or serve the folder anywhere static).
- **`digest/seen.json`** — dedup state. Commit it and digests never repeat papers.

## ❓ FAQ

**Does it work without an LLM?** Yes — that's the default. Keyword scoring is
transparent and free; the LLM pass only adds TL;DRs and a second ranking signal.

**Why do I miss cross-listed papers sometimes?** The window filters on the
*original submission* date, so a paper cross-listed to your category days
later may fall outside. Raise `radar.days` to compensate.

**How do I run two radars (e.g. two projects)?** Two config files:
`arxiv-radar run --config radar-a.yaml --out digest-a` and the same for B.
In Actions, duplicate the workflow with different args.

**Is scraping arXiv OK?** arxiv-radar uses the official
[arXiv API](https://info.arxiv.org/help/api/index.html), one request per run,
well within their rate limits. arXiv is a public good — please keep it that way.

**Where do digests go locally?** `./digest/` by default; override with
`--out` or `output.dir`.

## 🗺 Roadmap

- [ ] PyPI release → `uvx arxiv-radar` one-liner
- [ ] Email / Telegram / Feishu push channels
- [ ] Semantic Scholar & OpenReview sources
- [ ] Embedding-based scoring (local models, no API)
- [ ] `arxiv-radar serve` — tiny local web UI with archive browsing
- [ ] Bibtex export of starred papers

PRs welcome — the codebase is small on purpose.

## 🤝 Contributing

Issues and PRs are welcome! For a feature, open an issue first so we can agree
on scope. Dev setup:

```bash
git clone https://github.com/YOUR_USERNAME/arxiv-radar && cd arxiv-radar
pip install -e ".[dev]"
pytest -q          # all tests are offline & fast
```

## 🙏 Similar projects

Standing on the shoulders of: [AutoLLM/ArxivDigest](https://github.com/AutoLLM/ArxivDigest),
[dw-dengwei/daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced),
[ChatPaper](https://github.com/kaixindelele/ChatPaper). arxiv-radar's niche is
the **zero-key keyword mode + fork-and-forget Action + single-file HTML/RSS**
combination — use whichever fits your workflow.

## License

[MIT](LICENSE) — free for research and everything else.
