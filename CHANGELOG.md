# Changelog — Fund Selector v2.0

> 2026-07-06 — 基于 ai-berkshire (MIT) 三层架构哲学完整重构

---

## 🏗️ 架构升级（Phase 1-4）

### Skill 层 — 19 个场景入口

**新增（13 个）**：
- `/fund-deep-research` — 基金深度研究（穿透+六关评分+镜子测试）
- `/manager-deep-dive` — 基金经理深度画像
- `/private-fund-research` — 私募/非公开基金研究
- `/fund-series` — 8 篇系列研报（~120k 字）
- `/fund-earnings-review` — 季报/年报解读
- `/fund-earnings-team` — 多视角财报解读团队
- `/industry-research` — 行业产业链研究
- `/industry-funnel` — 全市场漏斗筛选（30-60→≤10→3）
- `/quality-screen` — 质量排除筛选（7 硬规则+3 豁免）
- `/bottleneck-hunter` — 供应链瓶颈套利
- `/fund-checklist` — 买入前 6 关检查清单
- `/portfolio-review` — 持仓组合管理
- `/news-pulse` — 快讯多源归因（4 并行 Agent）

**重构（6 个，从 6→19）**：
- `/fund-team`（原 fund-recommend 团队型）→ 4 大师对抗式
- `/thesis-tracker` — 买入后追踪
- `/thesis-drift` — 投资逻辑漂移检测
- `/fund-ask` — 大师问答模拟（巴菲特/段永平/芒格/李录）
- `/financial-data` — 双源数据交叉验证
- `/fund-article` — 研报写作工厂（3 Agent）

---

### Agent 层 — Team Lead + 4 大师视角

**新增文件（5 个）**：

| 文件 | 功能 | 行数 |
|------|------|------|
| `agents/team_lead.py` | 读取 step3 → 生成 4 视角 prompt | ~170 |
| `agents/synthesize.py` | 合并 4 视角 + 冲突检测 | ~130 |
| `agents/editor_agent.py` | 公众号风格润色 | ~80 |
| `agents/reviewer_agent.py` | 读者视角审阅 | ~90 |
| `tests/agents/test_agents_v2.py` | 3 个单元测试 | ~140 |

**4 大师视角**：

| Agent | 视角 | 评分维度 |
|-------|------|---------|
| 价值 Agent | 巴菲特 | 规模/费率/经理稳定性 |
| 成长 Agent | 段永平 | 收益/动量/赛道景气 |
| 风控 Agent | 李录 | 回撤/波动/极端亏损 |
| 周期 Agent | 芒格 | 行业周期+逆向思考 |

**冲突检测**：星级差 ≥2 或排名差 ≥3 自动标注

---

### 工具层 — 5 个工具

**新增文件（6 个）**：

| 文件 | 功能 | 子命令 |
|------|------|--------|
| `tools/financial_rigor.py` | Decimal 精度验算 | 7 个子命令 |
| `tools/report_audit.py` | 15% 随机抽样审计 | `extract`, `verdict` |
| `tools/data_validator.py` | 双源交叉验证 | `validate`, `batch` |
| `tools/stock_screener.py` | L1 动量+L2 质量筛选 | `screen`, `grade` |
| `tools/ashare_data.py` | A 股实时数据 MCP 封装 | `quote`, `financials`, `valuation`, `search` |
| `tests/tools/test_tools.py` | 10 个单元测试 | — |

---

## 🧪 测试

| 层级 | 测试数 | 状态 |
|------|--------|------|
| Agent 层 | 3 | ✅ 3/3 |
| 工具层 | 10 | ✅ 10/10 |
| 既有穿透+防护 | 31 | ✅ 31/31 |
| **合计** | **44** | **✅ 全绿** |

---

## 🔧 修复

| 问题 | 严重度 | 修复 |
|------|--------|------|
| 报告不从 step3 读取排除列表（D2 失效）| 高 | generate_recommend 消费 validated_funds |
| step4 VaR 嵌套读取失败（显示 N/A）| 高 | 解包嵌套 var_impacts |
| 镜子测试百分比格式错误（+6203%）| 中 | `:.1%` → `:.1f}%` |
| return_3y=None 标签重复"近1年" | 低 | 改为"成立以来(X年X月)"|

---

## 📁 目录结构

```
.claude/skills/fund-selector/
├── SKILL.md                  # 主索引（路由表 + 架构）
├── ARCHITECTURE.md           # 架构说明文档（新增）
├── skills/                   # 19 个 skill 定义
├── agents/                   # Agent 层（4 个脚本 + 测试）
├── tools/                    # 工具层（5 个工具 + 测试）
└── tests/                    # 测试（agents/ + tools/）
```

---

## 🔄 Git Commits

```
e8f2568  @test: Phase4集成测试——多Agent端到端通过+回归验证既有流程无损
de39777  @feat: 工具层——5个工具+10/10测试全绿
3d0dd7e  @feat: Agent层——TeamLead+4大师视角+综合器，3/3测试全绿
470efa6  @feat: Skill层骨架——19个场景入口(5深度+2财报+5行业+4持仓+3思维)
b34c6da  @fix: 修复VaR嵌套读取+镜子测试百分比+成立以来标签
25a06e3  @fix: generate_recommend消费step3 validated_funds，修复D2回撤过滤穿透
```

---

## 📊 对比 v1.0 → v2.0

| 维度 | v1.0 | v2.0 |
|------|------|------|
| Skill 入口 | 6 | **19** |
| Agent | 单 Agent + 快否决 | **4 大师视角 + 综合器 + 冲突检测** |
| 工具 | 5（无审计/验证）| **5（精度+审计+验证+筛选+行情）** |
| 测试 | 31 | **44** |
| 买入后追踪 | ❌ | ✅ |
| 报告审计 | ❌ | ✅ |

---

*Changelog 格式基于 [Keep a Changelog](https://keepachangelog.com/)*
