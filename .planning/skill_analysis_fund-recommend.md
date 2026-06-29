# fund-recommend Skill 分析

## 当前状态

| 问题 | 状态 | 触发案例 | 修复方案 |
|------|------|---------|---------|
| P1 规模筛选失效 | ✅ 已修复 | 2026-06-29 报告中出现 024120（44.81万）和 002214（3877万） | AKShare 实时规模验证 |

---

## P1 修复详情

### 触发案例

2026-06-29 推荐报告（recommend_20260629.txt）中出现以下不合格基金：
- 024120 中邮核心主题混合C：实际规模 44.81万（0.004481亿），被规则要求排除
- 002214 中海沪港深价值优选混合A：实际规模 3877.78万（0.387亿），被规则要求排除
- 020362 中海沪港深价值优选混合C：实际规模 744.35万（0.074亿），被规则要求排除

### 根因

Excel 候选池 `fund_screening_corrected_20260624.xlsx` 不含"规模"列。  
`screen_candidates.py` 第68行条件 `if "规模（亿元）" in candidates.columns` 始终为 False，筛选静默跳过。

### 修复方案

在 `screen_candidates.py` 中内置 `validate_scale()` 函数，通过 AKShare `fund_individual_basic_info_xq(symbol=code)` 获取"最新规模"字段，解析后判断是否 ≥ 2 亿（20000万元）。

### 修改文件

| 文件 | 变更 |
|------|------|
| `.claude/skills/fund-recommend/scripts/screen_candidates.py` | 新增 `get_fund_scale_wan()` / `validate_scale()` / stderr 日志 |
| `.claude/skills/fund-recommend/SKILL.md` | Step 2 筛选逻辑更新为6步（含规模验证） |
| `.claude/skills/_shared/rule-definitions.md` | 新增"规模验证补充说明"章节 |
| `.claude/skills/fund-recommend/evals/evals.json` | 3条自动化断言 |

### 验证结果

修复后 `screen_candidates.py` 输出：
```
[EXCLUDE] 024120 规模44.81万 < 20000万（2亿）阈值
[EXCLUDE] 002214 规模3877.78万 < 20000万（2亿）阈值
[EXCLUDE] 020362 规模744.35万 < 20000万（2亿）阈值
[INFO] 因规模不足被排除: 6只
```

---

## 待修复问题

| 问题 | 状态 | 描述 |
|------|------|------|
| P2 待定义 | ⏳ 待规划 | 待用户确认 |
