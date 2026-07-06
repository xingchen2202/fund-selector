# Fund Selector v2.0 — Skill 审计报告

> 审计日期：2026-07-06 | 审计范围：`.claude/skills/fund-selector/`

---

## 📊 总览

| 维度 | 状态 | 说明 |
|------|------|------|
| Skill 入口 | ⚠️ 需修复 | 19 个声明，路由表有 5 个错误路径 |
| 实现完整性 | ❌ 严重缺失 | 全部 19 个 skill 仅有文档，无 backing script |
| 测试覆盖 | ❌ 严重缺失 | 19 个 skill 全部零测试（仅底层工具/agent 有测试）|
| 安全 | ✅ 通过 | 无敏感信息泄露 |
| Agent 层 | ⚠️ 不完整 | 缺少 4 个大师视角 Agent |
| 工具层 | ✅ 完整 | 5 工具 + 10 tests |

---

## 🔴 严重问题（必须修复）

### S1：全部 19 个 skill 零测试

**现状**：`tests/` 仅覆盖底层工具（10 tests）和 agent 基础设施（3 tests），19 个 skill 工作流本身完全无测试。

**风险**：skill 行为无法验证，重构或扩展时无安全网。

**修复建议**：为每个 skill 添加 eval 断言文件 `evals/evals.json`，至少覆盖：
- 触发词是否正确路由
- 输出是否包含必要段落
- MCP 失败时是否优雅降级

### S2：全部 19 个 skill 仅有文档，无 backing script

**现状**：所有 `skills/*.md` 是纯 Markdown 文档，没有对应的 Python 脚本实现。当用户触发 skill 时，Claude 需要从零开始理解文档并执行整个流程。

**风险**：
- 每次执行路径不一致（文档 → Claude 自由推理 → 输出）
- 无法保证输出格式统一
- 复杂流程（如 4 Agent 并行）容易遗漏步骤

**修复建议**：为高频/复杂 skill 添加 backing script：
- `scripts/fund_team.py` — 封装 Team Lead → 4 Agent → Synthesize 流程
- `scripts/fund_deep_research.py` — 封装穿透分析 + 六关评分
- `scripts/industry_funnel.py` — 封装漏斗筛选

### S3：路由表有 5 个错误路径

**现状**：SKILL.md 路由表被 grep 误提取出不存在路径：`/ashare`, `/data`, `/financial`, `/report`, `/stock`。

**风险**：用户或 Claude 尝试触发这些路径时会失败。

**修复建议**：清理路由表，只保留真实存在的 19 个 skill 路径。

---

## 🟡 高度问题（建议修复）

### H1：缺少 4 个大师视角 Agent

**现状**：`agents/` 只有 `team_lead.py` + `synthesize.py` + `editor_agent.py` + `reviewer_agent.py`。SKILL.md 声明的 4 个大师视角（价值/成长/风控/周期）没有对应实现。

**风险**：`/fund-team` 无法真正并行 4 个视角，退化为单 Agent。

**修复建议**：
- 方案 A：在 `team_lead.py` 中生成 4 个 prompt，由 Claude 通过 Agent 工具并行调度
- 方案 B：创建 `agents/value_agent.py`, `growth_agent.py`, `risk_agent.py`, `cycle_agent.py`

### H2：Skill 未引用 MCP 工具或脚本

**现状**：19 个 skill 文档中没有引用任何 `mcp__*` 工具或 `tools/*.py` 脚本。

**风险**：Claude 执行 skill 时不知道应该调用哪些工具，可能遗漏关键数据源。

**修复建议**：在每个 skill 文档中添加"工具依赖"段落：
```markdown
## 工具依赖
- `mcp__cn-mutual-fund__get_fund_info`
- `mcp__cn-financial__get_valuation_metrics`
- `tools/financial_rigor.py verify-scale`
```

### H3：无 MCP 失败降级文档

**现状**：所有 skill 文档未说明 MCP 接口失败时的降级策略。

**风险**：网络异常时 skill 直接崩溃，用户体验差。

**修复建议**：在每个 skill 中添加"失败处理"段落，明确：
- MCP 超时 → 标注"数据不可用"并继续
- MCP 返回陈旧数据（如 2014 年北向资金）→ 标注异常并跳过
- 全部 MCP 失败 → 输出"当前无法获取实时数据"

---

## 🟢 中度问题（可选修复）

### M1：无 skill 级 eval 框架

**现状**：项目已有 `evals/` 目录结构（来自 fund-recommend），但 fund-selector 没有建立。

**修复建议**：创建 `.claude/skills/fund-selector/evals/evals.json`，为每个 skill 定义断言。

### M2：Agent 与 Skill 无映射文档

**现状**：不清楚哪些 skill 走 Agent 层、哪些直连工具。

**修复建议**：在 SKILL.md 中明确标注每个 skill 的类型（轻量/团队型）。

### M3：缺少端到端集成测试

**现状**：无完整 pipeline 测试（Step 0 → 7 + Agent + 报告）。

**修复建议**：创建 `tests/test_full_pipeline.py`，模拟完整运行。

---

## ✅ 通过项

| 检查项 | 状态 |
|--------|------|
| 无敏感信息泄露（password/secret/token）| ✅ |
| 19 个 skill 都有触发词 | ✅ |
| 19 个 skill 都有输出说明 | ✅ |
| 工具层 5 工具完整 | ✅ |
| 工具层 10/10 测试通过 | ✅ |
| Agent 基础架构完整 | ✅ |

---

## 📋 修复优先级清单

| 优先级 | 编号 | 修复项 | 工作量 |
|--------|------|--------|--------|
| P0 | S3 | 清理路由表 5 个错误路径 | 5 分钟 |
| P0 | S1 | 为 19 个 skill 添加 eval 断言 | 1-2 天 |
| P1 | S2 | 为高频 skill 添加 backing script | 2-3 天 |
| P1 | H1 | 实现 4 大师视角 Agent | 1 天 |
| P1 | H2 | skill 文档添加工具依赖 | 0.5 天 |
| P2 | H3 | 添加 MCP 失败降级文档 | 0.5 天 |
| P2 | M1 | 建立 eval 框架 | 0.5 天 |
| P3 | M3 | 端到端集成测试 | 1 天 |

---

*审计方法：静态分析 + 代码审查 + 测试覆盖扫描*
