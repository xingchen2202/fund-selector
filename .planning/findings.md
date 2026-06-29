# Iteration 3 研究发现 — P7/P8/P9 数据质量缺陷

## P7 — 最大回撤过滤器失效

### 问题现象
2026-06-29 recommend_20260629.txt：
- 003593（国泰景气行业灵活配置混合）：最大回撤 -75.55%，混合型阈值 25%，未被排除
- 166001（中欧新趋势混合A）：最大回撤 -68.94%，混合型阈值 25%，未被排除

### 根因分析

**代码路径追踪**：

1. `validate_funds.py` 第 136 行：
   ```python
   "max_drawdown": None,  # 由 Claude 通过 MCP 填充
   ```
   validate_funds.py 不获取回撤数据，留为 None。

2. 回撤数据由 Claude 通过 `get_fund_nav_history` MCP 获取，写入 step3。
   但 MCP 返回的字段语义模糊 — "成立以来最大回撤" 而非 "近3年最大回撤"。

3. `generate_recommend.py` 第 213-214 行：
   ```python
   max_dd = fund_detail.get("max_drawdown")
   max_dd_str = f"{max_dd:+.2f}%" if max_dd is not None else "待补充"
   ```
   只显示，不过滤。**整个代码库无任何 drawdown 过滤逻辑**。

4. `generate_recommend.py` 第 68-76 行 `limit_candidates()` 只按评分排序取前3，
   没有回撤阈值检查。

### 关键缺陷
- **缺陷 A**：过滤逻辑完全缺失（不是 bug，是功能未实现）
- **缺陷 B**：单字段 `max_drawdown` 无法区分成立以来 vs 近3年
- **缺陷 C**：rule-definitions.md 阈值表未注明适用时间范围

### 修复方向
在 `generate_recommend.py` 的 `limit_candidates` 之前插入 `filter_by_drawdown()` 步骤。
要求 Claude 在 step3 中写入 `drawdown_3y` 和 `drawdown_inception` 两个字段。

---

## P8 — VaR 计算使用固定值

### 问题现象
2026-06-29 recommend_20260629.txt：
- 003593（混合型）：加入 5% 仓位预计增加 VaR：45.82 元
- 166001（价值型）：加入 5% 仓位预计增加 VaR：45.82 元
- 018167（有色ETF）：加入 5% 仓位预计增加 VaR：45.82 元

三只风险特征完全不同的基金，VaR 增量精确到分相同。

### 根因分析

**代码路径追踪**：

1. `calc_var_impact.py` 第 60-78 行：
   ```python
   def calc_marginal_var(
       new_fund_value: float,
       existing_value: float,
       existing_var: float,
       new_fund_vol: float = 0.15,  # ← 固定值！
       correlation: float = 0.5,
   ) -> dict:
       new_fund_var = new_fund_value * new_fund_vol / math.sqrt(12)
       ...
   ```
   所有基金使用相同的 `new_fund_vol=0.15`（15% 年化波动率）。

2. 第 100-108 行：
   ```python
   for c in candidates:
       result = calc_marginal_var(new_fund_value, existing_value, existing_var)
       # 未传入 new_fund_vol → 使用默认值 0.15
   ```
   循环中未传入每只基金的实际波动率。

3. 净值序列（`nav_history`）由 MCP 获取后存在 step3，但 `calc_var_impact.py`
   从未读取 step3 数据。

### 关键缺陷
- **缺陷 A**：固定波动率假设（0.15）不符合实际
- **缺陷 B**：未利用已有的 NAV 时间序列数据
- **缺陷 C**：无数据不足时的降级处理

### 修复方向
`calc_var_impact.py` 读取 step3 的 `nav_history`，计算每只基金的实际年化波动率。
公式：`σ_annual = std(daily_returns) × √252`，`VaR_95 = investment × σ_annual × 1.645 × √(21/252)`。

---

## P9 — 新闻正负面分类错误

### 问题现象
2026-06-29 report_20260629.txt：
```
[黄金] 利多: 贵金属板块大幅走弱，多家银行收紧个人贵金属业务
```
"大幅走弱"、"收紧" 是明显利空词，却被标为利多。

6/8 板块显示"近7天无明显利多/利空消息"。

### 根因分析

**代码路径追踪**：

1. `search_news.py`（两个文件）第 110-113 / 67-70 行：
   ```python
   NEGATIVE_WORDS = [
       "下跌", "风险", "监管", "利空", "回调", "亏损",
       "警示", "暴跌", "崩盘", "退市", "违规", "处罚",
   ]
   ```
   缺少常见利空词：走弱、收紧、下滑、承压、下行、限制、暂停、罚款、撤资等。

2. 分类逻辑（第 166-172 / 115-123 行）：
   ```python
   is_negative = any(w in text for w in NEGATIVE_WORDS)
   is_positive = any(w in text for w in POSITIVE_WORDS)

   if is_negative and len(results["negative"]) < 2:
       results["negative"].append(item)
   elif is_positive and len(results["positive"]) < 2:
       results["positive"].append(item)
   ```
   当 `is_negative=True` 时，即使 `is_positive=True` 也标为利空 — 这本身是对的。
   但问题在于："走弱""收紧"不在 NEGATIVE_WORDS 中，所以 `is_negative=False`，
   而"收紧"被某些正面词（如"政策"在 POSITIVE_WORDS 的"政策支持"）误匹配。

3. 新闻源单一：只用 `stock_news_em(symbol=representative_stock)`，
   代表性个股无新闻时直接返回"无消息"，无降级源。

### 关键缺陷
- **缺陷 A**：NEGATIVE_WORDS 覆盖不足
- **缺陷 B**：矛盾分类时缺少显式保守原则（代码碰巧正确但不清晰）
- **缺陷 C**：单一新闻源，无降级链

### 修复方向
1. 扩充 NEGATIVE_WORDS 列表
2. 显式保守原则：`if is_negative and is_positive → negative`
3. 添加降级新闻源（全市场新闻 → 百度经济）

---

## 相关文件路径

| 文件 | 涉及问题 |
|------|---------|
| `fund-recommend/scripts/generate_recommend.py` | P7 |
| `fund-recommend/scripts/calc_var_impact.py` | P8 |
| `fund-recommend/scripts/search_news.py` | P9 |
| `fund-weekly-report/scripts/search_news.py` | P9 |
| `_shared/rule-definitions.md` | P7 |
| `fund-recommend/SKILL.md` | P7 (Step 3) |
| `fund-recommend/evals/evals.json` | P7/P8/P9 |
