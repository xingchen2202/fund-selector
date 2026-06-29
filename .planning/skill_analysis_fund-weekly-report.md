# fund-weekly-report Skill 分析

## 当前状态

| 问题 | 状态 | 触发案例 | 修复方案 |
|------|------|---------|---------|
| P2 新闻返回英文 | ✅ 已修复 | 新闻板块出现英文开头"As of June 2026" | 搜索词中文化 + days=7 + 时间检查 |
| P6 新闻源Tavily英文 | ✅ 已修复 | Tavily对中文财经覆盖不足，返回英文 | 完全移除Tavily，改用AKShare东方财富新闻 |

---

## P6 修复详情

### 触发案例

2026-06-29 周报中新闻板块全部为英文内容（Tavily来源），各板块新闻内容雷同。

### 根因

1. Tavily对中文财经内容覆盖不足，即使使用中文搜索词也主要返回英文来源
2. AKShare `stock_news_em` 对部分基金代码报 KeyError 导致 fallback 到 Tavily
3. `news_cctv` 搜索窗口仅3天，周末无数据时直接 fallback

### 修复方案

1. 完全移除 Tavily 依赖
2. 每个板块使用代表性股票获取东方财富新闻
3. `news_cctv` 搜索窗口扩展到7天
4. `generate_report.py` 支持新新闻格式（dict of dicts）

### 修改文件

| 文件 | 变更 |
|------|------|
| `.claude/skills/fund-weekly-report/scripts/search_news.py` | 完全重写：AKShare东方财富，无Tavily |
| `.claude/skills/fund-weekly-report/scripts/generate_report.py` | 支持新格式 + 新闻来源标注改为"东方财富" |

### 验证结果

全部8个板块新闻均为中文，来自东方财富（AKShare），无英文内容。

---

## P2 修复详情

### 触发案例

2026-06-29 周报中新闻板块出现：
- 英文开头 "As of June 2026, the Hang Seng Tech Index..."
- 混入超过7天的旧新闻（如 "Goldman Sachs predicts..."）

### 根因

1. `search_news.py` 搜索词为英文（如 "NASDAQ US tech"、"Hang Seng tech"）
2. Tavily 搜索未传入 `days=7` 参数
3. 输出未标注发布时间，无法识别超期新闻

### 修复方案

1. 搜索词全部中文化（如 "美国纳斯达克 美股科技 AI 2026年6月"）
2. Tavily 搜索加入 `days=7` 参数
3. 输出新增 `published_date` 和 `time_warning` 字段
4. 新增 `is_older_than_7_days()` 时效验证函数
5. 添加 UTF-8 stdout wrapper（Windows GBK 兼容性）

### 修改文件

| 文件 | 变更 |
|------|------|
| `.claude/skills/fund-weekly-report/scripts/search_news.py` | 搜索词中文化 + days=7 + 时间检查 + UTF-8 wrapper |
| `.claude/skills/fund-recommend/scripts/search_news.py` | 同上（模板文件） |
| `.claude/skills/_shared/sector-map.md` | 搜索词表移除英文列 |
| `.claude/skills/fund-recommend/evals/evals.json` | 3条自动化断言 (B4-B6) |

### 验证结果

全部8个搜索词均为中文，Tavily 调用包含 `days=7`，输出含 `published_date` 和 `time_warning`。

---

## 待修复问题

| 问题 | 状态 | 描述 |
|------|------|------|
| 无 | — | 所有已知问题已修复 |

---

## 迭代记录

| 版本 | 日期 | 变更 |
|------|------|------|
| iteration-1 | 2026-06-24 | 初始版本 |
| iteration-2 | 2026-06-29 | P2 新闻中文化 + 7天过滤 |
| iteration-3 | 2026-06-29 | P6 完全移除Tavily，改用AKShare东方财富 |
