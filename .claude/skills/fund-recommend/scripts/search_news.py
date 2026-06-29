#!/usr/bin/env python3
"""
search_news.py — Tavily 搜索板块新闻（利多+利空）
━━━━━━━━━━━━━━━━━━━━
对每只候选基金搜索板块近 7 天新闻。
实际执行时由 Claude 直接调用 Tavily MCP 工具。

P2修复：
  1. 搜索词全部中文化
  2. 加入 days=7 参数
  3. 输出标注发布时间

此脚本输出搜索模板。实际执行时，请由 Claude 直接调用 Tavily MCP 工具。
"""
import json
import sys
import io
from datetime import datetime

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def main():
    """
    实际执行时，Claude 会调用：
    - tavily_search(query="XX板块 利好 政策 2026年6月", days=7)
    - tavily_search(query="XX板块 风险 下跌 2026年6月", days=7)

    days=7 参数限制只返回近7天新闻。
    """
    template = {
        "sector_news": [],
        "unavailable": False,
        "days_filter": 7,
        "language": "zh",
    }
    print(json.dumps(template, ensure_ascii=False, indent=2))
    print("\n[提示] 此脚本为模板。实际执行时，请由 Claude 直接调用 Tavily MCP 工具。")
    print("P2修复要点：")
    print("  1. 搜索词全部使用中文")
    print("  2. tavily_search 必须传入 days=7")
    print("  3. 检查 published_date，超期标注[时间超期]")


if __name__ == "__main__":
    main()
