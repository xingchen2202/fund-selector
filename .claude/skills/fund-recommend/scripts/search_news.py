#!/usr/bin/env python3
"""
search_news.py — 搜索板块新闻，写入 pipeline
━━━━━━━━━━━━━━━━━━━━
读取 _pipeline_data.json 中的 candidates，
优先使用 AKShare 获取东方财富个股新闻，
按板块关键词过滤，只保留近7天内容，
AKShare 失败时回退到 Tavily，
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
REPORTS_DIR = PROJECT_ROOT / "fund-reports"

# 板块关键词映射（用于过滤 AKShare 新闻标题）
SECTOR_KEYWORDS = {
    "银行": ["银行", "金融", "央行", "利率", "信贷"],
    "金融科技": ["金融科技", "数字金融", "区块链", "数字货币", "支付"],
    "人工智能": ["人工智能", "AI", "大模型", "算力", "机器学习"],
    "半导体": ["半导体", "芯片", "集成电路", "封装", "光刻"],
    "美股纳指": ["纳斯达克", "美股", "美股科技", "QDII"],
    "黄金": ["黄金", "金价", "贵金属", "避险"],
    "港股科技": ["港股", "恒生科技", "南向", "港股通"],
    "科创板": ["科创板", "科创50", "注册制", "硬科技"],
    "科技成长": ["科技", "芯片", "AI", "半导体", "人工智能"],
    "美股QDII": ["纳斯达克", "美股", "QDII", "海外"],
    "债券固收": ["债券", "利率", "固收", "信用债", "国债"],
    "港股": ["港股", "恒生", "港股通", "南向"],
    "均衡": ["A股", "市场", "配置", "价值", "成长"],
    "FOF": ["FOF", "基金中基金", "资产配置"],
}

# Tavily 调用参数（备用）
TAVILY_PARAMS = {
    "days": 7,
    "max_results": 3,
    "search_depth": "basic",
}

# Tavily 搜索词模板
SECTOR_TAVILY_QUERIES = {
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


def read_candidates():
    """从 step2 文件读取候选列表"""
    try:
        script_dir = Path(__file__).parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from pipeline import read_step
        data = read_step("step2")
        return data.get("top10", [])
    except Exception:
        return []


def write_news(data):
    """写入 step5 文件"""
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from pipeline import write_step
    write_step("step5", {"news": data})


def is_within_7_days(date_str):
    """检查日期是否在最近7天内"""
    if not date_str:
        return False
    try:
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
            try:
                dt = datetime.strptime(date_str[:19], fmt)
                return (datetime.now() - dt).days <= 7
            except ValueError:
                continue
        return False
    except Exception:
        return False


def matches_sector_keywords(title, sector):
    """检查新闻标题是否包含板块关键词"""
    if not title:
        return False
    keywords = SECTOR_KEYWORDS.get(sector, [])
    return any(kw in title for kw in keywords)


def search_with_akshare(fund_code, sector):
    """
    使用 AKShare 获取新闻，按板块关键词过滤。
    优先使用 stock_news_em（个股新闻），失败时用 news_cctv（新闻联播）。
    返回 (bullish_list, bearish_list) — 每条是 (title, date) 元组。
    """
    try:
        import akshare as ak
    except ImportError:
        print(f"[WARN] akshare 未安装，跳过 AKShare 新闻", file=sys.stderr)
        return [], []

    bullish = []
    bearish = []

    # 1. 尝试 stock_news_em（个股新闻）
    try:
        df = ak.stock_news_em(symbol=fund_code)
        if df is not None and not df.empty:
            # 确定列名
            title_col = None
            date_col = None
            for c in df.columns:
                c_str = str(c)
                if "标题" in c_str or "新闻标题" in c_str or "title" in c_str.lower():
                    title_col = c
                if "时间" in c_str or "日期" in c_str or "date" in c_str.lower() or "time" in c_str.lower():
                    date_col = c

            if title_col is None:
                title_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            if date_col is None:
                for c in df.columns:
                    if c != title_col:
                        date_col = c
                        break

            for _, row in df.iterrows():
                title = str(row[title_col]) if title_col else ""
                date_str = str(row[date_col]) if date_col else ""

                if not is_within_7_days(date_str):
                    continue

                if matches_sector_keywords(title, sector):
                    is_bearish = any(w in title for w in ["跌", "下跌", "风险", "回调", "亏", "损失", "裁员", "监管"])
                    if is_bearish:
                        bearish.append((title[:100], date_str[:10]))
                    else:
                        bullish.append((title[:100], date_str[:10]))

    except Exception as e:
        # stock_news_em 失败（AKShare API 变化），尝试 news_cctv
        print(f"[WARN] stock_news_em({fund_code}) 失败: {e}，尝试 news_cctv", file=sys.stderr)

    # 2. 如果个股新闻不足，补充 news_cctv（新闻联播）— 查最近7天
    if not bullish or not bearish:
        try:
            import datetime
            today = datetime.date.today()
            for delta in range(0, 7):
                d = today - datetime.timedelta(days=delta)
                ds = d.strftime('%Y%m%d')
                try:
                    df = ak.news_cctv(date=ds)
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            title = str(row.get('title', ''))
                            if matches_sector_keywords(title, sector):
                                is_bearish = any(w in title for w in ["跌", "下跌", "风险", "回调", "下降", "收紧"])
                                if is_bearish:
                                    bearish.append((title[:100], ds))
                                else:
                                    bullish.append((title[:100], ds))
                    if bullish and bearish:
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"[WARN] news_cctv 获取失败: {e}", file=sys.stderr)

    return bullish, bearish


def search_with_tavily(query, api_key):
    """
    使用 Tavily API 搜索新闻（备用方案）。
    返回 (summary, pub_date) 或 (None, None)。
    """
    try:
        from tavily import TavilyClient
    except ImportError:
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
        print(f"[WARN] Tavily 搜索失败: {e}", file=sys.stderr)
        return None, None


def main():
    # 从 step2 读取 candidates
    candidates = read_candidates()
    if not candidates:
        print(json.dumps({"error": "step2 中无 candidates，请先运行 screen_candidates.py"}))
        sys.exit(1)

    # 获取 Tavily API Key（备用）
    import os
    tavily_api_key = os.environ.get("TAVILY_API_KEY", "")

    print(f"[INFO] 搜索 {len(candidates)} 只候选基金的板块新闻...", file=sys.stderr)
    print(f"[INFO] 数据源: AKShare (主) + Tavily (备)", file=sys.stderr)

    news_results = {}
    for c in candidates:
        code = c.get("code", "")
        name = c.get("name", "")
        sector = c.get("sector", "未知")

        # 1. 优先使用 AKShare
        bullish_list, bearish_list = search_with_akshare(code, sector)

        # 2. 如果 AKShare 没有结果，回退到 Tavily
        used_fallback = False
        if not bullish_list and not bearish_list and tavily_api_key:
            queries = SECTOR_TAVILY_QUERIES.get(sector, SECTOR_TAVILY_QUERIES.get("均衡"))
            bullish_summary, bullish_date = search_with_tavily(queries["positive"], tavily_api_key)
            bearish_summary, bearish_date = search_with_tavily(queries["negative"], tavily_api_key)
            used_fallback = True

            if bullish_summary:
                bullish_list = [(bullish_summary, bullish_date or "未知")]
            if bearish_summary:
                bearish_list = [(bearish_summary, bearish_date or "未知")]

        # 3. 格式化输出
        if bullish_list:
            bullish_str = "；".join([f"{t[0]}({t[1]})" for t in bullish_list[:3]])
        elif used_fallback:
            bullish_str = "未找到明显利多"
        else:
            bullish_str = "未找到明显利多（AKShare无相关新闻）"

        if bearish_list:
            bearish_str = "；".join([f"{t[0]}({t[1]})" for t in bearish_list[:3]])
        elif used_fallback:
            bearish_str = "未找到明显利空"
        else:
            bearish_str = "未找到明显利空（AKShare无相关新闻）"

        news_results[code] = {
            "code": code,
            "name": name,
            "sector": sector,
            "bullish": bullish_str,
            "bearish": bearish_str,
            "data_source": "akshare" if not used_fallback else "tavily",
            "bullish_count": len(bullish_list),
            "bearish_count": len(bearish_list),
        }
        print(f"[NEWS] {code} {sector}: 利多={len(bullish_list)}条 利空={len(bearish_list)}条 数据源={'AKShare' if not used_fallback else 'Tavily'}", file=sys.stderr)

    # 写入 step5
    write_news(news_results)
    print(json.dumps(news_results, ensure_ascii=False, indent=2))
    print(f"\n[INFO] 已写入 pipeline['news'] ({len(news_results)} 只基金)", file=sys.stderr)


if __name__ == "__main__":
    main()
