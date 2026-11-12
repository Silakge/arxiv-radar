<div align="center">

# 📡 arxiv-radar

**让 arXiv 每天自动为你筛选真正相关的新论文。**
一个小型 CLI + 一个 GitHub Action：每天自动抓取 arXiv 最新提交、按**你的**
研究方向打分排序、生成值得认真读的精美日报。

[![CI](https://github.com/Silakge/arxiv-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/Silakge/arxiv-radar/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[English](README.md) · **简体中文**

</div>

---

## 解决什么问题

仅 cs.CL 一个分类，arXiv 每天就有 **约 400 篇新论文**。刷一次列表就被淹没，
然后干脆不刷了——直到审稿人问："为什么不引用那篇关键文献？"

**arxiv-radar 解决的是"阅读清单"问题。** 它每天早上自动完成无聊的部分：
抓取 → 过滤 → 打分 → 排版。评分默认用完全透明的关键词模式（**无需 API Key、
零成本**），也可以开启 LLM 精筛（OpenAI / DeepSeek / GLM / Ollama 等任意
OpenAI 兼容接口）。

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
```

🖼 **看一个真实样例**：[`examples/sample-digest/`](examples/sample-digest/) 是对
arXiv 线上 API 实跑生成的日报（关键词模式）——用浏览器打开
[`2026-11-12.html`](examples/sample-digest/2026-11-12.html) 查看完整效果。

## 为什么选 arxiv-radar

| | |
|---|---|
| 🙈 **零配置即可跑** | 不写任何配置，`arxiv-radar run` 直接用内置示例兴趣生成日报 |
| 🔑 **无需 API Key** | 关键词评分完全离线、完全透明；LLM 只是你可选择的加餐 |
| 🍴 **Fork 即用** | 自带 GitHub Action：Fork 仓库 → 加一份 `radar.yaml` → 每天自动提交日报 |
| 📤 **三种输出** | 单文件 HTML（自适应深色模式）/ Markdown（适合 Issue 与 README）/ RSS 2.0 |
| 🧠 **任意 LLM** | 改一行 `base_url` 即可切换 OpenAI、DeepSeek、智谱 GLM、Moonshot、OpenRouter、本地 Ollama/vLLM |
| 🧹 **自动去重** | 一个小小的 `seen.json` 记录已推送论文，跨运行不重复打扰 |
| 📦 **仅 4 个依赖** | `requests`、`PyYAML`、`Jinja2`、`feedparser` |

## 🚀 快速开始

### 方式 A — GitHub Actions（零本地环境，推荐）

1. **Use this template**（或 Fork）本仓库。
2. 把 [`examples/radar.example.yaml`](examples/radar.example.yaml) 复制为仓库根目录的
   `radar.yaml`，改成你的关键词 / 分类 / 兴趣。
3. （仅当启用了 `llm:`）`Settings → Secrets and variables → Actions` 添加
   Secret：`PAPER_RADAR_API_KEY`。
4. 打开 **Actions** 标签 → **Radar** → **Run workflow**，立刻试跑一次。
5. 完成。以后每天 UTC 08:00（北京时间 16:00）自动生成日报并提交到 `digest/`
   （cron 可在 [`.github/workflows/radar.yml`](.github/workflows/radar.yml) 中修改）。

> 💡 想让日报以 GitHub Issue 形式发布（可订阅、可评论、有通知）？
> 添加仓库变量 `RADAR_PUBLISH_ISSUE=true`。

### 方式 B — 本地 CLI

```bash
pip install git+https://github.com/Silakge/arxiv-radar.git

arxiv-radar init    # 交互式生成 radar.yaml
arxiv-radar run     # 生成今天的日报
arxiv-radar check   # 校验配置并显示实际发出的 arXiv 查询
```

完全没有配置？`arxiv-radar run` 会使用内置示例兴趣直接运行——先看看效果再定制。
发布到 PyPI 后，`uvx arxiv-radar run` 将是真正的一行命令。

要求 Python ≥ 3.9，Windows / macOS / Linux 均可。

## ⚙️ 配置（`radar.yaml`）

```yaml
radar:
  name: My Research Radar     # 日报标题
  days: 3                     # 回看窗口（1-30 天）
  max_papers: 20              # 每期日报最多展示篇数

arxiv:
  categories: [cs.CL, cs.LG]  # 关注的 arXiv 分类（[] = 不限）
  keywords:                   # 抓取查询词（OR 连接，支持多词短语）
    - large language model
    - LLM agents
  exclude: []                 # 标题+摘要包含任一词则直接排除

interests:                    # 评分权重（省略则按关键词、权重 1）
  - "LLM agents": 3
  - "reward model": 2

llm:                          # 可选，任意 OpenAI 兼容 API
  enabled: false              # false = 纯关键词模式
  base_url: https://api.openai.com/v1
  model: gpt-4o-mini
  api_key_env: PAPER_RADAR_API_KEY
  max_papers: 20              # 每次运行送入 LLM 的候选篇数上限

output:
  dir: digest
  formats: [md, html, rss]
```

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `radar.days` | `3` | 按论文 v1 提交日期过滤的时间窗口 |
| `radar.max_papers` | `20` | 日报篇幅上限（1-100） |
| `arxiv.categories` | 不限 | 如 `cs.CL`、`cs.LG`、`stat.ML`、`eess.SP` |
| `arxiv.keywords` | — | OR 连接进 arXiv 查询，自动按短语加引号 |
| `arxiv.exclude` | 无 | 对标题+摘要做大小写不敏感的子串匹配 |
| `interests` | 关键词 ×1 | `{词: 权重}`；标题命中计 3 倍权重 |
| `llm.*` | 关闭 | 见下方服务商表 |
| `output.formats` | 三种全开 | `md`、`html`、`rss` 的任意子集 |

## 🔍 评分原理（完全透明）

对每篇论文的标题与摘要（大小写不敏感）：

```text
raw = Σ  weight(词) × (3 × 标题命中次数 + 摘要命中次数)
```

- 本期最高分归一化为 **100**，其余按比例缩放；
- 档位：**🔥 high ≥ 70 · ● medium ≥ 40 · ○ low**；
- 开启 `llm.enabled` 后，头部候选会额外获得 0-10 的 **relevance** 判断和
  一句话 TL;DR，日报按 LLM 相关性重排。TL;DR 由模型生成——请务必对照摘要核实
  （摘要始终完整展示）。

## 🤖 LLM 服务商（全部可选）

任何兼容 `/chat/completions` 的接口都可以，只需改两行配置：

| 服务商 | `base_url` | `model` 示例 |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| OpenRouter | `https://openrouter.ai/api/v1` | `google/gemini-2.0-flash-001` |
| Ollama（本地） | `http://localhost:11434/v1` | `llama3.1` |
| vLLM（本地） | `http://localhost:8000/v1` | 你部署的模型 |

API Key 从 `api_key_env` 指定的环境变量读取（默认 `PAPER_RADAR_API_KEY`），
**永远不会写进配置文件**。成本有硬上限：每次运行最多送 `llm.max_papers` 篇摘要，
每批 8 篇一次调用。

## 📤 输出说明

- **`digest/YYYY-MM-DD.html`** — 单文件、系统字体、跟随系统深色模式。打开即读，可直接打印。
- **`digest/YYYY-MM-DD.md`** — GitHub 风格 Markdown（`<details>` 折叠摘要），
  适合发 Issue、贴 Slack、或并入仓库 README。
- **`digest/YYYY-MM-DD.xml`** — RSS 2.0，任何阅读器都能订阅静态托管后的地址。
- **`digest/seen.json`** — 去重状态。提交它，日报永不重复推荐。

## ❓ FAQ

**不用 LLM 能用吗？** 能，这就是默认模式。关键词评分透明且免费，LLM 只增加 TL;DR
和第二排序信号。

**为什么偶尔会漏掉跨列表（cross-list）的论文？** 窗口按论文**首次提交**日期过滤，
几天后才 cross-list 到你分类的论文可能超出窗口。适当调大 `radar.days` 即可。

**想同时跑两个雷达（两个课题）？** 两份配置即可：
`arxiv-radar run --config radar-a.yaml --out digest-a`，B 同理。
在 Actions 中复制一份 workflow 并改参数。

**抓 arXiv 合规吗？** arxiv-radar 使用官方
[arXiv API](https://info.arxiv.org/help/api/index.html)，每次运行仅 1 个请求，
远低于官方限速。arXiv 是公共资源，请与我们一起爱护它。

## 🗺 路线图

- [ ] 发布 PyPI → `uvx arxiv-radar` 一行命令
- [ ] 邮件 / Telegram / 飞书推送通道
- [ ] Semantic Scholar 与 OpenReview 数据源
- [ ] 本地 embedding 语义评分（无 API 依赖）
- [ ] `arxiv-radar serve` 本地 Web UI 与历史浏览
- [ ] 星标论文一键导出 BibTeX

欢迎 PR——代码库刻意保持精小。

## 🤝 参与贡献

欢迎 Issue 与 PR！新功能请先开 Issue 对齐范围。开发环境：

```bash
git clone https://github.com/Silakge/arxiv-radar && cd arxiv-radar
pip install -e ".[dev]"
pytest -q          # 全部测试离线、秒级完成
```

## 🙏 同类项目

站在巨人的肩膀上：[AutoLLM/ArxivDigest](https://github.com/AutoLLM/ArxivDigest)、
[dw-dengwei/daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced)、
[ChatPaper](https://github.com/kaixindelele/ChatPaper)。arxiv-radar 的差异点是
**"无需 Key 的关键词模式 + Fork 即用的 Action + 单文件 HTML/RSS"** 的组合——
按自己的工作流任意选择。

## 许可证

[MIT](LICENSE)。
