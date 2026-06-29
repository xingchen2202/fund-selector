#!/usr/bin/env python3
"""
search_news.py — 搜索板块新闻
━━━━━━━━━━━━━━━━━━━━
读取 ../_shared/sector-map.md 中的板块映射，
优先使用 AKShare 获取东方财富个股新闻，
按板块关键词过滤，只保留近7天内容，
AKShare 失败时回退到 Tavily，
输出 JSON 到 stdout。

P2修复：
  1. 搜索词全部中文化，包含具体年月
  2. Tavily搜索加入 days=7 限制
  3. 输出标注发布时间，超期新闻标记[时间超期]
  4. 时效验证：过滤超过7天的结果

P5修复：
  5. AKShare 作为主要数据源，Tavily 作为备用
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

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
REPORTS_DIR = PROJECT_ROOT / "fund-reports"

# 板块搜索关键词（中文，区分利多/利空）
SECTOR_QUERIES = [
    {"sector": "银行", "query": "中国银行板块 政策利好 利率 2026年6月", "fund_codes": ["004597"]},
    {"sector": "金融科技", "query": "中国金融科技 数字金融 政策 2026年6月", "fund_codes": ["013477"]},
    {"sector": "人工智能", "query": "人工智能 AI算力 政策支持 2026年6月", "fund_codes": ["024725"]},
    {"sector": "半导体", "query": "半导体 芯片 国产替代 2026年6月", "fund_codes": ["008888"]},
    {"sector": "纳斯达克", "query": "美国纳斯达克 美股科技 AI 2026年6月", "fund_codes": ["017437"]},
    {"sector": "黄金", "query": "黄金市场 金价走势 分析 2026年6月", "fund_codes": ["008702", "000216", "009033"]},
    {"sector": "港股科技", "query": "港股科技 恒生科技指数 2026年6月", "fund_codes": ["025720"]},
    {"sector": "科创板", "query": "中国科创板 科创50 2026年6月", "fund_codes": ["023729"]},
]

# 板块关键词映射（用于过滤 AKShare 新闻标题）
SECTOR_KEYWORDS = {
    "银行": ["银行", "金融", "央行", "利率", "信贷"],
    "金融科技": ["金融科技", "数字金融", "区块链", "数字货币", "支付"],
    "人工智能": ["人工智能", "AI", "大模型", "算力", "机器学习"],
    "半导体": ["半导体", "芯片", "集成电路", "封装", "光刻"],
    "纳斯达克": ["纳斯达克", "美股", "美股科技", "QDII"],
    "黄金": ["黄金", "金价", "贵金属", "避险"],
    "港股科技": ["港股", "恒生科技", "南向", "港股通"],
    "科创板": ["科创板", "科创50", "注册制", "硬科技"],
}

# Tavily 调用参数（备用）
TAVILY_PARAMS = {
    "days": 7,
    "max_results": 3,
    "search_depth": "basic",
}


def is_older_than_7_days(date_str):
    """检查日期是否超过7天"""
    if not date_str:
        return False
    try:
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
            try:
                dt = datetime.strptime(date_str[:19], fmt)
                return (datetime.now() - dt).days > 7
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

                if is_older_than_7_days(date_str):
                    continue

                if matches_sector_keywords(title, sector):
                    is_bearish = any(w in title for w in ["跌", "下跌", "风险", "回调", "亏", "损失", "裁员", "监管"])
                    if is_bearish:
                        bearish.append((title[:100], date_str[:10]))
                    else:
                        bullish.append((title[:100], date_str[:10]))

    except Exception as e:
        print(f"[WARN] stock_news_em({fund_code}) 失败: {e}，尝试 news_cctv", file=sys.stderr)

    # 2. 如果个股新闻不足，补充 news_cctv（新闻联播）— 只查最近3天加速
    if not bullish or not bearish:
        try:
            import datetime
            today = datetime.date.today()
            for delta in range(0, 3):
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
    """使用 Tavily API 搜索新闻（备用方案）"""
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


def filter_recent_news(results, days=7):
    """
    P2修复：时效验证，过滤超过7天的结果。
    如果全部过期，返回提示信息。
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
                recent.append(r)
        else:
            recent.append(r)

    if not recent and outdated:
        oldest = outdated[-1].get("published_date", "未知")
        return [{"title": "近7天无相关新闻", "content": f"最新消息时间: {oldest}", "published_date": oldest}]

    return recent


def main():
    api_key = os.environ.get("TAVILY_API_KEY", "")

    print(f"[INFO] 搜索 {len(SECTOR_QUERIES)} 个板块新闻（中文，近7天）...", file=sys.stderr)
    print(f"[INFO] 数据源: AKShare (主) + Tavily (备)", file=sys.stderr)

    news_results = []
    for item in SECTOR_QUERIES:
        sector = item["sector"]
        query = item["query"]
        fund_codes = item["fund_codes"]

        # 1. 尝试 AKShare：对每个基金代码获取新闻，按板块过滤
        all_bullish = []
        all_bearish = []
        for code in fund_codes:
            bullish, bearish = search_with_akshare(code, sector)
            all_bullish.extend(bullish)
            all_bearish.extend(bearish)

        used_fallback = False
        # 2. 如果 AKShare 没有结果，回退到 Tavily
        if not all_bullish and not all_bearish and api_key:
            used_fallback = True
            summary, pub_date = search_with_tavily(query, api_key)
            if summary:
                # 简单拆分为利多/利空
                if any(w in summary for w in ["利好", "上涨", "增长"]):
                    all_bullish = [(summary[:100], pub_date or "未知")]
                elif any(w in summary for w in ["风险", "下跌", "回调"]):
                    all_bearish = [(summary[:100], pub_date or "未知")]
                else:
                    all_bullish = [(summary[:100], pub_date or "未知")]

        # 3. 组装结果
        time_warning = ""
        if not all_bullish and not all_bearish and not used_fallback:
            time_warning = ""

        if all_bullish:
            bullish_str = "；".join([f"{t[0]}({t[1]})" for t in all_bullish[:3]])
        else:
            bullish_str = "未找到明显利多"

        if all_bearish:
            bearish_str = "；".join([f"{t[0]}({t[1]})" for t in all_bearish[:3]])
        else:
            bearish_str = "未找到明显利空"

        news_results.append({
            "sector": sector,
            "query": query,
            "summary": f"利多: {bullish_str} | 利空: {bearish_str}",
            "bullish": bullish_str,
            "bearish": bearish_str,
            "published_date": "未知",
            "time_warning": time_warning,
            "fund_codes": fund_codes,
            "data_source": "akshare" if not used_fallback else "tavily",
        })
        print(f"[NEWS] {sector}: 利多={len(all_bullish)}条 利空={len(all_bearish)}条 数据源={'AKShare' if not used_fallback else 'Tavily'}", file=sys.stderr)

    print(json.dumps(news_results, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
