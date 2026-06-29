#!/usr/bin/env python3
"""
search_news.py — 搜索板块新闻
━━━━━━━━━━━━━━━━━━━━
读取 ../_shared/sector-map.md 中的板块映射，
使用 Tavily API 搜索各板块近7天新闻。
输出 JSON 到 stdout。

用法:
    python search_news.py

环境变量:
    TAVILY_API_KEY — Tavily API Key（可选，未设置则跳过）

输出格式:
    [{"sector": "银行", "keywords": "...", "summary": "...", "url": "..."}, ...]
"""

import os
import sys
import json
import io
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 板块搜索关键词（与 sector-map.md 保持一致）
SECTOR_QUERIES = [
    {
        "sector": "银行",
        "query": "中国银行板块 最新政策 利率 2026年6月",
        "fund_codes": ["004597"],
    },
    {
        "sector": "金融科技",
        "query": "中国金融科技 数字金融 最新政策 2026年6月",
        "fund_codes": ["013477"],
    },
    {
        "sector": "人工智能",
        "query": "中国AI算力 人工智能 最新消息 2026年6月",
        "fund_codes": ["024725"],
    },
    {
        "sector": "半导体",
        "query": "中国半导体芯片 集成电路 最新消息 2026年6月",
        "fund_codes": ["008888"],
    },
    {
        "sector": "纳斯达克",
        "query": "NASDAQ US tech stocks AI latest news June 2026",
        "fund_codes": ["017437"],
    },
    {
        "sector": "黄金",
        "query": "gold price outlook analysis June 2026",
        "fund_codes": ["008702", "000216", "009033"],
    },
    {
        "sector": "港股科技",
        "query": "港股科技 恒生科技指数 最新消息 2026年6月",
        "fund_codes": ["025720"],
    },
    {
        "sector": "科创板",
        "query": "中国科创板 科创50 最新消息 2026年6月",
        "fund_codes": ["023729"],
    },
]


def search_with_tavily(query, api_key):
    """
    使用 Tavily API 搜索新闻。
    返回摘要文本，失败返回 None。
    """
    try:
        from tavily import TavilyClient
    except ImportError:
        print("[!] tavily-python 未安装，跳过新闻搜索", file=sys.stderr)
        return None

    try:
        client = TavilyClient(api_key=api_key)
        result = client.search(
            query=query,
            search_depth="basic",
            max_results=3,
            include_answer=True,
        )
        # 提取摘要
        answer = result.get("answer", "")
        if answer:
            return answer[:200]  # 限制长度

        # 无 answer 时拼接 titles
        results = result.get("results", [])
        if results:
            titles = [r.get("title", "") for r in results[:3]]
            return " | ".join(titles)[:200]

        return None
    except Exception as e:
        print(f"[!] Tavily 搜索失败: {e}", file=sys.stderr)
        return None


def main():
    api_key = os.environ.get("TAVILY_API_KEY", "")

    if not api_key:
        print("[WARN] TAVILY_API_KEY 未设置，新闻搜索将跳过", file=sys.stderr)
        print(json.dumps([]))
        sys.exit(0)

    print(f"[INFO] 搜索 {len(SECTOR_QUERIES)} 个板块新闻...", file=sys.stderr)

    news_results = []
    for item in SECTOR_QUERIES:
        summary = search_with_tavily(item["query"], api_key)
        news_results.append({
            "sector": item["sector"],
            "query": item["query"],
            "summary": summary or "搜索不可用",
            "fund_codes": item["fund_codes"],
        })

    print(json.dumps(news_results, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
