# PLAN-P6: 新闻数据源完全切换为AKShare，移除Tavily

## 问题现状

虽然 P5 已将主要数据源改为 AKShare，但当前实现仍存在以下问题：

1. **Tavily 仍作为备用**：当 AKShare 失败时 fallback 到 Tavily，返回英文内容
2. **stock_news_em 频繁报错**：`KeyError: 'code'` 导致个股新闻获取失败
3. **news_cctv 覆盖面有限**：新闻联播只有宏观新闻，细分板块（如"有色"）无匹配
4. **三只基金新闻完全相同**：Tavily 返回通用市场摘要，无差异化

## 修复方案

### 核心原则
**完全移除 Tavily，只使用 AKShare。** 当 AKShare 无法获取新闻时，标注"无相关新闻"而非 fallback 到英文内容。

### 改进点

#### 1. stock_news_em 错误处理增强
当前 `stock_news_em` 对某些基金代码报 `KeyError: 'code'`。这是因为 AKShare 返回的 DataFrame 列名可能变化。改进：
- 增加列名模糊匹配（支持 `news_title`、`title`、`新闻标题` 等）
- 增加日期列模糊匹配
- 异常时返回空列表而非崩溃

#### 2. news_cctv 搜索窗口扩展
当前 weekly-report 只查 3 天，fund-recommend 已扩展到 7 天。统一为 7 天。

#### 3. 新增：东方财富个股新闻接口
AKShare 的 `stock_news_em` 是基于东方财富的个股新闻。对于 ETF/LOF 基金，可以尝试用基金代码对应的股票前缀搜索。对于纯 ETF 联接基金，使用 `news_cctv` 作为唯一数据源。

#### 4. 完全移除 Tavily
- 删除 `search_with_tavily` 函数
- 删除 `SECTOR_TAVILY_QUERIES` / `TAVILY_PARAMS`
- 删除 `import os` 获取 `TAVILY_API_KEY` 的代码
- AKShare 无结果时，统一标注"未找到明显利多/利空（AKShare无相关新闻）"

## 文件修改清单

### .claude/skills/fund-recommend/scripts/search_news.py

1. 删除 `TAVILY_PARAMS`
2. 删除 `SECTOR_TAVILY_QUERIES`
3. 删除 `search_with_tavily` 函数
4. `main()` 中移除 Tavily fallback 逻辑
5. 移除 `import os`
6. 改进 `search_with_akshare` 中的列名匹配

### .claude/skills/fund-weekly-report/scripts/search_news.py

1. 删除 `TAVILY_PARAMS`
2. 删除 `search_with_tavily` 函数
3. `main()` 中移除 Tavily fallback 逻辑
4. 移除 `import os`
5. `news_cctv` 搜索窗口从 3 天扩展到 7 天
6. 改进 `search_with_akshare` 中的列名匹配

## 验证断言

```json
{
  "id": "B6-no-english-news",
  "description": "P6：报告中不应出现英文新闻",
  "prompt": "运行/fund:recommend和/fund:report，检查新闻板块",
  "assertions": [
    {
      "type": "not_contains",
      "value": "As of June 2026",
      "description": "不应出现英文开头的时间描述"
    },
    {
      "type": "not_contains",
      "value": "China's central bank announced",
      "description": "不应出现英文央行公告"
    },
    {
      "type": "not_contains",
      "value": "gold prices have dropped to",
      "description": "不应出现英文黄金价格描述"
    },
    {
      "type": "not_contains",
      "value": "Hang Seng Tech Index includes",
      "description": "不应出现英文港股科技描述"
    },
    {
      "type": "not_contains",
      "value": "data_source: tavily",
      "description": "不应使用Tavily数据源"
    }
  ]
}
```

## 预期效果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| Tavily 依赖 | AKShare失败时fallback到Tavily | 完全移除 |
| 英文新闻 | AKShare失败时出现 | 永远不出现 |
| 新闻语言 | 中英混合 | 纯中文 |
| 空结果处理 | 返回英文摘要 | 标注"无相关新闻" |
