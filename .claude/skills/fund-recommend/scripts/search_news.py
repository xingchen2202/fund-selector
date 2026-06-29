#!/usr/bin/env python3
"""
search_news.py — Tavily 搜索板块新闻（利多+利空）
━━━━━━━━━━━━━━━━━━━━
对每只候选基金搜索板块近 7 天新闻。
实际执行时由 Claude 直接调用 Tavily MCP 工具。

P2修复：
  1. 搜索词全部中文化，区分利多/利空
  2. 加入 days=7 参数
  3. 输出标注发布时间，超期新闻标记[时间超期]
  4. 时效验证：过滤超过7天的结果
"""
import json
import sys
import io
from datetime import datetime, timedelta

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# P2修复：板块搜索关键词（中文，区分利多/利空）
SECTOR_QUERIES = {
    "银行": {
        "positive": "中国银行板块 政策利好 最新消息 2026年6月",
        "negative": "银行板块 风险 利空 监管 2026年6月"
    },
    "金融科技": {
        "positive": "金融科技 监管政策 利好 A股 2026年6月",
        "negative": "金融科技 监管收紧 风险 2026年6月"
    },
    "人工智能": {
        "positive": "人工智能 政策支持 A股 利好 2026年6月",
        "negative": "人工智能 泡沫 监管 算力短缺 2026年6月"
    },
    "半导体": {
        "positive": "半导体 芯片 国产替代 利好 2026年6月",
        "negative": "半导体 出口限制 供应链 风险 2026年6月"
    },
    "美股纳指": {
        "positive": "纳斯达克 科技股 上涨 QDII 2026年6月",
        "negative": "美股 回调 美联储 加息 风险 2026年6月"
    },
    "黄金": {
        "positive": "黄金 价格上涨 避险 需求 2026年6月",
        "negative": "黄金 回调 美元走强 抛压 2026年6月"
    },
    "港股科技": {
        "positive": "恒生科技 港股 上涨 南向资金 2026年6月",
        "negative": "港股 外资流出 监管 下跌 2026年6月"
    },
    "科创板": {
        "positive": "科创板 政策支持 上涨 2026年6月",
        "negative": "科创板 回调 估值压力 2026年6月"
    },
}


# P2修复：Tavily调用参数（限制7天内）
TAVILY_PARAMS = {
    "days": 7,           # 只返回7天内的新闻
    "max_results": 3,
    "search_depth": "basic",
}


def filter_recent_news(results, days=7):
    """
    P2修复：时效验证，过滤超过7天的结果。
    返回近期结果列表。如果全部过期，返回提示信息。
    """
    recent = []
    outdated = []
    cutoff = datetime.now() - timedelta(days=days)

    for r in results:
        pub_date = r.get("published_date")
        if pub_date:
            try:
                pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                if pub_dt.replace(tzinfo=None) >= cutoff:
                    recent.append(r)
                else:
                    outdated.append(r)
            except (ValueError, TypeError):
                recent.append(r)  # 解析失败时保留
        else:
            recent.append(r)  # 无时间信息时保留

    # 如果全部过期，返回提示
    if not recent and outdated:
        oldest = outdated[-1].get("published_date", "未知")
        return [{"title": "近7天无相关新闻", "content": f"最新消息时间: {oldest}", "published_date": oldest}]

    return recent


def main():
    """
    实际执行时，Claude 会调用：
    - tavily_search(query=sector_query["positive"], days=7)
    - tavily_search(query=sector_query["negative"], days=7)

    然后调用 filter_recent_news() 过滤超期结果。
    """
    template = {
        "sector_news": [],
        "unavailable": False,
        "days_filter": 7,
        "language": "zh",
        "queries": {k: v for k, v in SECTOR_QUERIES.items()},
    }
    print(json.dumps(template, ensure_ascii=False, indent=2))
    print("\n[提示] 此脚本为模板。实际执行时，请由 Claude 直接调用 Tavily MCP 工具。")
    print("P2修复要点：")
    print("  1. 搜索词全部使用中文，区分 positive/negative")
    print("  2. tavily_search 必须传入 days=7")
    print("  3. filter_recent_news() 过滤超期结果")
    print("  4. 全部过期时返回'近7天无相关新闻'提示")


if __name__ == "__main__":
    main()
