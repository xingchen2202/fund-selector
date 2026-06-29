# P6 研究发现 — Tavily英文新闻问题

## 根因分析

### 问题现象

2026-06-29 两份报告的新闻板块：
- weekly报告：全部英文（Tavily来源）
- recommend报告：英文机器翻译风格，三只基金新闻完全相同

### 数据流分析

```
当前数据流：

search_with_akshare(fund_code, sector)
  ├─ stock_news_em(symbol=fund_code)
  │   ├─ 成功 → 按板块关键词过滤 → 返回中文新闻 ✅
  │   └─ 失败 (KeyError: 'code') → 进入下一步 ❌
  ├─ news_cctv(date=ds)
  │   ├─ 有匹配板块关键词 → 返回中文新闻 ✅
  │   └─ 无匹配 → 返回空 ❌
  └─ 两者都为空 → fallback to Tavily ❌ (英文)
```

### 关键问题

1. **stock_news_em 报错**：AKShare API 对某些基金代码返回格式不一致
2. **news_cctv 覆盖有限**：细分板块（如"有色"）在新闻联播中无报道
3. **Tavily fallback**：AKShare 失败时返回英文，违反中文新闻需求

### 修复方向

完全移除 Tavily，AKShare 失败时标注"无相关新闻"。

## 相关文件路径

- `.claude/skills/fund-recommend/scripts/search_news.py` — 新闻搜索（fund-recommend）
- `.claude/skills/fund-weekly-report/scripts/search_news.py` — 新闻搜索（fund-weekly-report）
- `.claude/skills/fund-recommend/evals/evals.json` — 断言文件
