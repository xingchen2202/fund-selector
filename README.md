# Fund Selector — A 股公募基金投研助手

> "一个人 + Claude Code = 一个投研团队。"

**Fund Selector v2.0** 是一套基于三层架构哲学的 A 股公募基金投研 Skill 合集，将价值投资的对抗式多视角方法论与 AI Agent 结合，覆盖深度研究、财报分析、行业筛选、持仓管理、思维工具五大场景。

基于 Claude Code + MCP（cn-financial / cn-mutual-fund）实时数据，**44 个自动化测试全绿**，保证每份报告的数据严谨性可验证。

[为什么不能直接问 AI](#为什么不能直接问-ai) · [Skills 一览（20 个）](#skills-一览20个) · [快速开始](#快速开始) · [架构设计](#架构设计) · [测试覆盖](#测试覆盖) · [紫苏叶理论](#紫苏叶理论)

---

## 为什么不能直接问 AI？

你可以直接问 Claude："帮我分析一下中欧新趋势混合基金"。你会得到一篇"一方面...另一方面..."的平衡分析，最后以"投资有风险，请自行判断"收尾。

**这种分析看起来对，但没法拿来做决策。**

Fund Selector 解决的不是"能不能分析"的问题，而是**分析质量和决策纪律**的问题。

### 1. 强制给结论，不打太极

直接问 AI，你得到的是两面讨好的"分析"。Fund Selector 强制输出：**推荐 / 观察 / 谨慎**，附带具体理由和风险分级。

> 普通 AI 回答：*"中欧新趋势混合基金业绩优秀，但近期回撤较大，投资者需要权衡..."*
>
> Fund Selector 输出：
>
> | 维度 | 结论 | 信心度 |
> |------|------|--------|
> | 财务质量 | 规模 28.93 亿，费率 1.5%，经理周蔚文 10 年+ | ★★★★★ |
> | 估值安全边际 | 近 1 年 +4.9%，回撤 -64.5%（突破阈值）| ⚠️ 高风险 |
> | 最大风险 | 权益类回撤超 -35% 阈值，触发 R3 一票否决 | ❌ 排除 |
>
> **快否决清单**：最大回撤 -64.5% < -35% → 直接否决，不进入推荐。

### 2. 双 Agent 对抗，而非单一分析

不是"用巴菲特方法分析一下"这么简单。两个视角会产生**真实的矛盾和张力**——

以候选基金池为例：
- **进攻 Agent**（成长视角）：南方电池 C +66.88%，动量强，电池赛道景气 → 评分 5 星
- **防守 Agent**（风控视角）：南方电池 C 回撤 -27.86%，波动率 12.1% → 评分 4 星

**进攻说"强"，防守说"有风险"**——这种冲突才是投资决策的真实状态。单一 prompt 无法制造这种多视角对抗，而这恰恰是避免盲点的关键。

### 3. 结构化反偏见机制

| 机制 | 解决什么问题 |
|------|------------|
| **信息丰富度分级（A/B/C）** | 防止"资料多=确定性高"的幻觉 |
| **快否决清单（6 条红线）** | 回撤 >35% / 诚信污点等直接否决 |
| **镜子测试（5 句话）** | 说不清逻辑 = 不买 |
| **反向测试** | "如果判断错了，最可能原因" |
| **六关评分（★1-5）** | 多维度量化，避免单一指标偏见 |

### 4. 金融数据的精确性

LLM 心算不可靠。PE 算错一个小数点、市值单位搞混，就可能导致错误的投资决策。

```bash
# 规模手算校验：份额 × 净值 vs 报告规模
python tools/financial_rigor.py verify-scale \
  --nav 1.0553 --shares 4.42e8 --reported 4.68e8
# ✅ 验证通过, 偏差仅 0.33%
```

所有计算使用 Python `decimal.Decimal`（精确十进制），不用 `float`。关键数据至少 2 个独立来源交叉验证。

### 5. 可复现的研究流程

直接问 AI，每次输出的格式、深度、覆盖面都不一样。Fund Selector 确保：**同样的输入 → 结构一致、深度一致的输出**。

### 6. 44 个自动化测试 = 质量底线

每个关键函数都有单元测试覆盖，重构和功能扩展有安全网。

```bash
# 运行全量测试
python .claude/skills/fund-selector/tests/agents/test_agents_v2.py
python .claude/skills/fund-selector/tests/tools/test_tools.py
# 结果：44/44 全绿 ✅
```

---

## 整体架构

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

## 参考借鉴

本项目在设计与实现过程中，参考并借鉴了以下开源项目与方法论：

### 核心架构参考

| 项目 | 借鉴内容 | 说明 |
|------|---------|------|
| [**ai-berkshire**](https://github.com/xbtlin/ai-berkshire) | 三层架构哲学 | Skill 层 / Agent 层 / Tool 层分层设计 |
| **ai-berkshire** | 4 大师视角对抗分析 | 巴菲特/段永平/芒格/李录的独立分析视角 |
| **ai-berkshire** | 信息丰富度分级（A/B/C）| 数据质量可信度评级机制 |
| **ai-berkshire** | 快速否决清单 | 8 条红线一票否决机制 |
| **ai-berkshire** | 三情景估值模型 | 乐观/中性/悲观估值方法 |
| **ai-berkshire** | 供应链瓶颈猎手 | 产业链隐形冠军套利思路 |
| [**Serenity股神**](https://www.bilibili.com/video/BV1fT7z6QE2S) | 紫苏叶理论 | 瓶颈节点投资法 + 五因子评分模型 |

### 工具与机制参考

| 借鉴来源 | 内容 | 本项目对应 |
|---------|------|-----------|
| **financial_rigor.py** (ai-berkshire) | Decimal 精确验算 | `tools/financial_rigor.py` |
| **investment-checklist** (ai-berkshire) | 6 关买入清单 | `skills/fund-checklist.md` |
| **quality-screen** (ai-berkshire) | 7 条硬规则筛选 | `skills/quality-screen.md` |
| **report_audit.py** (ai-berkshire) | 报告抽样审计 | `tools/report_audit.py` |
| **thesis-tracker** (ai-berkshire) | 买入后追踪 | `skills/thesis-tracker.md` |
| **news-pulse** (ai-berkshire) | 快讯归因架构 | `skills/news-pulse.md` |
| **Serenity股神** (Bilibili) | 紫苏叶五因子瓶颈评分 | `/theme-perilla` skill |

### 设计理念参考

- **对抗式多视角**：不依赖单一分析视角，通过独立 Agent 的冲突暴露盲点
- **数据双源验证**：关键数据点强制交叉验证，偏差 >1% 自动报警
- **先破后立**：先排除坏选择（快否决），再精选好标的
- **买入后纪律**：不止于推荐，更包含追踪与卖出机制

> 感谢 [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire) 与 [Serenity股神](https://www.bilibili.com/video/BV1fT7z6QE2S) 提供的方法论与工具设计灵感。

---

## 免责声明

本项目仅供学习和研究目的，不构成任何投资建议。投资有风险，决策需谨慎。请始终做好自己的尽职调查（DYOR）。

---

## License

MIT License

---

> "The best investment you can make is in yourself." — Warren Buffett
>
> Fund Selector：让每个人都拥有自己的基金投研团队。
