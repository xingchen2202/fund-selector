---
name: fund-recommend
description: >
  筛选候选基金并分析组合影响。触发词：推荐基金、基金筛选、 fund recommend、有什么基金可以买、推荐、筛选基金。 用户想了解有哪些基金值得关注时触发。
  用户想在现有组合基础上新增基金时触发。 不触发：用户只是查询某只基金信息（普通对话处理）。 不触发：用户查看现有持仓（由fund-weekly-report处理）。
---


# 基金筛选推荐 Skill

基于宏观数据 + 现有组合约束 + 新闻背景，筛选候选基金并分析组合影响。
移植增强：集成 ai-berkshire (MIT) 的「双 Agent 对抗分析 + 快否决清单 + 镜子测试 + Decimal 精度工具」防偏差机制。

## 架构（三层）

| 层级 | 组件 | 说明 |
|------|------|------|
| **Agent 层** | `agents/offense_agent.py` | 进攻视角（成长/动量/赛道）|
|             | `agents/defense_agent.py` | 防守视角（回撤/波动/稳定性）|
|             | `agents/synthesizer.py`   | 双视角综合 + 冲突检测 |
| **Skill 层** | `/fund-recommend`         | 主入口（单 Agent pipeline）|
| **工具层** | `scripts/financial_rigor.py` | Decimal 精度验算 |
|             | `scripts/rejection_checklist.py` | 6 条一票否决红线 |
|             | `scripts/generate_recommend.py` | 报告生成（含 6 个移植函数）|

## 运行模式

### 模式 A：单 Agent（默认）
```
Step 0 → Step 1 → Step 2 → Step 3 → Step 3.5 → Step 4 → Step 5 → Step 7
```
适用于快速筛选，MCP 调用量 ~30 次。

### 模式 B：双 Agent（--team 参数，实验性）
```
Step 0 → Step 1 → Step 2 → Step 3
  ├─ 进攻 Agent → _agent_offense.json
  ├─ 防守 Agent → _agent_defense.json
  └─ 综合器 → _agent_synthesized.json → Step 7（含双 Agent 段落）
```
适用于深度投研，两个视角并行分析后综合，可暴露单一视角盲区。

## 执行前准备 (MUST)

在开始任何工作之前，必须完成以下读取：

1. **读取持仓文件**: `portfolio.json`（仓库根目录）
   - 提取所有基金的 code、name、units、cost_nav、cost_value

2. **读取规则定义**: `${CLAUDE_SKILL_DIR}\..\_shared\rule-definitions.md`
   - 了解集中度限制、VaR 上限、回撤阈值等（第一节：基金筛选规则）

3. **读取板块映射**: `${CLAUDE_SKILL_DIR}\..\_shared\sector-map.md`
   - 了解基金代码与板块的映射关系（含聚合分组 + 新闻关键词）

4. **读取宏观周期指南**: `${CLAUDE_SKILL_DIR}\..\_shared\macro-cycle-guide.md`
   - 了解经济周期判断逻辑

5. **读取紫苏叶框架**: `${CLAUDE_SKILL_DIR}\..\_shared\perilla-framework.md`
   - 了解持仓穿透分析标准（仅 --perilla 模式需要）

**MUST NOT** 跳过任何前置读取。如果 portfolio.json 不存在，明确报错并停止。

---

## Step 0：组合约束计算

运行脚本计算当前组合的约束条件：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\load_portfolio.py
```

**输出**:
- 当前各板块占比（按 sector-map.md 的分组）
- 已超配板块列表（占比 > 25% 的板块）
- 当前组合总市值
- 上次 VaR 估算值（简化计算）
- 本次筛选的 VaR 新增预算（上限 = 2000 - 当前月度 VaR 估算）

**失败处理**: 如果 portfolio.json 不存在，输出"请先更新 portfolio.json"，停止执行。

---

## Step 1：宏观环境判断（Claude直接执行MCP调用）

> **[MUST] Claude直接调用以下MCP工具，不得委托Python脚本。**

### 1.1 调用 MCP 工具

调用1：`get_macro_pmi()`
  → 提取最新制造业PMI值和同比变化
  → 失败时标注"PMI数据不可用"，继续

调用2：`get_macro_money_supply()`
  → 提取M2同比增速
  → 失败时标注"M2数据不可用"，继续

调用3：`get_valuation_metrics(symbol="000300", num_periods=60)`
  → 提取当前PE分位
  → 失败时标注"估值数据不可用"，继续

调用4：`get_north_bound_flow()`
  → 提取近期净流入方向
  → 返回异常数据（如2014年数据）时标注"北向资金接口异常"，继续

### 1.2 判断经济周期

基于上述数据，参考 macro-cycle-guide.md 判断经济周期阶段。

### 1.3 写入 pipeline

[MUST] 完成以上调用后，Claude将结果写入：
  `fund-reports/_pipeline_step1.json`
  格式：
  ```json
  {
    "pmi": {"value": 50.0, "trend": "持平", "available": true},
    "m2": {"value": 8.6, "available": true},
    "valuation": {"pe_percentile": null, "available": false, "reason": "数据为空"},
    "north_flow": {"direction": null, "available": false, "reason": "接口返回2014年数据"},
    "cycle_judgment": "震荡期",
    "cycle_confidence": "中",
    "generated_at": "2026-06-29T15:00:00"
  }
  ```

[MUST NOT] 不得在此步骤调用Python脚本获取宏观数据。

---

## Step 2：候选池筛选

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

**输出**: 候选基金列表（代码 + 名称 + Excel 评分 + 板块 + 实际规模）

**stderr 日志**:
- `[EXCLUDE] {code} {name} 规模{scale}万，低于2亿阈值` — 被排除的基金
- `[WARN] {code} 规模数据不可用，保留待人工核实` — AKShare 接口异常
- `[INFO] 因规模不足被排除: N只` — 排除汇总

---

## Step 3：候选基金验证（Claude直接执行MCP调用）

> 读取 `_pipeline_step2.json` 获取候选基金列表。
> **[MUST] Claude对每只候选基金直接调用以下MCP工具。**

### 3.1 对每只候选基金调用 MCP

对每只候选基金 `fund_code`：

  调用1：`get_fund_info(fund_code=fund_code)`
    → 提取：规模、基金经理、成立日期、管理费、托管费
    → 单只失败：标注"数据不可用"，不中止整体流程

  调用2：`get_fund_nav_history(fund_code=fund_code, period="3y")`
    → 提取：近1年收益、近3年收益、最大回撤
    → 计算：Sharpe比率（如有足够数据）
    → 成立不满3年：标注"成立以来（X年X月）"而非"近3年"

  调用3：`get_fund_manager_info(fund_code=fund_code)`
    → 提取：经理姓名、任职年限

  调用4：`get_fund_nav_history(fund_code=fund_code, period="6mo")` → nav_series（净值序列，至少20个点）
    → **[D3 MUST]** 必须将完整净值序列写入 `_pipeline_step3.json` 的 `nav_series` 字段
    → 无此字段则 Step 4 的真实 VaR 无法计算，回退到"数据不足"占位符

### 3.2 写入 pipeline

[MUST] 完成以上调用后，Claude将所有基金的验证结果写入：
  `fund-reports/_pipeline_step3.json`
  格式：
  ```json
  {
    "validated_funds": [
      {
        "code": "003593",
        "name": "国泰景气行业灵活配置混合",
        "scale": 4.42,
        "scale_unit": "亿",
        "manager": "陈异/王阳",
        "manager_years": 3.5,
        "fee_total": 1.5,
        "return_1y": 5.55,
        "return_label": "近1年",
        "return_3y": -12.86,
        "return_3y_label": "近3年",
        "max_drawdown": -19.94,
        "inception_date": "2017-03-20",
        "nav_series": [1.02, 1.05, 0.98, ...],
        "data_available": true
      }
    ],
    "excluded": [],
    "generated_at": "2026-06-29T15:00:00"
  }
  ```

[MUST NOT] 不得在此步骤调用Python脚本获取基金数据。

**失败处理**:
- 单只基金失败：标注"数据获取失败"，跳过，继续处理下一只
- 全部失败：输出"所有候选基金数据获取失败，请检查网络"，停止

### 3.3 数据精度校验（MUST，移植自 ai-berkshire financial_rigor.py）

对每只候选基金的**关键数值**执行精度校验，确保 MCP 返回数据未漂移：

```bash
# 规模验算：份额 × 净值 vs 报告规模
python ${CLAUDE_SKILL_DIR}\scripts\financial_rigor.py verify-scale --nav {nav} --shares {shares} --reported {reported_scale}

# 多源交叉验证：MCP vs Excel 排名 vs 实时（至少两源）
python ${CLAUDE_SKILL_DIR}\scripts\financial_rigor.py cross-validate --field 规模 --values '{"MCP": X, "Excel": Y}' --unit 亿
```

**校验标准**：偏差 > 5% 标记数据异常，> 1% 可接受但需注明"或因申购赎回波动"。
**工具说明**：`financial_rigor.py` 使用 Python `decimal.Decimal` 而非 float，彻底避免浮点累积误差。

---

## Step 3.5：快否决清单（移植自 ai-berkshire 8 条红线）

对每只候选基金逐条检查，**触发任一条直接一票否决**，不得进入最终候选：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\rejection_checklist.py --code {code} --name {name} \
    --output ${REPORTS_DIR}/_pipeline_rejection.json \
    [--business-unclear] [--fcf-negative] [--drawdown -0.61] [--erosion] [--relying-on-next-buyer] [--cannot-afford-zero]
```

**关键**：必须传 `--output` 将否决结果写入 `_pipeline_rejection.json`，否则 Step 7 报告生成无法消费该结果，被否决的基金仍会出现在最终推荐中。

**6 条一票否决红线（A 股基金版）**：
- **R1** 无法说清底层赚钱方式 → 否决
- **R2** 连续 3 年自由现金流为负且看不到改善 → 否决
- **R3** 权益类最大回撤 < -35%（股票型/指数型/偏股混合/LOF） → 否决
- **R4** 竞争优势被不可逆侵蚀 → 否决
- **R5** 靠"下一个接盘者出更高价"赚钱（博傻） → 否决
- **R6** 无法承受归零后果 → 否决

**阈值参考**：R3 回撤阈值 -35% 对权益类生效，债券/货币基金豁免。

**输出处理**：
- 返回码 0 = 全部通过，继续 Step 4
- 返回码 1 = 触发红线，记录触发的 [R?] 编号，**立即从候选池移除**，不得进入最终推荐

---

运行脚本计算加入新基金后的 VaR 变化：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\calc_var_impact.py
```

对每只通过验证的候选基金：
- 模拟加入 5% 仓位（约 2500 元）后的组合 VaR 变化
- 排除加入后月度 VaR 超过 2000 元的基金
- 标注每只基金的"预计 VaR 新增"

**输出**: 通过 VaR 约束的最终候选列表

---

## Step 5：新闻搜索

运行脚本搜索板块新闻：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\search_news.py
```

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

## Step 7：生成报告（P5修复：Claude MCP + Python 流水线混合模式）

执行顺序：

### 7.1 宏观数据（Claude MCP → step1）
> 已在 Step 1 完成，跳过。

### 7.2 候选池筛选（Python）
```bash
python ${CLAUDE_SKILL_DIR}\scripts\screen_candidates.py
```
写入 `_pipeline_step2.json`

### 7.3 基金验证（Claude MCP → step3）
> 已在 Step 3 完成，跳过。

### 7.4 VaR 影响计算（Python）
```bash
python ${CLAUDE_SKILL_DIR}\scripts\calc_var_impact.py
```
读取 step0 + step2，写入 `_pipeline_step4.json`

### 7.5 新闻搜索（Python）
```bash
python ${CLAUDE_SKILL_DIR}\scripts\search_news.py
```
读取 step2，写入 `_pipeline_step5.json`

### 7.6 生成最终报告（Python）
```bash
python ${CLAUDE_SKILL_DIR}\scripts\generate_recommend.py --pipeline
```
读取所有 step 文件，合并生成报告。

**数据总线文件**:
- `_pipeline_step1.json` — Claude 写入的宏观数据（Step 1）
- `_pipeline_step2.json` — Python 写入的候选列表（Step 7.2）
- `_pipeline_step3.json` — Claude 写入的基金验证数据（Step 3）
- `_pipeline_step4.json` — Python 写入的 VaR 影响（Step 7.4）
- `_pipeline_step5.json` — Python 写入的新闻数据（Step 7.5）

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
  规模：XX 亿（精度校验：偏差 X%） | 经理：XXX | 总费率：X.XX%
  近 1 年：+X.XX% | 近 3 年：+X.XX% | 最大回撤：-XX.XX%
[分析层]
  基于数据的客观描述，不含主观推荐
[快否决]（移植自 ai-berkshire 6 条红线）
  ✅ 全部红线未触发 或 ⛔ 触发 [R?]：{原因} → 已移除
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
- 新闻来源：AKShare（东方财富）
- 持仓数据滞后：一个季度
- 本报告不构成投资建议
```

**报告保存路径**: `fund-reports/recommend_YYYYMMDD.txt`（仓库根目录）

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
| 精度校验偏差 >5% | 标记"数据异常"，人工复核后方可纳入 |
| 触发快否决红线 | 立即移除，记录 [R?] 编号，不进入推荐 |
| 权益类回撤 < -35% | VaR 排除 + 记录到 excluded_by_drawdown |

---

## 注意事项

- 所有客观数据必须标注来源和时间
- 所有分析必须是客观描述，不含主观推荐
- 利空新闻不能为空（防止确认偏误）
- 持仓数据必须标注"滞后一季度"
- 始终附带免责声明
- **MCP 调用必须由 Claude 执行，不得放入 Python 脚本**
