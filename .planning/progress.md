# P5 修复进度 — 2026-06-29

## 状态：已规划，待用户确认执行

### 问题
- 推荐报告中所有数据字段显示"待补充"或"N/A"
- 根因：Python 脚本无法调用 MCP 工具，但 pipeline 架构假设脚本能获取全部数据
- 上上版报告正确是因为 Claude 直接调用 MCP 后手动整合

### 方案
- 重构 SKILL.md Step 1 和 Step 3 为 Claude 主导的 MCP 调用
- Claude 将 MCP 结果写入 pipeline JSON
- Python 脚本降级为纯格式化/补充工具
- 新增架构约束到 rule-definitions.md

### 产物
- `.planning/PLAN-v3.md` — 完整修复计划（本文档的配套计划文件）
- `.planning/task_plan.md` — 任务计划（已更新 P5 内容）
- `.planning/findings.md` — 根因分析（本文档）
- `iteration-3/` — 修复后的文件输出目录

### 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/pipeline.py` | 修改 | 扩展支持语义化 step 文件命名 |
| `SKILL.md` | 修改 | Step1+Step3 改为 Claude MCP 调用 |
| `scripts/get_macro.py` | 修改 | 降级为读取 step1 并格式化输出 |
| `scripts/validate_funds.py` | 修改 | 降级为读取 step3 并补充 AKShare |
| `scripts/generate_recommend.py` | 修改 | 适配新的 step 文件命名 |
| `../_shared/rule-definitions.md` | 修改 | 新增"架构约束"章节 |
| `evals/evals.json` | 修改 | 追加 C1-C3 P5 断言 |

### 新 step 文件映射

| 新命名 | 旧命名 | 数据来源 | 写入者 |
|--------|--------|----------|--------|
| step0_constraints | step0 | portfolio.json | Python |
| step1_macro | (无) | MCP get_macro_* | Claude |
| step2_candidates | step2 | Excel + AKShare | Python |
| step3_funds | (无) | MCP get_fund_info | Claude |
| step3_akshare | step3 | AKShare | Python |
| step4_var | step4 | 计算 | Python |
| step5_news | step5 | AKShare + Tavily | Python |

---

## 依赖关系

```
Phase 1 (pipeline.py) ──→ Phase 2 (SKILL.md) ──→ Phase 6 (evals)
                          ↗                      ↑
Phase 3 (get_macro.py) ──┘                       │
Phase 4 (validate_funds.py) ─────────────────────┘
Phase 5 (rule-definitions.md) ───────────────────┘
```

Phase 1-5 可并行修改，Phase 6 依赖全部完成。
