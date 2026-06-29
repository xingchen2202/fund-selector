#!/usr/bin/env python3
"""
search_news.py — 搜索板块新闻，写入 pipeline
━━━━━━━━━━━━━━━━━━━━
读取 _pipeline_data.json 中的 candidates，
使用 Tavily API 搜索各板块近 7 天新闻（利多+利空），
写入 _pipeline_data.json["news"]。
"""
import json
import sys
import io
from datetime import datetime, timedelta
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
PIPELINE_FILE = PROJECT_ROOT / "fund-reports" / "_pipeline_data.json"

# 板块搜索关键词（中文，区分利多/利空）
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
    "科技成长": {
        "positive": "科技成长 A股 人工智能 芯片 利好 2026年6月",
        "negative": "科技股 回调 估值过高 监管 2026年6月"
    },
    "美股QDII": {
        "positive": "纳斯达克 科技股 AI 上涨 2026年6月",
        "negative": "美股 回调 美联储 风险 2026年6月"
    },
    "债券固收": {
        "positive": "债券市场 利率下行 利好 2026年6月",
        "negative": "债券 利率上行 风险 2026年6月"
    },
    "港股": {
        "positive": "港股 恒生指数 上涨 南向资金 2026年6月",
        "negative": "港股 外资流出 下跌 风险 2026年6月"
    },
    "均衡": {
        "positive": "A股 均衡配置 价值 利好 2026年6月",
        "negative": "A股 市场调整 风险 2026年6月"
    },
}

# Tavily 调用参数
TAVILY_PARAMS = {
    "days": 7,
    "max_results": 3,
    "search_depth": "basic",
}


def read_pipeline():
    if PIPELINE_FILE.exists():
        with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def write_pipeline(key, data):
    pipeline = read_pipeline()
    pipeline[key] = data
    PIPELINE_FILE.parent.mkdir(exist_ok=True)
    with open(PIPELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(pipeline, f, ensure_ascii=False, indent=2)


def search_with_tavily(query, api_key):
    """
    使用 Tavily API 搜索新闻。
    返回 (summary, pub_date) 或 (None, None)。
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
            search_depth=TAVILY_PARAMS["search_depth"],
            max_results=TAVILY_PARAMS["max_results"],
            include_answer=True,
            days=TAVILY_PARAMS["days"],
        )
        answer = result.get("answer", "")
        if answer:
            return answer[:300], None

        results = result.get("results", [])
        if results:
            # 优先选中文标题
            titles = []
            for r in results[:3]:
                title = r.get("title", "")
                if any('一' <= c <= '鿿' for c in title):
                    titles.insert(0, title)
                else:
                    titles.append(title)
            pub_date = results[0].get("published_date", "")
            return " | ".join(titles)[:300], pub_date

        return None, None
    except Exception as e:
        print(f"[!] Tavily 搜索失败: {e}", file=sys.stderr)
        return None, None


def main():
    pipeline = read_pipeline()
    candidates = pipeline.get("candidates", [])

    if not candidates:
        print(json.dumps({"error": "pipeline 中无 candidates 字段"}))
        print("[提示] 请先运行 screen_candidates.py 生成候选列表", file=sys.stderr)
        sys.exit(1)

    api_key = ""
    if not api_key:
        # 尝试从环境变量获取
        import os
        api_key = os.environ.get("TAVILY_API_KEY", "")

    if not api_key:
        print("[WARN] TAVILY_API_KEY 未设置，新闻搜索将跳过", file=sys.stderr)
        # 写入空结果
        write_pipeline("news", {})
        print(json.dumps({"error": "TAVILY_API_KEY 未设置", "news": {}}))
        sys.exit(0)

    print(f"[INFO] 搜索 {len(candidates)} 只候选基金的板块新闻...", file=sys.stderr)

    news_results = {}
    for c in candidates:
        code = c.get("code", "")
        name = c.get("name", "")
        sector = c.get("sector", "未知")

        queries = SECTOR_QUERIES.get(sector, SECTOR_QUERIES.get("均衡"))

        # 搜索利多
        bullish_summary, bullish_date = search_with_tavily(queries["positive"], api_key)
        # 搜索利空
        bearish_summary, bearish_date = search_with_tavily(queries["negative"], api_key)

        news_results[code] = {
            "code": code,
            "name": name,
            "sector": sector,
            "bullish": bullish_summary or "未找到明显利多",
            "bearish": bearish_summary or "未找到明显利空",
            "bullish_date": bullish_date or "未知",
            "bearish_date": bearish_date or "未知",
        }
        print(f"[NEWS] {code} {sector}: 利多={'有' if bullish_summary else '无'} 利空={'有' if bearish_summary else '无'}", file=sys.stderr)

    # 写入 pipeline
    write_pipeline("news", news_results)
    print(json.dumps(news_results, ensure_ascii=False, indent=2))
    print(f"\n[INFO] 已写入 pipeline['news'] ({len(news_results)} 只基金)", file=sys.stderr)


if __name__ == "__main__":
    main()
