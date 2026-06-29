# P5 研究发现 — MCP调用职责分离

## 根因分析

### 问题现象

2026-06-29 的推荐报告（recommend_20260629.txt）中：
- 总市值：N/A 元（应为 41,323.55）
- 周期判断：未知（置信度：N/A）
- 经理：待补充（应为具体姓名）
- 总费率：待补充（应为 X.XX%）
- 近1年：待补充（应为 +X.XX%）
- 近3年：待补充（应为 +X.XX%）
- 最大回撤：待补充（应为 -X.XX%）

### 上上版数据正确的原因

上上版（P3修复前）报告正确显示了数据：
```
近1年：+5.55% | 近3年：-12.86% | 最大回撤：-19.94%
```

原因是 **Claude 直接调用 MCP 工具后手动整合到报告中**，没有经过 Python 脚本。

### P3 修复后引入的回归

P3 修复建立了 pipeline 架构，但错误地假设：
1. `get_macro.py` 可以自己获取宏观数据 → 实际输出空模板
2. `validate_funds.py` 可以自己获取基金数据 → 实际只获取 AKShare 数据，MCP 字段留空
3. `calc_var_impact.py` 可以读取 constraints 中的 total_value → 实际 step0 的 total_value 未正确传递

### 数据流断裂图

```
当前断裂的数据流：

load_portfolio.py → step0 ✅ {total_value: 41323.55, ...}
screen_candidates.py → step2 ✅ {top10: [...]}
get_macro.py → 输出空模板 ❌ → 无 step1 文件
validate_funds.py → step3（AKShare数据 + None字段）❌ → MCP字段全为None
calc_var_impact.py → step4 ✅（但读不到 total_value）
search_news.py → step5 ✅（但 sector=未知）
                    ↓
generate_recommend.py → 合并所有 step
                    ↓
报告：total_value=N/A, 经理=待补充, 收益=待补充
```

### 核心矛盾

| 能力 | Claude | Python 脚本 |
|------|--------|-------------|
| 调用 MCP 工具 | ✅ | ❌ |
| 调用 AKShare | ✅（间接） | ✅ |
| 文件读写 | ✅ | ✅ |
| 数学计算 | ✅ | ✅ |
| 报告格式化 | ✅ | ✅ |

**矛盾**：pipeline 架构要求 Python 脚本串联执行，但 MCP 工具只能由 Claude 调用。

### 修复方案：职责分离

```
Claude 的职责：
  1. 调用 MCP 工具获取数据
  2. 将结果写入 pipeline JSON 文件
  3. 触发 Python 脚本进行后续处理

Python 脚本的职责：
  1. 读取 pipeline JSON 中的 MCP 数据
  2. 执行本地计算（AKShare、数学、格式化）
  3. 写入计算结果到 pipeline JSON
```

## 设计决策

| 决策点 | 选项 A | 选项 B | 选择 |
|--------|--------|--------|------|
| step 文件命名 | 数字编号（step0-step5） | 语义化命名（step1_macro, step3_funds） | B（清晰表达数据来源）|
| Claude 写入方式 | Claude 直接写 JSON | Python 脚本格式化后写 | A（减少脚本复杂度）|
| AKShare 数据获取 | Python 脚本 | Claude 调用 MCP | B（Python 可直接 import）|
| generate_recommend 适配 | 重写读取逻辑 | 保持兼容多格式 | A（统一命名后重写）|

## 新文件结构

```
fund-reports/
├── _pipeline_step0_constraints.json   ← load_portfolio.py
├── _pipeline_step1_macro.json         ← Claude MCP 写入
├── _pipeline_step2_candidates.json    ← screen_candidates.py
├── _pipeline_step3_funds.json         ← Claude MCP 写入
├── _pipeline_step3_akshare.json       ← validate_funds.py（AKShare补充）
├── _pipeline_step4_var.json           ← calc_var_impact.py
├── _pipeline_step5_news.json          ← search_news.py
└── _pipeline_step6_report.txt         ← generate_recommend.py
```

**注意**：为保持向后兼容，pipeline.py 内部映射：
- step0 → step0_constraints
- step1 → step1_macro（Claude 写入）
- step2 → step2_candidates
- step3 → step3_funds（Claude 写入）
- step3_akshare → step3_akshare（Python 写入）
- step4 → step4_var
- step5 → step5_news

## 相关文件路径

- `.claude/skills/fund-recommend/scripts/pipeline.py` — 步骤文件管理
- `.claude/skills/fund-recommend/scripts/get_macro.py` — 宏观数据脚本（需降级）
- `.claude/skills/fund-recommend/scripts/validate_funds.py` — 基金验证脚本（需降级）
- `.claude/skills/fund-recommend/scripts/generate_recommend.py` — 报告生成（需适配）
- `.claude/skills/fund-recommend/SKILL.md` — Skill 定义（需重构 Step1/3）
- `.claude/skills/_shared/rule-definitions.md` — 规则定义（需新增约束）
