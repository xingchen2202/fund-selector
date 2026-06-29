# P3 修复计划 — 脚本数据流断裂

## 状态：✅ 已完成 (iteration-2)

## 问题描述

### 现象
`generate_recommend.py` 生成的报告中，VaR 和新闻部分显示"无"或临时估算值。

### 根因
各脚本（`load_portfolio.py`、`screen_candidates.py`、`calc_var_impact.py`、`search_news.py`、`validate_funds.py`）独立运行，输出到 stdout（JSON）。但 `generate_recommend.py` 只接受**一个 data_json_file 参数**，无法同时接收多个脚本的输出。

Claude Code 在执行时，虽然会依次运行各脚本，但：
1. `validate_funds.py` 和 `calc_var_impact.py` 是**模板脚本**，实际数据由 Claude 直接调用 MCP 获取
2. Claude 获取的数据停留在对话上下文中，**没有写入文件**
3. `generate_recommend.py` 读取的 data_json_file 只包含初始的约束和候选数据
4. 最终报告缺少 VaR 和新闻数据 → 显示"无"

### 数据流现状（断裂）

```
load_portfolio.py → stdout JSON → Claude 读取
screen_candidates.py → stdout JSON → Claude 读取
validate_funds.py → Claude 直接调用 MCP → 数据在对话中 ❌ 未写入文件
calc_var_impact.py → Claude 直接调用 MCP → 数据在对话中 ❌ 未写入文件
search_news.py → Claude 直接调用 Tavily → 数据在对话中 ❌ 未写入文件
                    ↓
generate_recommend.py → 读取一个 JSON → 缺少 VaR + 新闻 → 报告不完整
```

### 修复后数据流（统一数据总线）

```
load_portfolio.py → stdout JSON → Claude 读取
screen_candidates.py → stdout JSON → Claude 读取
validate_funds.py → 写入 _pipeline_data.json["funds"]
calc_var_impact.py → 写入 _pipeline_data.json["var"]
search_news.py → 写入 _pipeline_data.json["news"]
                    ↓
generate_recommend.py → 读取 _pipeline_data.json → 完整报告
```

## 修复方案：`_pipeline_data.json` 数据总线

### 数据总线结构

```json
{
  "meta": {
    "generated_at": "2026-06-29T10:00:00",
    "version": "1.0"
  },
  "constraints": {
    "total_value": 50000.0,
    "var_budget": 1200,
    "overloaded_sectors": {"科技成长": 35.2}
  },
  "macro": {
    "cycle_judgment": {"phase": "震荡", "confidence": "中"},
    "available_indicators": ["PMI=51.2", "M2=8.5%"]
  },
  "candidates": [
    {
      "code": "008888",
      "name": "XX基金",
      "sector": "科技成长",
      "score": 85.5
    }
  ],
  "funds": {
    "008888": {
      "code": "008888",
      "name": "XX基金",
      "scale": 12.5,
      "manager": "张三",
      "fee": "1.2%",
      "return_1y": "+15.2%",
      "return_3y": "+42.1%",
      "max_drawdown": "-18.3%",
      "sharpe": 1.45,
      "top_holdings": ["宁德时代", "比亚迪"]
    }
  },
  "var": {
    "008888": {
      "code": "008888",
      "marginal_var": 156.5,
      "combined_var": 1356.5,
      "exceeds_budget": false
    }
  },
  "news": {
    "008888": {
      "code": "008888",
      "sector": "科技成长",
      "bullish": "半导体芯片国产替代加速...",
      "bearish": "出口限制风险仍存...",
      "bullish_date": "2026-06-25",
      "bearish_date": "2026-06-23"
    }
  }
}
```

## 修改清单

### 1. `validate_funds.py` — 写入 funds 字段

**当前**：模板脚本，只输出空模板
**修改后**：接受候选列表 JSON，调用 AKShare 获取数据，写入 `_pipeline_data.json["funds"]`

```python
# 输入：candidates.json（来自 screen_candidates.py 的 stdout）
# 输出：_pipeline_data.json["funds"] 字段
```

关键逻辑：
- 从 `candidates.json` 读取候选基金列表
- 对每只基金调用 `get_fund_info()`、`get_fund_nav_history()`、`get_fund_portfolio()`
- 将结果写入 `_pipeline_data.json` 的 `funds` 字段（以基金代码为 key）

### 2. `calc_var_impact.py` — 写入 var 字段

**当前**：接受命令行参数，输出到 stdout
**修改后**：读取 `_pipeline_data.json`，计算后写入 `var` 字段

关键逻辑：
- 读取 `_pipeline_data.json` 的 `constraints.existing_var` 和 `candidates`
- 对每只候选基金调用 `calc_marginal_var()`
- 将结果写入 `_pipeline_data.json` 的 `var` 字段

### 3. `search_news.py` — 写入 news 字段

**当前**：模板脚本，只输出空模板
**修改后**：读取候选列表，调用 Tavily 搜索，写入 `news` 字段

关键逻辑：
- 从 `_pipeline_data.json` 读取候选基金及其板块映射
- 对每只基金搜索利多/利空新闻（使用 Tavily MCP）
- 将结果写入 `_pipeline_data.json` 的 `news` 字段

### 4. `generate_recommend.py` — 从数据总线读取

**当前**：接受一个 data_json_file 参数
**修改后**：接受 `--pipeline` 参数，直接读取 `_pipeline_data.json`

关键逻辑：
- 新增 `--pipeline` 模式：读取 `_pipeline_data.json`
- 从 `candidates` + `funds` + `var` + `news` 四个字段组装报告数据
- 保持向后兼容：原有单文件模式仍可用

### 5. `SKILL.md` Step 7 更新

**修改内容**：
- Step 7.1：运行 `validate_funds.py` → 写入 `_pipeline_data.json["funds"]`
- Step 7.2：运行 `calc_var_impact.py` → 写入 `_pipeline_data.json["var"]`
- Step 7.3：运行 `search_news.py` → 写入 `_pipeline_data.json["news"]`
- Step 7.4：运行 `generate_recommend.py --pipeline` → 读取完整数据生成报告

## 实施步骤

| 步骤 | 文件 | 操作 |
|------|------|------|
| 1 | `validate_funds.py` | 重写：读取 candidates.json → 调用 AKShare → 写入 pipeline["funds"] |
| 2 | `calc_var_impact.py` | 修改：读取 pipeline.json → 计算 → 写入 pipeline["var"] |
| 3 | `search_news.py` | 重写：读取 pipeline.json → 调用 Tavily MCP → 写入 pipeline["news"] |
| 4 | `generate_recommend.py` | 修改：新增 --pipeline 模式，从 _pipeline_data.json 读取 |
| 5 | `SKILL.md` | 更新 Step 7 为 4 步流水线 |
| 6 | `evals/evals.json` | 追加 P3 断言（B7-B9） |
| 7 | `PLAN-P3.md` | 本文档 |

## 断言设计（evals.json 追加）

### B7-pipeline-data-bus
- **描述**：_pipeline_data.json 必须包含 funds/var/news 三个字段
- **prompt**：运行完整流水线后检查 _pipeline_data.json
- **assertions**：
  - `contains`: `funds` — 文件应包含 funds 字段
  - `contains`: `var` — 文件应包含 var 字段
  - `contains`: `news` — 文件应包含 news 字段

### B8-report-includes-var
- **描述**：最终报告必须包含 VaR 数值（非"无"或"N/A"）
- **prompt**：运行 /fund:recommend，检查报告
- **assertions**：
  - `contains`: `增加 VaR` — 报告应包含 VaR 影响描述
  - `not_contains`: `N/A 元` — 不应出现 N/A 占位

### B9-report-includes-news
- **描述**：最终报告必须包含新闻正文（非"无"）
- **prompt**：运行 /fund:recommend，检查报告
- **assertions**：
  - `contains`: `利多` — 报告应包含利多新闻
  - `contains`: `利空` — 报告应包含利空新闻
  - `not_contains`: `利多：无` — 不应出现"无"占位

## 风险与注意事项

1. **AKShare 调用耗时**：首次 import 约 10 秒，每只基金查询约 2-3 秒
   - 缓解：validate_funds.py 只在需要时调用，且可并行

2. **Tavily 调用限制**：免费版每月 1000 次搜索
   - 缓解：每只基金只搜 2 次（利多+利空），3 只候选 = 6 次

3. **向后兼容**：generate_recommend.py 保留原有单文件模式
   - 原因：其他调用方可能仍使用旧接口

4. **数据一致性**：所有脚本写入同一文件，需要按顺序执行
   - 缓解：SKILL.md 明确标注执行顺序

## 验证方案

1. **单元测试**：每个脚本独立运行，验证输出格式
2. **集成测试**：完整执行 Step 0-7，检查 _pipeline_data.json 完整性
3. **报告验证**：检查最终报告中 VaR 和新闻部分不再显示"无"
