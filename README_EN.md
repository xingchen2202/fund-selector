# Fund Selector — AI-Powered Mutual Fund Research Assistant for A-Shares

> "One person + Claude Code = A research team."

**Fund Selector v2.0** is a Claude Code Skill collection for researching mainland China mutual funds (A-share 公募基金). Built on a three-layer architecture philosophy, it combines adversarial multi-perspective value investing methodology with AI agents, spanning deep research, earnings analysis, industry screening, portfolio management, and thinking tools.

Powered by Claude Code + MCP (cn-financial / cn-mutual-fund) real-time data, with **64 automated tests passing** — ensuring every report's data rigor is verifiable.

[Why not just ask AI?](#why-not-just-ask-ai) · [Skills Overview (20)](#skills-overview-20) · [Quick Start](#quick-start) · [Architecture](#architecture) · [Test Coverage](#test-coverag

---

## Why Not Just Ask AI?

Ask Claude directly: "Analyze 中欧新趋势混合基金 for me." You'll get a balanced "on one hand... on the other hand..." analysis ending with "invest at your own risk."

**The analysis looks right, but you can't make decisions with it.**

Fund Selector solves not "can it analyze" but "**analysis quality and decision discipline**."

### How a Normal LLM Responds

```
中欧新趋势混合基金（166001）业绩优秀，成立以来收益可观。
近1年回报+4.9%，但最大回撤较大。基金经理周蔚文经验丰富。
总体来看，这只基金适合长期投资者，但需注意波动风险。
投资有风险，入市需谨慎。
```

**Problems**: Both-siding hedging, no conclusion, no data validation, no risk thresholds, no actionability.

---

### How Fund Selector Responds

```
▌ Data Layer
  Scale: ¥2.893B (verified: deviation 0.33% ✓)
  Manager: Zhou Weiwen (10+ years) | Total fees: 1.5%
  1Y return: +4.9% | Max drawdown: -64.5%

▌ Risk Assessment
  ⚠️ Max drawdown -64.5% breaches -35% equity threshold
  → Triggers Fast-Rejection Rule R3: ONE-VOTE VETO

▌ Conclusion: ❌ Not Recommended
  Reason: Excessive drawdown, fails conservative portfolio criteria
```

**Difference**: Data-validated, risk-thresholded, conclusion-driven, action-oriented.

---

### Six Core Differences

**1. Data-backed, not vague descriptors**

A normal LLM says "strong performance." We fetch real-time NAV, scale, and fees via MCP and cross-validate:

```bash
# Scale verification: shares × NAV vs reported scale
python tools/financial_rigor.py verify-scale \
  --nav 1.0553 --shares 4.42e8 --reported 4.68e8
# ✅ Verified, deviation only 0.33%
```

All calculations use `decimal.Decimal` (exact decimal arithmetic), never `float`.

**2. Rule-guarded, not free-form**

A normal LLM has no risk thresholds. We enforce **8 iron rules**:

| Red Line | Trigger | Action |
|----------|---------|--------|
| Excessive drawdown | Equity max drawdown < -35% | One-vote veto |
| Insufficient scale | Fund scale < ¥200M | Exclude |
| High fees | Total fees > 2.5%/yr | Warning |
| Short manager tenure | < 1 year | Exclude |

**3. Adversarial perspectives, not single analysis**

A normal LLM uses one voice. We use **dual-agent adversarial analysis + conflict detection**:

- **Offense Agent** (growth lens): 南方电池C +66.88%, strong momentum → 5 stars
- **Defense Agent** (risk lens): 南方电池C drawdown -27.86%, high volatility → 4 stars
- **Conflict detection**: Star gap ≥2 → flagged "perspective divergence — needs deeper discussion"

**4. Penetration analysis, not surface metrics**

A normal LLM looks at fund NAV. We **drill down to underlying holdings**:

- What stocks does the fund hold?
- What are their gross margins, ROEs, market positions?
- Are they "bottleneck nodes" (perilla-grade)?

**5. Reproducible process, not reinventing each time**

A normal LLM outputs different formats each run. We ensure: **same input → structurally consistent output**.

**6. Automated tests, not manual checking**

64 test cases cover the full pipeline — refactoring has a safety net.

```bash
python .claude/skills/fund-selector/tests/agents/test_agents_v2.py
python .claude/skills/fund-selector/tests/tools/test_tools.py
# Result: 64/64 green
```

---

## Architecture

**Three-layer design philosophy**:

- **Layer 1 — Skills**: 20 clear entry points abstracted by scenario: deep research, earnings analysis, industry screening, portfolio management, thinking tools, theme bottleneck analysis
- **Layer 2 — Agents**: Team-based skills (e.g., `/fund-team`, `/news-pulse`) use a Team Lead to parallel-dispatch 4 master-perspective agents — each independently searches MCP data, forms judgments, and challenges others, then synthesized by the Team Lead; lightweight skills bypass this layer and connect directly to tools for fast in-out
- **Layer 3 — Tools**: Exact calculation (Decimal), real-time retrieval (MCP), report auditing (15% sampling) — ensuring every report's data rigor is verifiable

---

## Skills Overview (20)

### Deep Research (5)

| Skill | Purpose | Type |
|-------|---------|------|
| `/fund-deep-research` | Single-fund deep dive (penetration + six-gate scoring + mirror test) | Lightweight |
| `/fund-team` | Multi-agent parallel research team | Team-based |
| `/manager-deep-dive` | Fund manager deep profile | Lightweight |
| `/private-fund-research` | Private/non-public fund research | Lightweight |
| `/fund-series` | 8-article fund series report | Team-based |

### Earnings Analysis (2)

| Skill | Purpose | Type |
|-------|---------|------|
| `/fund-earnings-review` | Quarterly/annual report interpretation | Lightweight |
| `/fund-earnings-team` | Multi-perspective earnings reading team | Team-based |

### Industry Screening (5)

| Skill | Purpose | Type |
|-------|---------|------|
| `/industry-research` | Industry chain research | Lightweight |
| `/industry-funnel` | Market-wide funnel screening (30-60→≤10→3) | Lightweight |
| `/quality-screen` | Quality exclusion screen (7 hard rules + 3 exemptions) | Lightweight |
| `/bottleneck-hunter` | Supply chain bottleneck arbitrage | Lightweight |
| `/fund-checklist` | Pre-purchase 6-gate checklist | Lightweight |

### Portfolio Management (4)

| Skill | Purpose | Type |
|-------|---------|------|
| `/portfolio-review` | Portfolio management | Lightweight |
| `/thesis-tracker` | Post-purchase tracking (quarterly review) | Lightweight |
| `/thesis-drift` | Investment thesis drift detection | Lightweight |
| `/news-pulse` | Rapid news attribution (10-min response) | Team-based |

### Thinking Tools (3)

| Skill | Purpose | Type |
|-------|---------|------|
| `/fund-ask` | Master Q&A simulation (Buffett/Duan/Munger/Li) | Lightweight |
| `/financial-data` | Dual-source data cross-validation | Lightweight |
| `/fund-article` | Research report writing factory | Team-based |

### Theme Bottleneck Analysis (1)

| Skill | Purpose | Type |
|-------|---------|------|
| `/theme-perilla` | Perilla theme bottleneck analysis | Lightweight |

---

## Quick Start

### 1. Requirements

- Claude Code: `npm install -g @anthropic-ai/claude-code`
- Python >= 3.7 (stdlib only, no pip install needed)
- MCP servers: cn-financial + cn-mutual-fund (configured in `.mcp.json`)

### 2. Install

```bash
git clone https://github.com/xingchen2202/fund-selector
cd fund-selector

# Verify MCP connections
# In Claude Code, run:
# > /mcp
# Confirm cn-financial and cn-mutual-fund status shows ✓ connected
```

### 3. Usage

```bash
# Deep research
/fund-deep-research 中欧新趋势混合
/fund-team 国泰有色矿业

# Industry screening
/industry-funnel 电池
/quality-screen 沪深300成分股
/fund-checklist 易方达蓝筹, 中欧医疗, 招商白酒

# Portfolio management
/portfolio-review
/thesis-tracker 001198
/news-pulse 018167

# Thinking tools
/fund-ask 红利低波策略现在还能买吗？
/financial-data 中欧新趋势混合 规模
/fund-article 电池行业

# Perilla theme bottleneck analysis
/theme-perilla AI算力
/theme-perilla 新能源
/theme-perilla 半导体
```

---

## Agent Layer (Team-Based Skills Only)

### 4 Master Perspectives

| Agent | Lens | Core Question |
|-------|------|---------------|
| Offense Agent | Duan Yongping | Growth momentum, sector prosperity |
| Defense Agent | Warren Buffett | Drawdown, volatility, scale+fees |
| Risk Agent | Li Lu | Maximum risk, extreme loss |
| Cycle Agent | Charlie Munger | Industry landscape, competition |

### Dispatch Flow

```
User triggers team-based skill
  → Team Lead parallel-launches 4 agents
  → Each independently searches MCP data + forms judgment
  → 4-perspective conclusions aggregated to Team Lead
  → Conflict detection (star gap ≥2 or rank gap ≥3 flagged)
  → Synthesize → generate report
  → Report audit gate (15% sampling verification)
```

---

## Tool Layer

| Tool | Purpose | Key Subcommands |
|------|---------|-----------------|
| `tools/financial_rigor.py` | Decimal precision verification | `verify-scale`, `verify-valuation`, `cross-validate`, `benford`, `calc`, `three-scenario` |
| `tools/report_audit.py` | Report quality gate (15% sampling) | `extract`, `verdict` |
| `tools/data_validator.py` | Dual-source cross-validation | `validate`, `batch` |
| `tools/stock_screener.py` | L1 momentum + L2 quality screening | `screen`, `grade` |
| `tools/ashare_data.py` | A-share real-time data MCP wrapper | `quote`, `financials`, `valuation`, `search` |
| `tools/perilla_scorer.py` | Perilla five-factor bottleneck scoring | `--theme`, `--output` |
| `tools/industry_chain.py` | Industry chain mapping | `--theme`, `--output` |

---

## Test Coverage

| Layer | Tests | Status |
|-------|-------|--------|
| Agent | 5 | ✅ 5/5 |
| Tools | 10 | ✅ 10/10 |
| End-to-end | 5 | ✅ 5/5 |
| Existing penetration+protection | 37 | ✅ 37/37 |
| **Total** | **57** | **✅ All Green** |

Run tests:

```bash
# Agent layer
python .claude/skills/fund-selector/tests/agents/test_agents_v2.py

# Tool layer
python .claude/skills/fund-selector/tests/tools/test_tools.py

# Perilla
python .claude/skills/theme-perilla/scripts/perilla_scorer.py --theme AI算力
python .claude/skills/theme-perilla/scripts/industry_chain.py --theme AI算力
```

---

## Data Sources

| Server | Tools | Purpose |
|--------|-------|---------|
| cn-financial | 42 | A-share quotes/financials/macro/industry |
| cn-mutual-fund | ~20 | Fund info/NAV/managers/holdings |

---

## Iron Rules

1. **Penetration anti-overlap**: Top-3 funds in recommended portfolio must have ≤15% sector overlap
2. **Budget hard constraint**: DCA amount ≤ monthly net savings
3. **Fee transparency**: Every recommendation discloses full fee structure
4. **Common-sense validation**: Flag anomalous PE/PB values
5. **Financial pre-check**: Discourage investment if no emergency fund or high-interest debt
6. **Rebalancing mechanism**: Quarterly review + trigger at >10% deviation
7. **Dual-source data**: Key data points cross-validated from 2+ sources
8. **Report audit**: 15% random sampling verification

---

## Perilla Theory

> **Source**: Serenity股神 (Bilibili UP主 "一羽禅心的鹤")
> **Video**: [BV1fT7z6QE2S](https://www.bilibili.com/video/BV1fT7z6QE2S) — "Perilla Theory: Lesson 1 — Foundations & Investment Framework"
> **Core thesis**: Don't chase AI giants (tuna belly); find overlooked "bottleneck nodes" (perilla leaf).

### Three-Layer Framework

| Layer | Name | Content |
|-------|------|---------|
| Strategic core | Bottleneck-point investing | Find irreplaceable nodes in industry chains |
| Tactical engine | Human-machine collaborative research + Bayesian updating | AI-assisted research with dynamic belief revision |
| Execution sieve | Five-factor model | Quantitative screening criteria |

### Five-Factor Scoring

| # | Factor | Criterion | Points |
|---|--------|-----------|--------|
| 1 | Niche market share | Top 3 in segment | 3 |
| 2 | Gross margin | > 30% | 3 |
| 3 | Institutional holding | < 10% (overlooked) | 3 |
| 4 | Technical moat | Hard to replicate | 3 |
| 5 | Capacity constraint | Low supply elasticity | 3 |

**Rating**:
- **≥ 12/15**: Perilla-grade (strategic scarcity) → Strong recommend
- **9-11/15**: Potential bottleneck → Watch
- **< 9/15**: Ordinary holding → Hold off

### Core Metaphor

| Metaphor | Meaning | Investment Logic |
|----------|---------|------------------|
| **Tuna belly** | Everyone's AI giants (Nvidia/Microsoft/Google) | Value fully priced in, no excess return |
| **Perilla leaf** | Micro-cap, overlooked, but strategically scarce | Once discovered, explosive upside |

---

## Inspirations & Evolution

> This section records how the design inspirations from external projects evolved into our original implementation tailored for A-share mutual funds.

### Starting Points: Two Projects That Inspired Us

**1. [ai-berkshire](https://github.com/xbtlin/ai-berkshire) (MIT License)**

An AI Agent framework for individual-stock value investing. We built upon its three-layer architecture but made **directional adjustments**:

| ai-berkshire Original | Our Adjustments |
|----------------------|----------------|
| Global individual stocks (US/HK/CN stocks) | Focus on **A-share mutual funds** (equity/bond/money/QDII) |
| 4-master-perspective Agent parallel reasoning | **Dual Agent (offense/defense)** + fast-rejection checklist |
| Web-scraped data (Yahoo/Morningstar/Snowball) | **MCP real-time data interfaces** (cn-financial/cn-mutual-fund) |
| 19 skills focused on stock research | 20 skills focused on **fund screening + portfolio management + DCA execution** |

**Key difference**: ai-berkshire is a "stock-picking framework"; ours is a "fund-picking framework." We kept the three-layer soul but swapped data sources and scenario fit.

**2. [Serenity股神](https://www.bilibili.com/video/BV1fT7z6QE2S) — Perilla Theory**

A methodology about "bottleneck-node investing." We transplanted its core idea **from stock research to fund penetration analysis**:

| Perilla Theory Original | Our Implementation |
|------------------------|-------------------|
| Find small-cap bottleneck companies in AI supply chains | Drill into fund underlying holdings, evaluate **holding quality** |
| Five-factor scoring for individual stocks | Five-factor scoring for fund penetration → **Perilla Index** |
| Focus on "tuna belly vs perilla leaf" valuation gap | Focus on **whether a fund's underlying holds overlooked bottleneck enterprises** |

### Tool-Level Borrowing & Rewriting

Some open-source tool design ideas were reused but **rewritten for fund scenarios**:

| Original Tool | Our Counterpart | Rewrite Notes |
|--------------|-----------------|---------------|
| `financial_rigor.py` (ai-berkshire) | `tools/financial_rigor.py` | Kept Decimal precision thought, **rewrote for fund scenarios** (scale/fees/VaR) |
| Rejection-list mechanism | 6 red lines → expanded to **8 iron rules** | Added fund-specific constraints: fee penetration, budget hard balance, rebalancing |
| Report audit concept | `tools/report_audit.py` | Kept 15% sampling thought, **rewrote for fund report format** |

### Our Original Contributions

**1. Information-richness grading (A/B/C)**

Inspired by ai-berkshire's data-quality thinking, extended for fund-specific use:
- Grade A: Scale + manager + NAV, all 3 sources available
- Grade B: Missing 1 source
- Grade C: Missing 2+ sources, flagged "insufficient data, evaluate cautiously"

**2. Fast-rejection checklist (8 red lines)**

Extended from ai-berkshire's 8 red lines with fund-specific additions:
- Max drawdown breach (equity class -35%)
- Scale < ¥200M (liquidity risk)
- Excessive fee warning line
- Manager tenure < 1 year

**3. Perilla Index**

An original metric quantifying a fund's "underlying bottleneck quality":
```
Perilla Index = avg(perilla score of top holdings) × holding concentration
```

**4. Dual Agent adversarial + conflict detection**

Simplified ai-berkshire's 4-Agent architecture to dual Agent (offense/defense), adding conflict detection:
- Star gap ≥2 → flagged "perspective divergence"
- Rank gap ≥3 → flag specific conflict

### Evolution Roadmap

```
Phase 1 (Complete): Foundation
  Port ai-berkshire three-layer architecture → adapt for A-share fund scenario
  
Phase 2 (Complete): Anti-bias tools
  Port financial_rigor.py precision tools → rewrite for fund scenarios
  
Phase 3 (Complete): Fast-rejection
  Borrow ai-berkshire rejection checklist → expand to 8 fund iron rules
  
Phase 4 (Complete): Perilla penetration
  Borrow Serenity perilla bottleneck theory → create Perilla Index + penetration analysis
  
Phase 5 (In Progress): Automated testing
  64 test cases cover full pipeline (see "Test Coverage" section)
```

### Acknowledgments

> Thanks to the following projects and creators for inspiration:
> 
> - [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire) — three-layer architecture philosophy, Decimal precision tools, rejection-checklist mechanism
> - [Serenity股神](https://www.bilibili.com/video/BV1fT7z6QE2S) — perilla bottleneck-node investing methodology
>
> This project deeply adapts and originally extends their work for the A-share mutual fund scenario; all code is independently implemented.

---

## Disclaimer

This project is for learning and research purposes only and does not constitute investment advice. Invest at your own risk. Always conduct your own due diligence (DYOR).

---

## License

MIT License

---

> "The best investment you can make is in yourself." — Warren Buffett
>
> Fund Selector: Giving everyone their own fund research team.
