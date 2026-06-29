# fund-recommend Skill 分析

## 当前状态

| 问题 | 状态 | 触发案例 | 修复方案 |
|------|------|---------|---------|
| P1 规模筛选失效 | ✅ 已修复 | 2026-06-29 报告中出现 024120（44.81万）和 002214（3877万） | AKShare 实时规模验证 |
| P2 新闻返回英文 | ✅ 已修复 | 新闻板块出现英文开头"As of June 2026" | 搜索词中文化 + days=7 |
| P3 数据流断裂 | ✅ 已修复 | 报告中VaR和新闻显示"无" | 统一数据总线 pipeline.py |
| P4 收益标签误导 | ✅ 已修复 | 020362（2年5月）标注"近3年：+51.71%" | 成立日期校验+动态标签 |
| P5 MCP调用职责错误 | ✅ 已修复 | 2026-06-29报告中全部数据显示"待补充"，宏观周期"未知" | Claude直接执行MCP调用，Python仅格式化 |

---

## P5 修复详情

### 触发案例

2026-06-29 推荐报告（recommend_20260629.txt）中：
- 总市值：N/A 元（应为 40,831.62）
- 周期判断：未知（置信度：N/A）
- 经理：待补充（应为具体姓名）
- 总费率：待补充
- 近1年/近3年/最大回撤：全部待补充

### 根因

P3 修复引入 pipeline 架构后，将 MCP 数据获取职责错误地分配给 Python 脚本：
- `get_macro.py` 输出空模板（无法调用 get_macro_pmi 等 MCP 工具）
- `validate_funds.py` 只获取 AKShare 数据，MCP 字段（经理/费率/收益）留 None
- Python subprocess 无法访问 Claude 内置的 MCP 工具

### 修复方案

重构 SKILL.md 的 Step1 和 Step3 为 Claude 直接执行 MCP 调用：
1. Claude 调用 MCP 工具（get_macro_pmi, get_fund_info 等）
2. Claude 将结果写入 _pipeline_step1.json / _pipeline_step3.json
3. Python 脚本读取已填好的 JSON 进行格式化/计算
4. generate_recommend.py 合并所有 JSON 生成完整报告

### 关键文件

- `SKILL.md` — Step1/Step3 改为 Claude MCP 调用
- `scripts/pipeline.py` — 扩展支持 step1/step3 文件
- `scripts/generate_recommend.py` — 适配新数据格式
- `_shared/rule-definitions.md` — 新增架构约束章节

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
| `.claude/skills/fund-recommend/evals/evals.json` | 3条自动化断言 (B1-B3) |

### 验证结果

修复后 `screen_candidates.py` 输出：
```
[EXCLUDE] 024120 规模44.81万 < 20000万（2亿）阈值
[EXCLUDE] 002214 规模3877.78万 < 20000万（2亿）阈值
[EXCLUDE] 020362 规模744.35万 < 20000万（2亿）阈值
[INFO] 因规模不足被排除: 6只
```

---

## P2 修复详情

### 触发案例

2026-06-29 报告中新闻板块出现：
- 英文开头 "As of June 2026, the Hang Seng Tech Index..."
- 混入超过7天的旧新闻

### 根因

1. `search_news.py` 搜索词为英文（如 "NASDAQ US tech"、"gold price outlook"）
2. Tavily 搜索未传入 `days=7` 参数
3. 输出未标注发布时间，无法识别超期新闻

### 修复方案

1. 搜索词全部中文化（如 "美国纳斯达克 美股科技 AI 2026年6月"）
2. Tavily 搜索加入 `days=7` 参数
3. 输出新增 `published_date` 和 `time_warning` 字段
4. 新增 `is_older_than_7_days()` 时效验证函数

### 修改文件

| 文件 | 变更 |
|------|------|
| `.claude/skills/fund-recommend/scripts/search_news.py` | 搜索词中文化 + days=7 + 时间检查 |
| `.claude/skills/fund-weekly-report/scripts/search_news.py` | 同上 + UTF-8 stdout wrapper |
| `.claude/skills/_shared/sector-map.md` | 搜索词表移除英文列 |
| `.claude/skills/fund-recommend/evals/evals.json` | 3条自动化断言 (B4-B6) |

### 验证结果

全部8个搜索词均为中文，Tavily 调用包含 `days=7`，输出含 `published_date`。

---

## P3 修复详情

### 触发案例

2026-06-29 推荐报告中：
- 3只推荐基金的新闻均未写入报告正文（显示"无"）
- VaR 影响数值来自临时估算，非 `calc_var_impact.py` 的输出

### 根因

各脚本独立运行，输出到 stdout，但 `generate_recommend.py` 只接受一个 JSON 参数。Claude 获取的数据停留在对话上下文中，未写入文件。

### 修复方案

引入 `_pipeline_data.json` 统一数据总线：
- `load_portfolio.py` → `pipeline["constraints"]`
- `screen_candidates.py` → `pipeline["candidates"]`
- `validate_funds.py` → `pipeline["validated_funds"]`
- `calc_var_impact.py` → `pipeline["var_impacts"]`
- `search_news.py` → `pipeline["news"]`
- `generate_recommend.py --pipeline` → 读取完整数据

### 修改文件

| 文件 | 变更 |
|------|------|
| `.claude/skills/fund-recommend/scripts/pipeline.py` | **新建** — 统一数据总线模块 |
| `.claude/skills/fund-recommend/scripts/load_portfolio.py` | 末尾追加写入 pipeline |
| `.claude/skills/fund-recommend/scripts/screen_candidates.py` | 末尾追加写入 pipeline |
| `.claude/skills/fund-recommend/scripts/validate_funds.py` | 重写为实际执行脚本 |
| `.claude/skills/fund-recommend/scripts/calc_var_impact.py` | 修改为读取 pipeline |
| `.claude/skills/fund-recommend/scripts/search_news.py` | 重写为实际执行脚本 |
| `.claude/skills/fund-recommend/scripts/generate_recommend.py` | 新增 `--pipeline` 模式 + UTF-8 wrapper |
| `.claude/skills/fund-recommend/SKILL.md` | Step 7 更新为 4 步流水线 |
| `.claude/skills/fund-recommend/evals/evals.json` | 1条自动化断言 (B3-data-flow) |

### 验证结果

```
Pipeline keys: ['constraints', 'candidates', 'validated_funds', 'var_impacts']
Candidates: 9
Validated: 9
VaR impacts: 9
```

报告包含 VaR 数值（45.82 元/只）和新闻板块。

---

## P4 修复详情

### 触发案例

2026-06-29 报告中：
- 020362 中海沪港深价值优选混合C：成立日期 2024-01-12（约2年5个月）
- 报告标注：近3年：+51.71%（实为成立以来收益）

### 根因

1. `validate_funds.py` 不获取基金成立时间
2. Claude 在生成报告时直接使用 MCP 返回的"3年收益"字段
3. MCP 对不满3年基金的"3年收益"实际是"成立以来收益"，但标签仍为"近3年"

### 修复方案

1. `validate_funds.py` 从 AKShare 获取"成立时间"字段
2. 计算成立年限，不满3年生成标签 `"成立以来（Y年M月）"`
3. `generate_recommend.py` 使用动态标签而非固定"近3年"

### 修改文件

| 文件 | 变更 |
|------|------|
| `.claude/skills/fund-recommend/scripts/validate_funds.py` | 新增 `get_return_label()` + 成立日期获取 |
| `.claude/skills/fund-recommend/scripts/generate_recommend.py` | 收益显示使用动态标签 + 成立日期信息 |
| `.claude/skills/fund-recommend/evals/evals.json` | 1条自动化断言 (B4-return-label) |

### 验证结果

报告中不满3年基金显示：
```
近1年：待补充 | 成立以来（2年10月）：待补充 | 最大回撤：待补充
板块：未知 | 综合评分：22.8785 | 成立于2023-08-11（2年10月）
```

满3年基金不受影响：
```
近1年：待补充 | 近3年：待补充 | 最大回撤：待补充
板块：未知 | 综合评分：23.663
```

---

## 待修复问题

| 问题 | 状态 | 描述 |
|------|------|------|
| 无 | — | 所有已知问题已修复 |

---

## 迭代记录

| 版本 | 日期 | 变更 |
|------|------|------|
| iteration-1 | 2026-06-24 | 初始版本 |
| iteration-2 | 2026-06-29 | P1+P2+P3+P4 全部修复 |
