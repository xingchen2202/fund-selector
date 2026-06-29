#!/usr/bin/env python3
"""
search_news.py — 搜索板块新闻（纯AKShare实现，无Tavily）
━━━━━━━━━━━━━━━━━━━━
使用 AKShare 东方财富新闻接口获取中文财经新闻，
按板块关键词过滤，只保留近7天内容。

P6修复：完全移除Tavily，仅使用AKShare。
每个板块使用代表性股票获取新闻。
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

# 板块关键词映射
SECTOR_KEYWORDS = {
    "银行": ["银行", "利率", "存款准备金", "央行", "LPR", "存款"],
    "金融科技": ["金融科技", "支付", "数字金融", "监管", "互联网金融"],
    "人工智能": ["人工智能", "AI", "大模型", "算力", "智能体"],
    "半导体": ["芯片", "半导体", "光刻机", "封装", "集成电路"],
    "美股纳指": ["纳斯达克", "美股", "科技股", "QDII", "美联储"],
    "黄金": ["黄金", "金价", "贵金属", "避险", "黄金ETF"],
    "港股科技": ["港股", "恒生科技", "南向资金", "恒生指数", "港股通"],
    "科创板": ["科创板", "科创50", "注册制", "硬科技"],
    "有色矿业": ["有色金属", "铜", "锡", "矿业", "铝", "锂"],
}

# 每个板块对应的代表性股票（东方财富代码）
SECTOR_REPRESENTATIVE_STOCKS = {
    "银行": "601398",       # 工商银行
    "金融科技": "000559",    # 神州信息
    "人工智能": "000977",    # 浪潮信息
    "半导体": "002371",      # 北方华创
    "美股纳指": "000001",    # 平安银行（含美股概念）
    "黄金": "600547",        # 山东黄金
    "港股科技": "00700",     # 腾讯控股
    "科创板": "688981",      # 中芯国际
    "有色矿业": "600362",    # 江西铜业
}

CUTOFF_DAYS = 7


def fetch_eastmoney_news(sector):
    """获取东方财富财经新闻（使用板块代表性股票）"""
    try:
        import akshare as ak
        stock_code = SECTOR_REPRESENTATIVE_STOCKS.get(sector, "000001")
        df = ak.stock_news_em(symbol=stock_code)
        return df
    except Exception as e:
        print(f"[WARN] 东方财富新闻获取失败({sector}): {e}", file=sys.stderr)
        return None


def filter_by_sector(df, sector):
    """按板块关键词过滤新闻"""
    keywords = SECTOR_KEYWORDS.get(sector, [sector])
    cutoff = datetime.now() - timedelta(days=CUTOFF_DAYS)
    results = {"positive": [], "negative": []}

    NEGATIVE_WORDS = [
        "下跌", "风险", "监管", "利空", "回调", "亏损",
        "警示", "暴跌", "崩盘", "退市", "违规", "处罚"
    ]
    POSITIVE_WORDS = [
        "上涨", "利好", "政策支持", "创新高", "突破",
        "增长", "复苏", "扩张", "布局", "机遇"
    ]

    if df is None:
        return {"positive": ["新闻获取失败"], "negative": ["新闻获取失败"]}

    for _, row in df.iterrows():
        # 兼容多种列名格式
        title = str(
            row.get("新闻标题", "")
            or row.get("title", "")
            or row.get("news_title", "")
            or ""
        )
        content = str(
            row.get("新闻内容", "")
            or row.get("content", "")
            or row.get("news_content", "")
            or ""
        )
        pub_time = str(
            row.get("发布时间", "")
            or row.get("datetime", "")
            or row.get("date", "")
            or row.get("time", "")
            or ""
        )

        # 时效过滤
        try:
            pub_dt = datetime.strptime(pub_time[:19], "%Y-%m-%d %H:%M:%S")
            if pub_dt < cutoff:
                continue
        except Exception:
            pass

        # 关键词匹配
        text = title + content
        if not any(kw in text for kw in keywords):
            continue

        # 正负面分类
        is_negative = any(w in text for w in NEGATIVE_WORDS)
        is_positive = any(w in text for w in POSITIVE_WORDS)

        item_title = title[:60]

        if is_negative and len(results["negative"]) < 2:
            results["negative"].append(item_title)
        elif is_positive and len(results["positive"]) < 2:
            results["positive"].append(item_title)

        if len(results["positive"]) >= 2 and len(results["negative"]) >= 2:
            break

    if not results["positive"]:
        results["positive"] = [f"近{CUTOFF_DAYS}天无明显利多消息"]
    if not results["negative"]:
        results["negative"] = [f"近{CUTOFF_DAYS}天无明显利空消息"]

    return results


def main(sectors):
    output = {}
    for sector in sectors:
        df = fetch_eastmoney_news(sector)
        output[sector] = filter_by_sector(df, sector)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sectors = sys.argv[1:] if len(sys.argv) > 1 else list(SECTOR_KEYWORDS.keys())
    main(sectors)
