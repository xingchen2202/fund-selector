# Task Plan — Iteration 3: P7/P8/P9 修复

> 修复最大回撤过滤、VaR 假精确、新闻分类错误三个数据质量缺陷

## Phase 列表

| Phase | 描述 | 状态 | 依赖 |
|-------|------|------|------|
| Phase 1 | P7 — 最大回撤过滤器修复 | ✅ complete | 无 |
| Phase 2 | P8 — VaR 真实波动率计算 | ✅ complete | 无 |
| Phase 3 | P9 — 新闻正负面分类修复 | ✅ complete | 无 |
| Phase 4 | evals.json 追加 P7/P8/P9 断言 | ✅ complete | Phase 1-3 |
| Phase 5 | 运行完整流水线验证 | ✅ complete | 全部 |

---

## Phase 1: P7 — 最大回撤过滤器

### 问题
- 003593（混合型）最大回撤 -75.55%，远超 25% 阈值，仍被推荐
- 166001（混合型）最大回撤 -68.94%，远超 25% 阈值，仍被推荐
- `generate_recommend.py` 只显示回撤，不过滤

### 根因
1. `validate_funds.py` 不持有回撤数据（MCP 数据在 step3）
2. `generate_recommend.py` 读取 `max_drawdown` 但无过滤函数
3. 单一 `max_drawdown` 字段语义不明（成立以来 vs 近3年）

### 修改点

#### 1. SKILL.md Step 3 — 要求 Claude 提取两个回撤字段
```markdown
调用2：get_fund_nav_history(fund_code=fund_code, period="3y")
  → 提取：
    - drawdown_3y: 近3年最大回撤（净值序列计算，窗口3年）
    - drawdown_inception: 成立以来最大回撤（API 返回值）
    - drawdown_label: "近3年" 或 "成立以来"
```

#### 2. generate_recommend.py — 新增 filter_by_drawdown()
```python
DRAWDOWN_THRESHOLDS = {
    "股票型": 0.35,
    "混合型": 0.25,
    "债券型": 0.10,
}
DRAWDOWN_RELAXED = 0.50  # 成立以来数据放宽阈值

def filter_by_drawdown(candidates, fund_details):
    # 优先用 drawdown_3y，缺失时用 drawdown_inception + 放宽阈值
    # 排除超阈值基金，打印 [EXCLUDE] 日志
```

#### 3. generate_recommend.py — 报告标注时间范围
```python
# 显示时标注：
#   最大回撤（近3年）：-19.94%
#   最大回撤（成立以来）：-75.55%
```

#### 4. rule-definitions.md — 明确阈值适用时间范围
```markdown
### 最大回撤过滤规则
- 股票型：近3年最大回撤 > -35% → 排除
- 混合型：近3年最大回撤 > -25% → 排除
- 债券型：近3年最大回撤 > -10% → 排除
- 数据不可用时：使用成立以来数据，阈值放宽至 -50%
- 报告中每个回撤数字必须标注时间范围
```

---

## Phase 2: P8 — VaR 真实波动率计算

### 问题
- 三只基金（混合型/价值型/有色ETF）VaR 增量完全相同（45.82元）
- `calc_var_impact.py` 使用固定 `new_fund_vol=0.15`

### 根因
- 未从 NAV 序列计算真实历史波动率
- 所有基金共用同一波动率假设

### 修改点

#### calc_var_impact.py — 基于 NAV 序列计算波动率
```python
def compute_annual_volatility(nav_series):
    """从净值序列计算年化波动率（无 numpy依赖）"""
    navs = [item["nav"] for item in sorted(nav_series, key=lambda x: x["date"])]
    returns = [(navs[i] - navs[i-1]) / navs[i-1] for i in range(1, len(navs))]
    return std_dev(returns) * math.sqrt(252)

def compute_marginal_var(investment, annual_vol, existing_var, correlation=0.5):
    """月度 VaR（95%）= 投资金额 × 年化波动率 × 1.645 × sqrt(21/252)"""
    monthly_var = investment * annual_vol * 1.645 * math.sqrt(21 / 252)
    # 组合边际 VaR（考虑相关性）
    combined = math.sqrt(existing_var**2 + monthly_var**2 + 2*correlation*existing_var*monthly_var)
    return combined - existing_var
```

#### calc_var_impact.py — 读取 step3 的 NAV 序列
```python
# 从 step3 读取每只基金的 nav_history
step3 = read_step("step3")
for fund in verified_funds:
    nav_series = fund.get("nav_history")  # Claude 写入的净值序列
    if nav_series and len(nav_series) > 30:
        vol = compute_annual_volatility(nav_series)
    else:
        vol = None  # 标注"数据不足"
```

#### 报告输出
- 有数据：`加入 5% 仓位预计增加 VaR：XX.XX 元`
- 无数据：`VaR：数据不足，无法计算（净值序列缺失）`

---

## Phase 3: P9 — 新闻正负面分类修复

### 问题
- "贵金属板块大幅走弱，多家银行收紧个人贵金属业务" → 标为利多 ❌
- 6/8 板块显示"近7天无明显消息"

### 根因
1. `NEGATIVE_WORDS` 缺少常见利空词（走弱、收紧、下滑等）
2. 正负面词冲突时无保守原则
3. 单一新闻源 + 严格关键词匹配 → 大量板块无结果

### 修改点

#### 1. 补充 NEGATIVE_WORDS（两个文件）
```python
NEGATIVE_WORDS = [
    "下跌", "风险", "监管", "利空", "回调", "亏损",
    "警示", "暴跌", "崩盘", "退市", "违规", "处罚",
    "走弱", "收紧", "下滑", "承压", "下行", "限制",
    "暂停", "罚款", "缩水", "撤资", "减持", "抛售",
    "叫停", "整顿", "暴雷", "收紧", "限制", "收紧",
]
```

#### 2. 矛盾分类保守原则
```python
if is_negative and is_positive:
    # 同时含正负面词 → 优先标为利空（保守原则）
    results["negative"].append(item)
elif is_negative:
    results["negative"].append(item)
elif is_positive:
    results["positive"].append(item)
```

#### 3. 扩大新闻源（降级链）
```python
def fetch_sector_news(sector):
    # 主源：stock_news_em(representative_stock)
    # 降级1：stock_news_em("000001") 全市场新闻 + 板块关键词
    # 降级2：news_economic_baidu(category="股票") + 板块关键词
    # 全部失败 → "近7天无明显消息"
```

---

## Phase 4: evals.json 追加断言

```json
{
  "id": "B7-drawdown-filter",
  "description": "P7：最大回撤超阈值的基金应被排除",
  "assertions": [
    {"type": "not_contains", "value": "最大回撤：-75.55%", "description": "003593不应出现在推荐中"},
    {"type": "not_contains", "value": "最大回撤：-68.94%", "description": "166001不应出现在推荐中"},
    {"type": "source_contains", "value": "drawdown_3y", "description": "step3应包含drawdown_3y字段"},
    {"type": "source_contains", "value": "filter_by_drawdown", "description": "generate_recommend.py应包含过滤函数"}
  ]
},
{
  "id": "B8-var-unique",
  "description": "P8：不同基金的VaR增量不应完全相同",
  "assertions": [
    {"type": "source_contains", "value": "compute_annual_volatility", "description": "calc_var_impact.py应计算真实波动率"},
    {"type": "source_contains", "value": "nav_history", "description": "应从NAV序列读取数据"},
    {"type": "source_not_contains", "value": "new_fund_vol=0.15", "description": "不应使用固定波动率"}
  ]
},
{
  "id": "B9-news-sentiment",
  "description": "P9：新闻正负面分类应正确",
  "assertions": [
    {"type": "source_contains", "value": "走弱", "description": "NEGATIVE_WORDS应包含走弱"},
    {"type": "source_contains", "value": "收紧", "description": "NEGATIVE_WORDS应包含收紧"},
    {"type": "source_contains", "value": "is_negative and is_positive", "description": "应有矛盾分类保守原则"}
  ]
}
```

---

## Phase 5: 验证

1. 清空 pipeline 文件
2. 运行完整 recommend 流程
3. 检查：
   - 回撤超阈值基金被排除（stderr 有 [EXCLUDE] 日志）
   - 各基金 VaR 数值不同
   - 新闻利空分类正确（"走弱"不在利多）
4. 运行 evals.json 全部断言

---

## 文件修改清单

| 文件 | 操作 | 涉及问题 |
|------|------|---------|
| `fund-recommend/scripts/generate_recommend.py` | 修改 | P7 |
| `fund-recommend/scripts/calc_var_impact.py` | 重写 | P8 |
| `fund-recommend/scripts/search_news.py` | 修改 | P9 |
| `fund-weekly-report/scripts/search_news.py` | 修改 | P9 |
| `_shared/rule-definitions.md` | 修改 | P7 |
| `fund-recommend/SKILL.md` | 修改 | P7 (Step 3 回撤字段) |
| `evals/evals.json` | 修改 | P7/P8/P9 断言 |
