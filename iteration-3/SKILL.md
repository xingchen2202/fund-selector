---
name: fund-recommend
description: >
  筛选候选基金并分析组合影响。触发词：推荐基金、基金筛选、
  fund recommend、有什么基金可以买、推荐、筛选基金。
  用户想了解有哪些基金值得关注时触发。
when_to_use: >
  用户想在现有组合基础上新增基金时触发。
  不触发：用户只是查询某只基金信息（普通对话处理）。
  不触发：用户查看现有持仓（由fund-weekly-report处理）。
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily
effort: high
---

# 基金筛选推荐 Skill

基于宏观数据 + 现有组合约束 + 新闻背景，筛选候选基金并分析组合影响。

## 架构约束（铁律）

> **MCP 调用必须由 Claude 执行，Python 脚本只负责本地计算和文件读写。**

- MCP 工具（cn-financial、cn-mutual-fund、tavily）只能由 Claude 调用
- Python subprocess 无法访问 MCP 工具
- Claude 调用 MCP 后，将结果写入 pipeline JSON 文件
- Python 脚本读取已填好的 JSON 进行计算/格式化

---

## 执行前准备 (MUST)

在开始任何工作之前，必须完成以下读取：

1. **读取持仓文件**: `C:\Users\22218\Desktop\fund-selector\portfolio.json`
   - 提取所有基金的 code、name、units、cost_nav、cost_value

2. **读取规则定义**: `${CLAUDE_SKILL_DIR}\..\_shared\rule-definitions.md`
   - 了解集中度限制、VaR 上限、回撤阈值等（第一节：基金筛选规则）
   - 了解架构约束（第三节：MCP 调用职责分离）

3. **读取板块映射**: `${CLAUDE_SKILL_DIR}\..\_shared\sector-map.md`
   - 了解基金代码与板块的映射关系（含聚合分组 + 新闻关键词）

4. **读取宏观周期指南**: `${CLAUDE_SKILL_DIR}\..\_shared\macro-cycle-guide.md`
   - 了解经济周期判断逻辑

5. **读取紫苏叶框架**: `${CLAUDE_SKILL_DIR}\..\_shared\perilla-framework.md`
   - 了解持仓穿透分析标准（仅 --perilla 模式需要）

**MUST NOT** 跳过任何前置读取。如果 portfolio.json 不存在，明确报错并停止。

---

## Step 0：组合约束计算（Python 执行）

运行脚本计算当前组合的约束条件：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\load_portfolio.py
```

**输出**: 写入 `_pipeline_step0_constraints.json`
- 当前各板块占比（按 sector-map.md 的分组）
- 已超配板块列表（占比 > 25% 的板块）
- 当前组合总市值
- 上次 VaR 估算值（简化计算）
- 本次筛选的 VaR 新增预算（上限 = 2000 - 当前月度 VaR 估算）

**失败处理**: 如果 portfolio.json 不存在，输出"请先更新 portfolio.json"，停止执行。

---

## Step 1：宏观环境判断（Claude 执行 MCP 调用）

> **此步骤由 Claude 调用 MCP 工具，Python 脚本仅做格式化。**

### 1.1 调用 MCP 工具

分别调用以下 MCP 工具（每个独立 try/catch）：

```
cn-financial MCP:
  - get_macro_pmi()        → PMI 趋势（标注成功/失败）
  - get_macro_money_supply() → M2 增速（标注成功/失败）
  - get_valuation_metrics(symbol="000300", num_periods=60) → 沪深300估值（标注成功/失败）
  - get_north_bound_flow()  → 北向资金（标注成功/失败）
```

### 1.2 判断经济周期

基于上述数据，参考 macro-cycle-guide.md 判断经济周期阶段。

### 1.3 写入 pipeline

将结果写入 `_pipeline_step1_macro.json`：

```json
{
  "pmi": {"available": true, "manufacturing": 51.2, "non_manufacturing": 52.1},
  "money_supply": {"available": true, "m2_yoy": 8.5, "m1_yoy": 5.2},
  "valuation": {"available": true, "hs300_pe": 12.5, "hs300_pe_percentile": 35.0},
  "north_bound": {"available": false, "recent_flow": null},
  "cycle_judgment": {"phase": "复苏", "confidence": "中", "direction": "偏股"},
  "available_indicators": ["PMI", "M2", "沪深300PE"],
  "unavailable_indicators": ["北向资金"]
}
```

### 1.4 格式化确认

```bash
python ${CLAUDE_SKILL_DIR}\scripts\get_macro.py
```

此脚本读取 step1 文件并格式化输出到 stderr，确认数据完整性。

---

## Step 2：候选池筛选（Python 执行）

运行脚本从 Excel 候选池中筛选：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\screen_candidates.py
```

**筛选逻辑**:
1. 读取 `fund_screening_corrected_20260624.xlsx` 的"防守型"和"稳健型"两个 Sheet
2. 排除已持有的基金代码（与 portfolio.json 比对）
3. 排除已超配板块对应的基金（从 Step 0 获取）
4. 按综合得分降序排列，取前 15 只
5. **【P1修复】实时规模验证**：对每只候选调用 AKShare `fund_individual_basic_info_xq` 获取"最新规模"字段，低于 2 亿（20000 万）的基金排除，标注排除原因
6. 取前 10 只

**输出**: 写入 `_pipeline_step2_candidates.json`
- 候选基金列表（代码 + 名称 + Excel 评分 + 板块 + 实际规模）

**stderr 日志**:
- `[EXCLUDE] {code} {name} 规模{scale}万，低于2亿阈值` — 被排除的基金
- `[WARN] {code} 规模数据不可用，保留待人工核实` — AKShare 接口异常
- `[INFO] 因规模不足被排除: N只` — 排除汇总

---

## Step 3：候选基金验证（Claude 执行 MCP 调用）

> **此步骤由 Claude 调用 MCP 工具获取基金详细数据。**

### 3.1 读取候选列表

从 `_pipeline_step2_candidates.json` 读取 top10 候选基金代码。

### 3.2 调用 MCP 工具

对每只候选基金调用 cn-mutual-fund MCP：

```
cn-mutual-fund MCP（每只基金）:
  - get_fund_info(fund_code) → 规模、经理、费率、成立日期
  - get_fund_nav_history(fund_code, period="3y") → 近1年/近3年收益、最大回撤
  - get_fund_portfolio(fund_code) → 前十大持仓
```

### 3.3 写入 pipeline

将结果写入 `_pipeline_step3_funds.json`：

```json
{
  "candidates": ["003593", "166001", "018167"],
  "verified": [
    {
      "code": "003593",
      "name": "国泰景气行业灵活配置混合",
      "scale_wan": 44200,
      "manager": "XXX",
      "fee": "管理费1.5% + 托管费0.25%",
      "return_1y": 5.55,
      "return_1y_label": "近1年",
      "return_3y": -12.86,
      "return_3y_label": "近3年",
      "max_drawdown": -19.94,
      "sharpe": 0.85,
      "establishment_date": "2017-03-20",
      "age_years": 9,
      "age_months": 3,
      "top_holdings": [
        {"code": "600519", "name": "贵州茅台", "weight": 8.5}
      ]
    }
  ],
  "failed": []
}
```

**字段说明**：
- `return_1y` / `return_3y`：数值（如 5.55 表示 +5.55%）
- `return_1y_label` / `return_3y_label`：动态标签，不满3年显示"成立以来（X年X月）"
- `max_drawdown`：负数（如 -19.94）

### 3.4 AKShare 补充验证（可选）

```bash
python ${CLAUDE_SKILL_DIR}\scripts\validate_funds.py
```

此脚本读取 step3 文件，可选补充 AKShare 规模验证，写入 `_pipeline_step3_akshare.json`。

**失败处理**:
- 单只基金 MCP 失败：标注"数据获取失败"，跳过，继续处理下一只
- 全部失败：输出"所有候选基金数据获取失败，请检查网络"，停止

---

## Step 4：VaR 影响计算（Python 执行）

运行脚本计算加入新基金后的 VaR 变化：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\calc_var_impact.py
```

**输入**: step0（约束）+ step2（候选）
**输出**: 写入 `_pipeline_step4_var.json`

对每只通过验证的候选基金：
- 模拟加入 5% 仓位（约 2500 元）后的组合 VaR 变化
- 排除加入后月度 VaR 超过 2000 元的基金
- 标注每只基金的"预计 VaR 新增"

---

## Step 5：新闻搜索（Python 执行）

运行脚本搜索板块新闻：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\search_news.py
```

**输入**: step2（候选列表）
**输出**: 写入 `_pipeline_step5_news.json`

对每只最终候选基金：
- 搜索该板块近 7 天**利多**新闻（至少 1 条）
- 搜索该板块近 7 天**利空**新闻（至少 1 条，**不能省略**）
- 如果找不到利空新闻：标注"未找到明显利空"，**不允许跳过不写**

**失败处理**: Tavily 失败时标注"新闻数据不可用"，继续输出报告

---

## Step 6（可选）：紫苏叶分析

**仅当用户明确请求时执行**（`/fund:recommend --perilla`）

运行脚本进行持仓穿透分析：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\perilla_analysis.py
```

对每只候选基金的前十大持仓股：
- `get_financial_indicators(stock_code)` → 毛利率、ROE
- 对照 perilla-framework.md 的标准打分
- 标注符合条件的持仓股

**必须注明**: 数据来自基金季报，滞后一个季度

---

## Step 7：生成报告（Python 执行）

```bash
python ${CLAUDE_SKILL_DIR}\scripts\generate_recommend.py --pipeline
```

**数据源**（按优先级读取）：
1. `_pipeline_step0_constraints.json` — 组合约束
2. `_pipeline_step1_macro.json` — 宏观环境
3. `_pipeline_step2_candidates.json` — 候选列表
4. `_pipeline_step3_funds.json` — 基金详细数据（Claude MCP）
5. `_pipeline_step4_var.json` — VaR 影响
6. `_pipeline_step5_news.json` — 新闻数据

**报告结构**（严格遵循）:

```
=== 基金筛选参考报告 YYYY-MM-DD ===

【当前组合约束】
总市值：XX,XXX 元 | VaR 预算剩余：X,XXX 元
已超配（本次不推荐新增）：XX板块（占比 XX%）

【宏观环境】
周期判断：XX 期（置信度：高/中/低）
可用指标：PMI=XX, M2=X.X%, ...
不可用指标：北向资金（接口超时）

【最终候选基金】（不超过 3 只）
━━━━━━━━━━━━━━━━━━━━
▌ 基金名称（代码）
[数据层]
  规模：XX 亿 | 经理：XXX | 总费率：X.XX%
  近 1 年：+X.XX% | 近 3 年：+X.XX% | 最大回撤：-XX.XX%
[分析层]
  基于数据的客观描述，不含主观推荐
[VaR 影响]
  加入 5% 仓位预计增加 VaR：XXX 元
[新闻背景]
  利多：...
  利空：...
[紫苏叶视角]（仅在 --perilla 模式下）
  XX 股份：符合 3 项标准（中小盘+毛利率+行业地位）

【你需要自己判断的】
- 现在买还是等：AI 无法判断，这是你的决定
- 买入金额：建议不超过单次定投的 2 倍
- 是否先止盈现有持仓再买入

【数据说明】
- 基金数据来源：cn-mutual-fund MCP（AKShare）
- 新闻来源：AKShare + Tavily（备用）
- 持仓数据滞后：一个季度
- 本报告不构成投资建议
```

**报告保存路径**: `C:\Users\22218\Desktop\fund-selector\fund-reports\recommend_YYYYMMDD.txt`

同时在对话中输出报告完整内容。

---

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| portfolio.json 不存在 | 明确报错，停止执行 |
| MCP 接口超时 | 标注"数据不可用"，继续其他步骤 |
| 所有候选被过滤 | 输出"当前风险约束下无合适候选" |
| Tavily 不可用 | 标注跳过，继续生成报告 |
| Excel 文件不存在 | 输出"候选池文件缺失"，停止 |
| 某基金净值获取失败 | 跳过该基金，继续下一只 |
| step1/step3 文件不存在 | Claude 必须先调用 MCP 写入 |

---

## 注意事项

- 所有客观数据必须标注来源和时间
- 所有分析必须是客观描述，不含主观推荐
- 利空新闻不能为空（防止确认偏误）
- 持仓数据必须标注"滞后一季度"
- 始终附带免责声明
- **MCP 调用必须由 Claude 执行，不得放入 Python 脚本**
