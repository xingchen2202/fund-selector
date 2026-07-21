---
name: fund-selector
description: >
  A 股公募基金投研助手（v2.0）。基于三层架构：Skill 层（19 个场景入口）、
  Agent 层（4 大师视角分析 + 风险否决）、工具层（精度计算+数据验证+报告审计+约束校验）。
  覆盖深度研究、财报分析、行业筛选、持仓管理、思维工具五大场景。
when_to_use: >
  用户问"买什么基金"、"XX 基金怎么样"、"推荐基金"、"持仓分析"、
  "行业研究"、"经理画像"、"该卖了吗"、"写篇研报"等。
disable-model-invocable: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily mcp__node_repl
effort: high
---

# Fund Selector v2.0 — A 股公募基金投研助手

三层架构设计（移植自 ai-berkshire 哲学）：
- **Skill 层**：19 个明确入口，按场景选用
- **Agent 层**：团队型 skill 由 Team Lead 调度 4 大师视角分析（文档驱动模式：生成 4 个视角 prompt，Claude 独立分析后综合研判 + 风险否决）
- **工具层**：精确计算、实时检索、报告抽检

---

## 路由表（用户意图 → Skill）

> 以下 19 个 skill 均为**独立注册**的 Claude Code skill，可通过 `/<skill-name>` 直接触发。

### 深度研究
| 触发词 | Skill | 类型 |
|--------|-------|------|
| XX 基金怎么样、深度研究、全面分析 | `/fund-deep-research` | 轻量 |
| 多角度分析、投研团队、深度覆盖 | `/fund-team` | 团队型 |
| XX 经理怎么样、经理画像、经理深度 | `/manager-deep-dive` | 轻量 |
| 私募研究、非公开基金、一级市场 | `/private-fund-research` | 轻量 |
| 系列研报、深度覆盖、XX 行业系列 | `/fund-series` | 团队型 |

### 财报分析
| 触发词 | Skill | 类型 |
|--------|-------|------|
| 季报解读、年报分析、业绩点评 | `/fund-earnings-review` | 轻量 |
| 多视角财报会、深度解读 | `/fund-earnings-team` | 团队型 |

### 行业筛选
| 触发词 | Skill | 类型 |
|--------|-------|------|
| XX 行业研究、产业链分析 | `/industry-research` | 轻量 |
| 全市场筛选、漏斗精选、批量筛选 | `/industry-funnel` | 轻量 |
| 质量筛选、排除坏基金、负面清单 | `/quality-screen` | 轻量 |
| 供应链瓶颈、隐形冠军、细分龙头 | `/bottleneck-hunter` | 轻量 |
| 买入前检查、投资清单、检查清单 | `/fund-checklist` | 轻量 |

### 持仓管理
| 触发词 | Skill | 类型 |
|--------|-------|------|
| 持仓分析、组合管理、仓位调整 | `/portfolio-review` | 轻量 |
| 买入后追踪、季度复盘、该加仓吗 | `/thesis-tracker` | 轻量 |
| 逻辑漂移、该卖了吗、持有理由变化 | `/thesis-drift` | 轻量 |
| 快讯解读、为什么涨跌、新闻归因 | `/news-pulse` | 团队型 |

### 思维工具
| 触发词 | Skill | 类型 |
|--------|-------|------|
| 问问巴菲特、段永平怎么看、大师观点 | `/fund-ask` | 轻量 |
| 数据验证、交叉核对、数据可信吗 | `/financial-data` | 轻量 |
| 写篇研报、公众号文章、投资笔记 | `/fund-article` | 团队型 |

---

## Agent 层（团队型 Skill 专用）

### 4 大师视角

| Agent | 视角 | 核心问题 |
|-------|------|---------|
| 价值 Agent | 巴菲特 | 持仓企业质地如何？有护城河吗？估值安全吗？ |
| 成长 Agent | 段永平 | 商业模式好吗？护城河宽吗？ |
| 风控 Agent | 李录 | 最大风险是什么？管理层可信吗？ |
| 周期 Agent | 芒格 | 行业格局如何？竞争态势怎样？ |

### 调度规则

```
用户触发团队型 skill
  → Team Lead 并行启动 4 个 Agent
  → 各自独立搜索 MCP 数据 + 独立判断
  → 4 视角结论汇总到 Team Lead
  → 冲突检测（排名差 ≥3 标注）
  → 综合研判 → 生成报告
  → 报告审计门（15% 抽样验证）
```

---

## 工具层

| 工具 | 用途 | 关键子命令 |
|------|------|-----------|
| `tools/financial_rigor.py` | Decimal 精度验算 | `verify-scale`, `verify-valuation`, `cross-validate`, `benford`, `calc`, `three-scenario` |
| `tools/report_audit.py` | 报告质量门 | `extract`, `verdict` |
| `tools/data_validator.py` | 双源交叉验证 | `validate`, `flag-deviation` |
| `tools/stock_screener.py` | 动量+质量筛选 | `screen`, `grade` |
| `tools/ashare_data.py` | A 股实时数据 | `quote`, `financials`, `valuation`, `search` |

---

## 运行模式

### 模式 A：轻量（14 个 skill）
用户意图 → 直连工具层 → 快速输出（秒级）

### 模式 B：团队（5 个 skill）
用户意图 → Team Lead → 4 Agent 并行 → 综合研判 → 审计报告（分钟级）

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
