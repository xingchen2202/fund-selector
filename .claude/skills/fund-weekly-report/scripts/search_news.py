#!/usr/bin/env python3
"""
search_news.py — 搜索板块新闻
━━━━━━━━━━━━━━━━━━━━
读取 ../_shared/sector-map.md 中的板块映射，
使用 Tavily API 搜索各板块近7天新闻。
输出 JSON 到 stdout。

P2修复：
  1. 搜索词全部中文化
  2. Tavily搜索加入 days=7 限制
  3. 输出标注发布时间，超期新闻标记[时间超期]

用法:
    python search_news.py

环境变量:
    TAVILY_API_KEY — Tavily API Key（可选，未设置则跳过）

输出格式:
    [{"sector": "银行", "keywords": "...", "summary": "...", "published_date": "...", "time_warning": "..."}, ...]
"""

import os
import sys
import json
import io
from datetime import datetime, timedelta
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 板块搜索关键词（P2修复：全部中文化，要求中文结果）
SECTOR_QUERIES = [
    {
        "sector": "银行",
        "query": "中国银行板块 最新政策 利率 2026年6月 中文",
        "fund_codes": ["004597"],
    },
    {
        "sector": "金融科技",
        "query": "中国金融科技 数字金融 最新政策 2026年6月 中文",
        "fund_codes": ["013477"],
    },
    {
        "sector": "人工智能",
        "query": "中国AI算力 人工智能 最新消息 2026年6月 中文",
        "fund_codes": ["024725"],
    },
    {
        "sector": "半导体",
        "query": "中国半导体芯片 集成电路 最新消息 2026年6月 中文",
        "fund_codes": ["008888"],
    },
    {
        "sector": "纳斯达克",
        "query": "美国纳斯达克 美股科技 AI 最新消息 2026年6月 中文",
        "fund_codes": ["017437"],
    },
    {
        "sector": "黄金",
        "query": "黄金市场 金价走势 分析 2026年6月 中文",
        "fund_codes": ["008702", "000216", "009033"],
    },
    {
        "sector": "港股科技",
        "query": "港股科技 恒生科技指数 最新消息 2026年6月 中文",
        "fund_codes": ["025720"],
    },
    {
        "sector": "科创板",
        "query": "中国科创板 科创50 最新消息 2026年6月 中文",
        "fund_codes": ["023729"],
    },
]


def is_older_than_7_days(date_str):
    """检查日期是否超过7天"""
    try:
        # 尝试多种日期格式
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
            try:
                dt = datetime.strptime(date_str[:19], fmt)
                return (datetime.now() - dt).days > 7
            except ValueError:
                continue
        # 无法解析日期，返回 False（不标记）
        return False
    except Exception:
        return False


def search_with_tavily(query, api_key):
    """
    使用 Tavily API 搜索新闻。
    P2修复：加入 days=7 参数限制时间范围。
    返回摘要文本和发布时间，失败返回 (None, None)。
    """
    try:
        from tavily import TavilyClient
    except ImportError:
        print("[!] tavily-python 未安装，跳过新闻搜索", file=sys.stderr)
        return None, None

    try:
        client = TavilyClient(api_key=api_key)
        result = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=True,
            days=7,
        )
        answer = result.get("answer", "")
        if answer:
            return answer[:300], None

        results = result.get("results", [])
        if results:
            titles = []
            for r in results[:5]:
                title = r.get("title", "")
                if any('一' <= c <= '鿿' for c in title):
                    titles.insert(0, title)
                else:
                    titles.append(title)
            pub_date = results[0].get("published_date", "")
            return " | ".join(titles[:3])[:300], pub_date

        return None, None
    except Exception as e:
        print(f"[!] Tavily 搜索失败: {e}", file=sys.stderr)
        return None, None


def main():
    api_key = os.environ.get("TAVILY_API_KEY", "")

    if not api_key:
        print("[WARN] TAVILY_API_KEY 未设置，新闻搜索将跳过", file=sys.stderr)
        print(json.dumps([]))
        sys.exit(0)

    print(f"[INFO] 搜索 {len(SECTOR_QUERIES)} 个板块新闻（中文，近7天）...", file=sys.stderr)

    news_results = []
    for item in SECTOR_QUERIES:
        summary, pub_date = search_with_tavily(item["query"], api_key)

        # P2修复：检查是否超期
        time_warning = ""
        if pub_date and is_older_than_7_days(pub_date):
            time_warning = "[时间超期]"

        news_results.append({
            "sector": item["sector"],
            "query": item["query"],
            "summary": summary or "搜索不可用",
            "published_date": pub_date or "未知",
            "time_warning": time_warning,
            "fund_codes": item["fund_codes"],
        })

    print(json.dumps(news_results, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
