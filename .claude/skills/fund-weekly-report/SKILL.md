---
name: fund-weekly-report
description: >
  自动生成基金持仓周报。读�?portfolio.json，通过 AKShare 获取最新净值，
  计算盈亏，搜索板块新闻，检查规则触发，生成完整报告文件�?  触发词：基金报告、周报、fund report、生成报告、查看持仓、持仓分析�?  基金净值、持仓盈亏、我的基金、portfolio report�?  只要用户�?生成报告"�?查看持仓"，即触发�?Skill�?when_to_use: >
  用户想了解当前基金持仓盈亏状态时触发�?  包括：每周定期检查、手动触发分析、定投后更新确认�?  不触发场景：用户只是询问某只基金的信息（由普通对话处理）�?disable-model-invocation: false
user-invocable: true
context:
  agent: general-purpose
  allowed-tools:
    - Read
    - Write
    - Bash
    - Python
effort: high
---

# 基金持仓周报 Skill

自动生成基金持仓周报，包含最新净值、盈亏计算、板块新闻、规则提示�?
## 执行前准�?(Step 0)

在开始任何工作之前，必须完成以下读取�?
1. **读取持仓文件**: `portfolio.json`（仓库根目录）
   - 提取所有基金的 `code`、`name`、`units`、`cost_nav`

2. **读取 Schema**: `${CLAUDE_SKILL_DIR}\..\_shared\portfolio-schema.md`
   - 了解 JSON 格式规范和字段含�?
3. **读取板块映射**: `${CLAUDE_SKILL_DIR}\..\_shared\sector-map.md`
   - 了解基金代码与板块的映射关系，用于新闻搜�?
4. **读取规则定义**: `${CLAUDE_SKILL_DIR}\..\_shared\rule-definitions.md`
   - 了解止盈/集中�?跌幅等规则的阈�?
**MUST NOT** 跳过文件读取直接执行。如果文件不存在，明确报错并停止�?
---

## Step 1: 获取最新净�?
运行脚本获取所有基金最新净值：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\fetch_nav.py portfolio.json > fund-reports/_nav.json
```

**输出格式**: `[{"code": "004597", "name": "...", "nav": 1.3111, "nav_date": "2026-06-26"}, ...]`

**失败处理**: 如果脚本退出码�?0，显示具体错误信息，停止执行，不继续后续步骤�?
---

## Step 2: 计算盈亏

基于净值数据计算每只基金的盈亏�?
```bash
python ${CLAUDE_SKILL_DIR}\scripts\calculate_pnl.py portfolio.json fund-reports/_nav.json > fund-reports/_pnl.json
```

**计算逻辑**:
- 当前市�?= `units × latest_nav`
- 盈亏金额 = `当前市�?- (units × cost_nav)`
- 盈亏百分�?= `盈亏金额 / (units × cost_nav) × 100%`
- 距回本需涨幅 = `|亏损率| / (1 - |亏损率|)`（仅亏损时显示）

**输出格式**: `{"holdings": [...], "summary": {"total_value": ..., "total_pnl": ..., ...}}`

---

## Step 3: 搜索板块新闻

使用 Tavily 搜索各板块近 7 天新闻：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\search_news.py > fund-reports/_news.json
```

**搜索板块**: 银行、金融科技、人工智能、半导体、纳斯达克、黄金、港股科技、债券

**失败处理**: 如果 Tavily API 不可用（未设�?API Key 或网络错误），标�?新闻搜索不可�?�?*继续执行** Step 4�?
---

## Step 4: 规则检�?
根据规则定义检查是否触发警告：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\check_rules.py fund-reports/_pnl.json > fund-reports/_alerts.json
```

**检查规�?*:
- ⚠️ **止盈提示**: 任何基金盈利 > 30%
- ⚠️ **集中度警�?*: 任何板块占总市�?> 25%
- ⚠️ **跌幅提示**: 组合总跌�?> 3%
- ℹ️ **连续下跌关注**: 任何基金连续 4 周下跌（需历史数据，当前版本跳过）

**输出格式**: `[{"level": "warning", "type": "profit_alert", "message": "..."}, ...]`

---

## Step 5: 生成报告

整合所有数据，生成最终报告文件：

```bash
python ${CLAUDE_SKILL_DIR}\scripts\generate_report.py fund-reports/_pnl.json fund-reports/_news.json fund-reports/_alerts.json fund-reports/
```

**报告结构**:

```
=== 基金持仓周报 YYYY-MM-DD ===

【规则提示】（如有触发�?⚠️ [提示内容]

【持仓概览�?总市值：XX,XXX.XX �?总盈亏：+/-X,XXX.XX �?(+/-X.XX%)

【各基金明细�?基金名称 | 持有市�?| 盈亏金额 | 盈亏% | 备注
...

【板块新闻摘要】（如搜索成功）
[银行] ...
[AI] ...
...

【数据说明�?净值来源：天天基金网（AKShare�?新闻来源：Tavily
本报告仅供参考，不构成投资建�?```

**输出文件**: `fund-reports/report_YYYYMMDD.txt`（UTF-8 编码�?
---

## 对话内输�?
报告生成完成后，在对话中输出以下摘要（前 5 条最重要信息）：

1. **规则提示**（如有触发，优先展示�?2. **总市值和总盈�?*（一句话总结�?3. **盈利最多的基金**（名�?+ 盈亏%�?4. **亏损最多的基金**（名�?+ 盈亏% + 回本需涨幅�?5. **报告文件路径**（完整路径）

---

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| portfolio.json 不存�?| 明确报错，停止执�?|
| AKShare 网络超时 | 显示错误，停止执�?|
| Tavily API 不可�?| 跳过新闻，继续执�?|
| 某基金净值获取失�?| 标注"数据缺失"，继续其他基�?|
| 报告文件写入失败 | 显示权限/路径错误 |

---

## 注意事项

- 净值数据来源：天天基金网（AKShare），可能存在 T+2 延迟
- 新闻搜索依赖 Tavily API，需设置 `TAVILY_API_KEY` 环境变量
- 所有中间文件保存在 `fund-reports/` 目录（`_nav.json`, `_pnl.json`, `_news.json`, `_alerts.json`�?- 最终报告文件命名：`report_YYYYMMDD.txt`
- �?Skill 不执行任何买卖操作，仅生成分析报�?