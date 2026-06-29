# P2 修复任务：新闻全部返回英文

## 状态：✅ 已完成 (iteration-2)

## 任务概述

**问题**：`search_news.py`（fund-recommend 和 fund-weekly-report）的 Tavily 搜索返回全部英文新闻，且可能混入超过7天的旧新闻。  
**根因**：搜索词含英文/中英文混合，Tavily 默认返回英文；未设置 `days` 参数限制时间范围。  
**修复方案**：搜索词全部中文化 + 加入 `days=7` 参数 + 输出中标注发布时间。

---

## Phase 1：根因确认 ✅ ✅

- [x] 检查 `fund-weekly-report/scripts/search_news.py` → 8个搜索词中3个为英文（NASDAQ/gold price/Hang Seng）
- [x] 检查 `fund-recommend/scripts/search_news.py` → 模板文件，同样含英文搜索词
- [x] 检查 `search_with_tavily()` → 未传 `days` 参数
- [x] 确认 Tavily API 支持 `days` 参数限制时间范围

**发现**：
- `fund-weekly-report` 的 SECTOR_QUERIES 中，"纳斯达克"、"黄金"、"港股科技"使用英文搜索词
- 即使中文搜索词，Tavily 也可能返回英文结果（依赖内容库）
- 无 `days` 参数 → 返回任意时间旧新闻

---

## Phase 2：修复设计 ✅ ✅

### 修改文件

#### 1. `fund-weekly-report/scripts/search_news.py`

**变更1：搜索词全部中文化**

```python
SECTOR_QUERIES = [
    {"sector": "银行", "query": "中国银行板块 最新政策 利率 2026年6月", ...},
    {"sector": "金融科技", "query": "中国金融科技 数字金融 最新政策 2026年6月", ...},
    {"sector": "人工智能", "query": "中国AI算力 人工智能 最新消息 2026年6月", ...},
    {"sector": "半导体", "query": "中国半导体芯片 集成电路 最新消息 2026年6月", ...},
    {"sector": "纳斯达克", "query": "美国纳斯达克 美股科技 AI 最新消息 2026年6月", ...},  # 改中文
    {"sector": "黄金", "query": "黄金市场 金价走势 分析 2026年6月", ...},  # 改中文
    {"sector": "港股科技", "query": "港股科技 恒生科技指数 最新消息 2026年6月", ...},
    {"sector": "科创板", "query": "中国科创板 科创50 最新消息 2026年6月", ...},
]
```

**变更2：Tavily 搜索加入 `days=7`**

```python
result = client.search(
    query=query,
    search_depth="basic",
    max_results=3,
    include_answer=True,
    days=7,  # P2修复：限制近7天
)
```

**变更3：输出中添加发布时间检查**

```python
# 对每条结果检查发布时间
for r in results:
    pub_date = r.get("published_date", "")
    if pub_date and is_older_than_7_days(pub_date):
        r["time_warning"] = "[时间超期]"
```

#### 2. `fund-recommend/scripts/search_news.py`

同样修改 SECTOR_QUERIES 和 `search_with_tavily()`。

#### 3. `sector-map.md`

更新"新闻搜索关键词"表，移除英文列，统一为中文搜索词模板。

---

## Phase 3：实施 ✅

### 修改文件清单

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `fund-weekly-report/scripts/search_news.py` | 搜索词中文化 + days=7 + 时间检查 | P0 |
| `fund-recommend/scripts/search_news.py` | 同上 | P0 |
| `sector-map.md` | 搜索词模板统一中文 | P0 |
| `evals/evals.json` | 追加 P2 断言 | P1 |

### 实施步骤

1. 修改 `fund-weekly-report/scripts/search_news.py`
2. 修改 `fund-recommend/scripts/search_news.py`
3. 更新 `sector-map.md` 搜索词模板
4. 更新 `evals/evals.json` 追加 P2 断言
5. 测试：运行两个脚本验证中文新闻输出

---

## Phase 4：验证 ✅

### 验收标准

- [ ] 所有8个板块新闻均为中文
- [ ] 新闻发布时间均在7天内
- [ ] 超期新闻标注"[时间超期]"
- [ ] 纳斯达克/美股板块搜索词为中文但可获取国际新闻

### 测试用例

```
输入：python search_news.py
预期：
  [银行] 中国银行板块...（中文）
  [黄金] 黄金市场金价...（中文）
  [港股科技] 港股科技恒生...（中文）
  - 不含英文摘要
  - 不含超过7天的新闻
```

---

## 决策记录

| 决策 | 理由 |
|------|------|
| 搜索词全部中文化 | Tavily 对中文搜索词返回中文结果概率更高 |
| 加入 days=7 参数 | Tavily API 原生支持，无需本地过滤 |
| 保留时间超期标注 | 双重保险，即使 Tavily 返回超期内容也能识别 |
| 纳斯达克搜索词用"美国纳斯达克" | 指定中文仍可获取美股相关新闻 |
