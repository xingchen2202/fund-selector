#!/usr/bin/env python3
"""
search_news.py — Tavily 搜索板块新闻（利多+利空）
━━━━━━━━━━━━━━━━━━━━
对每只候选基金搜索板块近 7 天新闻。
实际执行时由 Claude 直接调用 Tavily MCP 工具。
"""
import json
import sys


def main():
    """
    实际执行时，Claude 会调用：
    - tavily_search(query="XX板块 利好 政策 2026年6月")
    - tavily_search(query="XX板块 风险 下跌 2026年6月")

    此脚本输出搜索模板。
    """
    template = {
        "sector_news": [],
        "unavailable": False,
    }
    print(json.dumps(template, ensure_ascii=False, indent=2))
    print("\n[提示] 此脚本为模板。实际执行时，请由 Claude 直接调用 Tavily MCP 工具。")


if __name__ == "__main__":
    main()
