# P6 修复进度 — 2026-06-29

## 状态：已规划，待用户确认执行

### 问题
- 两份报告的新闻板块仍在使用Tavily作为fallback，返回英文内容
- stock_news_em 对某些基金代码报 KeyError 导致 fallback 到 Tavily
- 三只基金新闻完全相同（Tavily返回通用摘要）

### 方案
- 完全移除Tavily依赖
- 增强stock_news_em错误处理
- news_cctv搜索窗口统一为7天
- AKShare无结果时标注"无相关新闻"

### 产物
- `.planning/PLAN-P6.md` — 完整修复计划
- `.planning/findings.md` — 根因分析
- `.planning/task_plan.md` — 任务计划（已更新）
- `.planning/progress.md` — 本文档

### 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `fund-recommend/scripts/search_news.py` | 修改 | 移除Tavily，增强列名匹配 |
| `fund-weekly-report/scripts/search_news.py` | 修改 | 移除Tavily，扩展CCTV窗口 |
| `evals/evals.json` | 修改 | 追加B6断言 |
