# Task Plan — P6 Tavily完全移除，纯AKShare新闻

## Phase 列表

| Phase | 描述 | 状态 | 依赖 |
|-------|------|------|------|
| Phase 1 | fund-recommend search_news.py 移除Tavily | ⏳ 待开始 | 无 |
| Phase 2 | fund-weekly-report search_news.py 移除Tavily | ⏳ 待开始 | 无 |
| Phase 3 | evals.json 追加 B6 断言 | ⏳ 待开始 | Phase 1-2 |
| Phase 4 | 运行完整流水线验证 | ⏳ 待开始 | 全部 |

---

## Phase 1: fund-recommend search_news.py

**目标**：移除所有 Tavily 相关代码，增强列名匹配

**修改点**：

1. **删除** `TAVILY_PARAMS` 字典
2. **删除** `SECTOR_TAVILY_QUERIES` 字典
3. **删除** `search_with_tavily` 函数
4. **删除** `main()` 中的 Tavily fallback 逻辑
5. **删除** `import os`
6. **改进** `search_with_akshare` 列名匹配：
   ```python
   # 增强列名匹配
   for c in df.columns:
       c_str = str(c).lower()
       if any(k in c_str for k in ["标题", "title", "新闻"]):
           title_col = c
       if any(k in c_str for k in ["时间", "日期", "date", "time", "pub"]):
           date_col = c
   ```
7. **改进** 日期过滤：对 `news_cctv` 返回的日期也做7天过滤

---

## Phase 2: fund-weekly-report search_news.py

**目标**：同 Phase 1，额外扩展 CCTV 窗口

**修改点**：

1. **删除** `TAVILY_PARAMS` 字典
2. **删除** `search_with_tavily` 函数
3. **删除** `main()` 中的 Tavily fallback 逻辑
4. **删除** `import os`
5. **扩展** `news_cctv` 搜索从 3 天到 7 天
6. **改进** `search_with_akshare` 列名匹配（同 Phase 1）
7. **改进** 日期过滤

---

## Phase 3: evals.json 追加 B6 断言

```json
{
  "id": "B6-no-english-news",
  "description": "P6：报告中不应出现英文新闻",
  "prompt": "运行/fund:recommend和fund:report，检查新闻板块",
  "assertions": [
    {"type": "not_contains", "value": "As of June 2026", "description": "不应出现英文开头"},
    {"type": "not_contains", "value": "China's central bank", "description": "不应出现英文央行公告"},
    {"type": "not_contains", "value": "gold prices have dropped", "description": "不应出现英文黄金描述"},
    {"type": "not_contains", "value": "Hang Seng Tech", "description": "不应出现英文港股描述"},
    {"type": "not_contains", "value": "data_source: tavily", "description": "不应使用Tavily数据源"}
  ]
}
```

---

## Phase 4: 验证

1. 清空 pipeline
2. 运行完整 recommend 流程
3. 运行 weekly report 流程
4. 检查两份报告新闻板块全部为中文
5. 确认无 "As of June 2026" 等英文开头

## 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `fund-recommend/scripts/search_news.py` | 修改 | 移除Tavily，增强AKShare |
| `fund-weekly-report/scripts/search_news.py` | 修改 | 移除Tavily，扩展窗口 |
| `evals/evals.json` | 修改 | 追加 B6 断言 |
