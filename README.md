# Fund Selector — A 股公募基金投研助手

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**中文** | [English](README_EN.md)

> "一个人 + Claude Code = 一个投研团队。"

**Fund Selector v2.0** 是一套基于三层架构哲学的 A 股公募基金投研 Skill 合集，将价值投资的对抗式多视角方法论与 AI Agent 结合，覆盖深度研究、财报分析、行业筛选、持仓管理、思维工具五大场景。

基于 Claude Code + MCP（cn-financial / cn-mutual-fund）实时数据，**60 个自动化测试全绿**，保证每份报告的数据严谨性可验证。

[从 LLM 到投研助手](#从-llm-到投研助手) · [Skills 一览（20 个）](#skills-一览20个) · [快速开始](#快速开始) · [架构设计](#架构设计) · [测试覆盖](#测试覆盖) · [紫苏叶理论](#紫苏叶理论)

---

## 从 LLM 到投研助手

> 直接问 AI，你得到的是"看起来对的废话"。用 Fund Selector，你得到的是"可以拿来做决策的投研报告"。

我们用同一个问题测试：**"帮我分析中欧新趋势混合基金"**。

---

### 普通 LLM 的回答

```
中欧新趋势混合基金（166001）业绩优秀，成立以来收益可观。
近1年回报+4.9%，但最大回撤较大。基金经理周蔚文经验丰富。
总体来看，这只基金适合长期投资者，但需注意波动风险。
投资有风险，入市需谨慎。
```

**问题**：两面讨好、没有结论、没有数据校验、没有风险阈值、无法执行。

---

### Fund Selector 的回答

```
▌ 数据层
  规模：28.93 亿（校验：偏差 0.33% ✓）
  经理：周蔚文（任职 10 年+）| 总费率：1.5%
  近1年：+4.9% | 最大回撤：-64.5%

▌ 风险评估
  ⚠️ 最大回撤 -64.5% 突破 -35% 权益阈值
  → 触发快否决清单 R3：一票否决

▌ 结论：❌ 不推荐
  原因：回撤超标，不符合稳健型组合标准
```

**差异**：有数据校验、有风险阈值、有明确结论、有执行建议。

---

### 六个核心差异

**1. 用数据说话，而非模糊描述**

普通 LLM 说"业绩优秀"。我们用 MCP 实时获取净值、规模、费率，并做交叉验证：

```bash
# 规模验算：份额 × 净值 vs 报告规模
python tools/financial_rigor.py verify-scale \
  --nav 1.0553 --shares 4.42e8 --reported 4.68e8
# ✅ 验证通过, 偏差仅 0.33%
```

所有计算使用 `decimal.Decimal`（精确十进制），不用 `float`。

**2. 用规则护栏，而非自由发挥**

普通 LLM 没有风控阈值。我们内置 **8 条铁律**：

| 红线 | 触发条件 | 动作 |
|------|---------|------|
| 回撤超标 | 权益类最大回撤 < -35% | 一票否决 |
| 规模不足 | 基金规模 < 2 亿 | 排除 |
| 费率过高 | 总费率 > 2.5%/年 | 警告 |
| 经理任期 | 任职 < 1 年 | 排除 |
| 数据缺失 | 关键数据点 >2 源不可用 | 标注不可用 |

**3. 用对抗视角，而非单一分析**

普通 LLM 只有一个声音我们用**双 Agent 对抗 + 冲突检测**：

- **进攻 Agent**（成长视角）：南方电池 C +66.88%，动量强 → 5 星
- **防守 Agent**（风控视角）：南方电池 C 回撤 -27.86%，波动大 → 4 星
- **冲突检测**：星级差 ≥2 → 标注"视角分歧大，需深入讨论"

**4. 用穿透分析，而非表面指标**

普通 LLM 看基金净值。我们**穿透到底层持仓**：

- 基金买了哪些股票？
- 这些股票的毛利率、ROE、市占率如何？
- 是否是"瓶颈节点"（紫苏叶级）？

**5. 用历史纪律，而非每次重新发明**

普通 LLM 每次输出格式不同。我们确保：**同样的输入 → 结构一致的输出**。

**6. 用自动化测试，而非人工检查**

60 个测试用例覆盖全链路，重构有安全网。

```bash
python .claude/skills/fund-selector/tests/agents/test_agents_v2.py
python .claude/skills/fund-selector/tests/tools/test_tools.py
# 结果：60/60 全绿 ✅
```

---

## 整体架构

```text
┌─────────────────────────────── Skill 层 ───────────────────────────────┐
│   深度研究 · 财报分析 · 行业筛选 · 持仓管理 · 思维工具 · 主题瓶颈分析     │
│   （20 个 skill 入口：轻量 skill 直连工具；团队型 skill 经 Agent 层）    │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   ▼
┌─────────────────────────────── Agent 层 ───────────────────────────────┐
│                            Team Lead （调度）                          │
│     ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                    │
│     │ 进攻    │ │ 防守    │ │ 风控    │ │ 周期    │   ← 4 大师视角    │
│     │ 段永平  │ │ 巴菲特  │ │ 李录    │ │ 芒格    │                    │
│     └─────────┘ └─────────┘ └─────────┘ └─────────┘                    │
│                   冲突检测 + 综合研判 → 报告审计门                       │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   ▼
┌─────────────────────────────── 工具层 ─────────────────────────────────┐
│  financial_rigor.py · report_audit.py · data_validator.py              │
│  stock_screener.py   · ashare_data.py  · perilla_scorer.py             │
│                                            industry_chain.py           │
└────────────────────────────────────────────────────────────────────────┘
```

**三层设计哲学**：

- **Skill 层**：把"你要做什么"抽象成 20 个明确入口——深度研究、财报分析、行业筛选、持仓管理、思维工具、主题瓶颈分析，按场景选用
- **Agent 层**：团队型 skill（如 `/fund-team`、`/news-pulse`）由 Team Lead 并行调度 4 个大师视角 Agent——各自独立搜索、独立判断、互相挑战，最后综合研判；轻量 skill 不经过这一层，直连工具快进快出
- **工具层**：精确计算、实时检索、报告抽检——保证每份报告的数据严谨性可验证

---

## Skills 一览（20 个）

### 深度研究类（5 个）

| Skill | 用途 | 类型 | 触发词 |
|-------|------|------|--------|
| `/fund-deep-research` | 单基金深度研究（穿透+六关评分+镜子测试）| 轻量 | XX 基金怎么样、深度研究、全面分析 |
| `/fund-team` | 多 Agent 并行投研团队 | 团队型 | 多角度分析、投研团队、深度覆盖 |
| `/manager-deep-dive` | 基金经理深度画像 | 轻量 | XX 经理怎么样、经理画像、经理深度 |
| `/private-fund-research` | 私募/非公开基金研究 | 轻量 | 私募研究、非公开基金、一级市场 |
| `/fund-series` | 基金系列研报（8 篇）| 团队型 | 系列研报、深度覆盖、XX 行业系列 |

### 财报分析类（2 个）

| Skill | 用途 | 类型 | 触发词 |
|-------|------|------|--------|
| `/fund-earnings-review` | 季报/年报解读 | 轻量 | 季报解读、年报分析、业绩点评 |
| `/fund-earnings-team` | 多视角财报解读团队 | 团队型 | 多视角财报会、深度解读 |

### 行业筛选类（5 个）

| Skill | 用途 | 类型 | 触发词 |
|-------|------|------|--------|
| `/industry-research` | 行业产业链研究 | 轻量 | XX 行业研究、产业链分析 |
| `/industry-funnel` | 全市场漏斗筛选（30-60→≤10→3）| 轻量 | 全市场筛选、漏斗精选、批量筛选 |
| `/quality-screen` | 质量排除筛选（7 硬规则+3 豁免）| 轻量 | 质量筛选、排除坏基金、负面清单 |
| `/bottleneck-hunter` | 供应链瓶颈套利 | 轻量 | 供应链瓶颈、隐形冠军、细分龙头 |
| `/fund-checklist` | 买入前 6 关检查清单 | 轻量 | 买入前检查、投资清单、检查清单 |

### 持仓管理类（4 个）

| Skill | 用途 | 类型 | 触发词 |
|-------|------|------|--------|
| `/portfolio-review` | 持仓组合管理 | 轻量 | 持仓分析、组合管理、仓位调整 |
| `/thesis-tracker` | 买入后追踪（季度复盘）| 轻量 | 买入后追踪、季度复盘、该加仓吗 |
| `/thesis-drift` | 投资逻辑漂移检测 | 轻量 | 逻辑漂移、该卖了吗、持有理由变化 |
| `/news-pulse` | 快讯多源归因（10 分钟响应）| 团队型 | 快讯解读、为什么涨跌、新闻归因 |

### 思维工具类（3 个）

| Skill | 用途 | 类型 | 触发词 |
|-------|------|------|--------|
| `/fund-ask` | 大师问答模拟（巴菲特/段永平/芒格/李录）| 轻量 | 问问巴菲特、段永平怎么看、大师观点 |
| `/financial-data` | 双源数据交叉验证 | 轻量 | 数据验证、交叉核对、数据可信吗 |
| `/fund-article` | 研报写作工厂 | 团队型 | 写篇研报、公众号文章、投资笔记 |

### 主题瓶颈分析类（1 个）

| Skill | 用途 | 类型 | 触发词 |
|-------|------|------|--------|
| `/theme-perilla` | 紫苏叶主题瓶颈分析 | 轻量 | 紫苏叶分析 XX、XX 产业链瓶颈、AI 瓶颈节点 |

---

## 快速开始

### 1. 环境要求

- Claude Code：`npm install -g @anthropic-ai/claude-code`
- Python >= 3.7（仅 stdlib，无需 pip install）
- MCP 服务器：cn-financial + cn-mutual-fund（已配置于 `.mcp.json`）

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/xingchen2202/fund-selector
cd fund-selector

# 验证 MCP 连接
# 在 Claude Code 中运行：
# > /mcp
# 确认 cn-financial 和 cn-mutual-fund 状态为 ✓ connected
```

### 3. 使用

```bash
# 深度研究
/fund-deep-research 中欧新趋势混合
/fund-team 国泰有色矿业

# 行业筛选
/industry-funnel 电池
/quality-screen 沪深300成分股
/fund-checklist 易方达蓝筹, 中欧医疗, 招商白酒

# 持仓管理
/portfolio-review
/thesis-tracker 001198
/news-pulse 018167

# 思维工具
/fund-ask 红利低波策略现在还能买吗？
/financial-data 中欧新趋势混合 规模
/fund-article 电池行业

# 紫苏叶主题瓶颈分析
/theme-perilla AI算力
/theme-perilla 新能源
/theme-perilla 半导体
```

---

## Agent 层（团队型 Skill 专用）

### 4 大师视角

| Agent | 视角 | 核心问题 |
|-------|------|---------|
| 进攻 Agent | 段永平 | 成长性、动量、赛道景气 |
| 防守 Agent | 巴菲特 | 回撤、波动、规模费率 |
| 风控 Agent | 李录 | 最大风险、极端亏损 |
| 周期 Agent | 芒格 | 行业格局、竞争态势 |

### 调度流程

```
用户触发团队型 skill
  → Team Lead 并行启动 4 个 Agent
  → 各自独立 MCP 搜索 + 独立判断
  → 4 视角结论汇总到 Team Lead
  → 冲突检测（星级差 ≥2 或排名差 ≥3）
  → 综合研判 → 生成报告
  → 报告审计门（15% 抽样验证）
```

---

## 工具层

| 工具 | 用途 | 关键子命令 |
|------|------|-----------|
| `tools/financial_rigor.py` | Decimal 精度验算 | `verify-scale`, `verify-valuation`, `cross-validate`, `benford`, `calc`, `three-scenario` |
| `tools/report_audit.py` | 报告质量门（15% 抽样）| `extract`, `verdict` |
| `tools/data_validator.py` | 双源交叉验证 | `validate`, `batch` |
| `tools/stock_screener.py` | L1 动量+L2 质量筛选 | `screen`, `grade` |
| `tools/ashare_data.py` | A 股实时数据 MCP 封装 | `quote`, `financials`, `valuation`, `search` |
| `tools/perilla_scorer.py` | 紫苏叶五因子瓶颈评分 | `--theme`, `--output` |
| `tools/industry_chain.py` | 产业链图谱构建 | `--theme`, `--output` |

---

## 紫苏叶理论

<details><summary>展开紫苏叶理论</summary>

> **来源**：Serenity股神（Bilibili UP主"一羽禅心的鹤"）
> **视频**：[BV1fT7z6QE2S](https://www.bilibili.com/video/BV1fT7z6QE2S) — "紫苏叶理论：第1讲 基础与投资框架"
> **核心理念**：不追 AI 巨头（金枪鱼大腹），寻找被忽视的"瓶颈节点"（紫苏叶）。

### 三层架构

| 层级 | 名称 | 内容 |
|------|------|------|
| 战略核心 | 瓶颈点投资法 | 寻找产业链中不可替代的关键节点 |
| 战术引擎 | 人机协同研究 + 贝叶斯更新 | AI 辅助研究，动态修正判断 |
| 执行筛子 | 五因子模型 | 量化筛选标准 |

### 五因子瓶颈评分模型

| # | 因子 | 标准 | 分值 | 说明 |
|---|------|------|------|------|
| 1 | 细分市占率 | 行业前3 | 3分 | 在细分领域有主导地位 |
| 2 | 毛利率 | > 30% | 3分 | 有定价权，盈利能力强 |
| 3 | 机构持仓 | < 10% | 3分 | 被市场忽视，有发现空间 |
| 4 | 技术壁垒 | 难以替代 | 3分 | 有专利/认证/技术门槛 |
| 5 | 产能约束 | 供给弹性低 | 3分 | 产能紧张，新进入者难 |

**评级标准**：
- **≥ 12/15**：紫苏叶级（战略稀缺）→ 强烈推荐
- **9-11/15**：潜在瓶颈 → 关注
- **< 9/15**：普通持仓 → 观望

### 核心比喻

| 比喻 | 含义 | 投资逻辑 |
|------|------|---------|
| **金枪鱼大腹** | 人人追捧的 AI 巨头（英伟达/微软/谷歌）| 价值已充分定价，无超额收益 |
| **紫苏叶** | 微型市值、被忽视、但战略稀缺的小公司 | 一旦被发现，弹性巨大 |

### 的工作流程

```
1. 输入热门主题（如 "AI算力"）
   ↓
2. 构建产业链图谱（上游/中游/下游）
   ↓
3. 发现各环节上市公司
   ↓
4. 对每只股票五因子评分
   ↓
5. 筛选瓶颈节点（≥12分）
   ↓
6. 关联基金发现（重仓瓶颈股的基金）
   ↓
7. 输出报告（瓶颈地图 + 基金/股票推荐）
```

### 产业链参考

| 主题 | 参考文件 |
|------|---------|
| AI 算力 | `references/industry-chains/ai-computing.md` |
| 新能源 | `references/industry-chains/new-energy.md` |
| 半导体 | `references/industry-chains/semiconductor.md` |

</details>

---

## 测试覆盖

| 层级 | 测试数 | 状态 |
|------|--------|------|
| Agent 层 | 3 | ✅ 3/3 |
| 工具层 | 10 | ✅ 10/10 |
| 紫苏叶 | 16 | ✅ 16/16 |
| 既有穿透+防护 | 31 | ✅ 31/31 |
| **合计** | **60** | **✅ 全绿** |

运行测试：

```bash
# Agent 层
python .claude/skills/fund-selector/tests/agents/test_agents_v2.py

# 工具层
python .claude/skills/fund-selector/tests/tools/test_tools.py

# 紫苏叶
python .claude/skills/theme-perilla/scripts/perilla_scorer.py --theme AI算力
python .claude/skills/theme-perilla/scripts/industry_chain.py --theme AI算力
```

---

## 数据源

| 服务器 | 工具数 | 用途 |
|--------|--------|------|
| cn-financial | 42 | A 股行情/财报/宏观/行业 |
| cn-mutual-fund | ~20 | 基金信息/净值/经理/持仓 |

---

## 约束（铁律）

1. **穿透防重叠**：推荐组合前三基金行业重合度 ≤15%
2. **预算硬平衡**：定投金额 ≤ 月净储蓄额
3. **费率穿透**：每次推荐披露完整费率
4. **常识校验**：PE/PB 异常值标注
5. **财务预检**：无应急金/高息负债先劝阻
6. **再平衡机制**：季度回顾 + 偏离 >10% 触发
7. **数据双源**：关键数据点强制交叉验证
8. **报告审计**：15% 随机抽样验证

---

## 目录结构

```
.claude/skills/
├── fund-selector/                    # 基金筛选主 skill（19 个子 skill）
│   ├── SKILL.md
│   ├── ARCHITECTURE.md
│   ├── skills/                       # 19 个 skill 定义
│   ├── agents/                       # Agent 层
│   ├── tools/                        # 工具层
│   └── tests/                        # 测试
├── theme-perilla/                    # 紫苏叶主题瓶颈分析（独立 skill）
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── perilla_scorer.py
│   │   └── industry_chain.py
│   ├── references/
│   │   ├── perilla-framework.md
│   │   └── industry-chains/
│   ├── evals/
│   │   └── evals.json
│   └── reports/
│       └── report-template.md
└── _shared/                          # 共享知识库
    ├── perilla-framework.md
    └── ...
```

---

## 灵感来源与演进

> 本章记录本项目的设计灵感如何从外部项目的启发，演进为适合 A 股公募基金场景的原创实现。

### 起点：两个项目的启发

本项目的早期设计受益于以下两个项目的启发：

**1. [ai-berkshire](https://github.com/xbtlin/ai-berkshire)（MIT License）**

这是一个面向个股价值投资的 AI Agent 框架。我们在其三层架构（Skill/Agent/Tool）的基础上，做了以下**方向性调整**：

| ai-berkshire 原版 | 本项目的调整 |
|------------------|-------------|
| 面向全球个股（美股/港股/A 股个股）| 聚焦 **A 股公募基金**（股/债/货币/QDII 全覆盖）|
| 4 大师视角 Agent 并行推理 | 改为 **进攻/防守双 Agent** + 快否决清单 |
| 网页爬取数据（Yahoo/Morningstar/雪球）| 改用 **MCP 实时数据接口**（cn-financial/cn-mutual-fund）|
| 19 个 skill 侧重个股研究 | 20 个 skill 侧重 **基金筛选 + 组合管理 + 定投执行** |

**关键差异**：ai-berkshire 是"选股框架"，本项目是"选基金框架"。我们保留了三层架构的灵魂，但替换了数据源和场景适配。

**2. [Serenity股神](https://www.bilibili.com/video/BV1fT7z6QE2S) — 紫苏叶理论**

这是一个关于"瓶颈节点投资"的方法论。我们将其核心思想**从个股研究移植到基金穿透分析**：

| 紫苏叶理论原版 | 本项目的实现 |
|--------------|-------------|
| 寻找 AI 供应链中小市值瓶颈公司 | 穿透基金底层持仓，评估 **持仓股质量** |
| 五因子评分筛选个股 | 五因子评分穿透基金 → **紫苏叶指数** |
| 关注"金枪鱼大腹 vs 紫苏叶"的估值差异 | 关注 **基金底层是否持有被忽视的瓶颈企业** |

### 工具层面的借鉴与改写

本项目复用了部分开源工具的设计思路，但做了**场景适配和代码重写**：

| 原始工具 | 本项目对应 | 改写说明 |
|---------|-----------|---------|
| `financial_rigor.py`（ai-berkshire）| `tools/financial_rigor.py` | 保留 Decimal 精度思想，**重写为基金场景**（规模/费率/VaR 计算）|
| 否决清单机制 | 6 条红线 → 扩展为 **8 条铁律** | 增加费率穿透、预算硬平衡、再平衡机制等基金特有约束 |
| 报告审计思路 | `tools/report_audit.py` | 保留 15% 抽样思想，**重写为基金报告格式** |

### 我们的原创贡献

本项目在借鉴基础上，加入了以下**原创设计**：

**1. 信息丰富度分级（A/B/C）**

借鉴 ai-berkshire 的数据质量思想，但扩展为基金专用：
- A 级：规模 + 经理 + 净值三源齐全
- B 级：缺 1 源
- C 级：缺 2 源以上，标注"数据不足谨慎评估"

**2. 快否决清单（8 条红线）**

在 ai-berkshire 的 8 条红线基础上，增加基金特有约束：
- 最大回撤突破阈值（权益类 -35%）
- 规模 < 2 亿（流动性风险）
- 费率过高警告线
- 基金经理任职 < 1 年

**3. 紫苏叶指数**

原创指标，用于量化基金的"底层持仓瓶颈质量"：
```
紫苏叶指数 = 重仓股平均五因子得分 × 持仓集中度
```

**4. 双 Agent 对抗 + 冲突检测**

简化 ai-berkshire 的 4 Agent 架构为双 Agent（进攻/防守），增加冲突检测机制：
- 星级差 ≥ 2 → 标注"视角分歧大"
- 排名差 ≥ 3 → 标注具体冲突

### 演进路线图

```
Phase 1（已完成）: 基础架构
  移植 ai-berkshire 三层架构 → 适配 A 股基金场景
  
Phase 2（已完成）: 防偏差工具
  移植 financial_rigor.py 精度工具 → 重写为基金场景
  
Phase 3（已完成）: 快否决机制
  借鉴 ai-berkshire 否决清单 → 扩展为 8 条基金铁律
  
Phase 4（已完成）: 紫苏叶穿透
  借鉴 Serenity股神瓶颈理论 → 创建紫苏叶指数 + 穿透分析
  
Phase 5（进行中）: 自动化测试
  60 个测试用例覆盖全链路
```

### 致谢

> 感谢以下项目与创作者提供的灵感：
> 
> - [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire) — 三层架构哲学、Decimal 精度工具、否决清单机制的设计灵感
> - [Serenity股神](https://www.bilibili.com/video/BV1fT7z6QE2S) — 紫苏叶瓶颈节点投资方法论
>
> 本项目在其基础上针对 A 股公募基金场景做了深度适配与原创扩展，所有代码均为独立实现。

---

## 免责声明

本项目仅供学习和研究目的，不构成任何投资建议。投资有风险，决策需谨慎。请始终做好自己的尽职调查（DYOR）。

---

## 贡献指南

欢迎社区参与：如有任何想法或改进，欢迎提交 Issue 或 Pull Request 与我们讨论。

以下四类反馈尤为宝贵：**Bug 报告**（行为与文档不符）、**性能优化**（运行效率与资源占用）、**测试用例**（补充边界场景覆盖）、**新功能**（新 skill 与新工具）。

提交前请确保已跑完整 **60 个测试用例**（`tests/agents/test_agents_v2.py`、`tests/tools/test_tools.py` 等），并确认全绿，以免破坏现有回归安全网。

---

## License

MIT License

---

> "The best investment you can make is in yourself." — Warren Buffett
>
> Fund Selector：让每个人都拥有自己的基金投研团队。

---

## 自检清单

- [x] 4 处新增均已插入
  - 新增 1（ASCII Architecture 图）：插入在 `## 整体架构` 与 `**三层设计哲学**` 之间，图下保留原三层设计哲学说明
  - 新增 2（CONTRIBUTING 段落）：插入在 `---` 分割线与 `## License` 之间，新增 `## 贡献指南` 段落（仓库无 CONTRIBUTING.md 文件，故未加链接）
  - 新增 3（License badge 行）：插入在第一行标题 `# Fund Selector — A 股公募基金投研助手` 正下方
  - 新增 4（紫苏叶折叠标记）：`## 紫苏叶理论` 标题后加 `<details><summary>展开紫苏叶理论</summary>`，正文末（产业链参考表后）加 `</details>`，内所有子章节/表格/工作流保留
- [x] 字数变化估计：增加约 380 字（ASCII 图约 200 字 + badge 行约 10 字 + 贡献指南段落约 120 字 + 折叠标记约 10 字），保留原文全部内容
- [x] 原有序列 / 章节顺序未变（从 LLM 到投研助手 → 整体架构 → Skills 一览 → 快速开始 → Agent 层 → 工具层 → 紫苏叶理论 → 测试覆盖 → 数据源 → 约束 → 目录结构 → 灵感来源与演进 → 免责声明 → 贡献指南 → License）
- [x] 原有 markdown 格式未破坏（表格、代码块、列表、链接均保持原样）
- [x] 已读 SKILL.md 子目录（`.claude/skills/fund-selector` 含 SKILL.md、ARCHITECTURE.md、agents、evals、reports、skills、tests、tools），确认新增不与真实文件冲突；CONTRIBUTING.md 不存在（已验证 404），故贡献指南未加外部链接

## 待确认

无冲突。4 处新增均未与原有章节产生重复或冲突。
