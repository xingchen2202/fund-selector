#!/usr/bin/env python3
"""
search_news.py — 搜索候选基金新闻（纯AKShare实现，无Tavily）
━━━━━━━━━━━━━━━━━━━━
读取 step2 候选列表（代码+板块），按板块获取东方财富新闻，
输出按基金代码索引，写入 step5 供 generate_recommend.py 消费。

P6修复：完全移除Tavily，仅使用AKShare。
P7修复：输出格式与 generate_recommend.py 对齐（按代码索引，bullish/bearish）。
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
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from pipeline import read_step, write_step

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
    "均衡": ["A股", "市场", "行情", "投资", "经济"],
}

# 每个板块对应的代表性股票（东方财富代码）
SECTOR_REPRESENTATIVE_STOCKS = {
    "银行": "601398",       # 工商银行
    "金融科技": "000559",    # 神州信息
    "人工智能": "000977",    # 浪潮信息
    "半导体": "002371",      # 北方华创
    "美股纳指": "000001",    # 平安银行
    "黄金": "600547",        # 山东黄金
    "港股科技": "00700",     # 腾讯控股
    "科创板": "688981",      # 中芯国际
    "有色矿业": "600362",    # 江西铜业
    "均衡": "510300",        # 沪深300
}

CUTOFF_DAYS = 7

# 基金名称关键词 → 板块推断（与 screen_candidates.py 保持一致）
SECTOR_NAME_KEYWORDS = {
    "银行": ["银行", "金融"],
    "保险": ["保险"],
    "证券": ["证券", "券商"],
    "半导体": ["半导体", "芯片", "集成电路"],
    "人工智能": ["人工智能", "AI", "智能"],
    "科技成长": ["科技", "成长", "新经济"],
    "黄金": ["黄金", "贵金属", "金价"],
    "有色": ["有色", "金属", "矿业"],
    "港股": ["港股", "恒生"],
    "美股纳指": ["纳斯达克", "美股", "QDII"],
    "科创板": ["科创板", "科创"],
    "新能源": ["新能源", "电动车", "光伏"],
    "医药": ["医药", "医疗", "健康"],
    "消费": ["消费", "白酒", "食品"],
    "债券固收": ["债券", "固收", "中短债"],
    "均衡": ["均衡", "灵活配置", "混合"],
    "FOF": ["FOF", "基金中基金"],
    "军工": ["军工", "国防"],
    "地产": ["地产", "房地产"],
    "环保": ["环保", "碳中和"],
    "汽车": ["汽车", "新能源车"],
    "电力": ["电力", "电网"],
    "传媒": ["传媒", "游戏", "动漫"],
    "农业": ["农业", "养殖"],
}


def infer_sector_by_name(fund_name):
    """根据基金名称关键词推断板块，无法推断返回"均衡" """
    if not fund_name:
        return "均衡"
    for sector, keywords in SECTOR_NAME_KEYWORDS.items():
        for kw in keywords:
            if kw in fund_name:
                return sector
    return "均衡"


def fetch_sector_news(sector):
    """获取某板块的近7天新闻，返回 {positive: [str], negative: [str]}"""
    try:
        import akshare as ak
        stock_code = SECTOR_REPRESENTATIVE_STOCKS.get(sector, "510300")
        df = ak.stock_news_em(symbol=stock_code)
    except Exception as e:
        print(f"[WARN] 东方财富新闻获取失败({sector}): {e}", file=sys.stderr)
        df = None

    keywords = SECTOR_KEYWORDS.get(sector, [sector])
    cutoff = datetime.now() - timedelta(days=CUTOFF_DAYS)

    NEGATIVE_WORDS = [
        "下跌", "风险", "监管", "利空", "回调", "亏损",
        "警示", "暴跌", "崩盘", "退市", "违规", "处罚",
    ]
    POSITIVE_WORDS = [
        "上涨", "利好", "政策支持", "创新高", "突破",
        "增长", "复苏", "扩张", "布局", "机遇",
    ]

    results = {"positive": [], "negative": []}

    if df is None or df.empty:
        return {
            "positive": [f"近{CUTOFF_DAYS}天无明显利多消息"],
            "negative": [f"近{CUTOFF_DAYS}天无明显利空消息"],
        }

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

        # 记录发布时间，格式：标题(日期)
        date_str = pub_time[:10]
        item = f"{title[:50]}({date_str})" if date_str else title[:60]

        is_negative = any(w in text for w in NEGATIVE_WORDS)
        is_positive = any(w in text for w in POSITIVE_WORDS)

        if is_negative and len(results["negative"]) < 2:
            results["negative"].append(item)
        elif is_positive and len(results["positive"]) < 2:
            results["positive"].append(item)

        if len(results["positive"]) >= 2 and len(results["negative"]) >= 2:
            break

    if not results["positive"]:
        results["positive"] = [f"近{CUTOFF_DAYS}天无明显利多消息"]
    if not results["negative"]:
        results["negative"] = [f"近{CUTOFF_DAYS}天无明显利空消息"]

    return results


def main():
    # 读取 step2 获取候选基金列表（代码 + 板块）
    step2 = read_step("step2")
    candidates = step2.get("top10", step2.get("candidates", []))

    if not candidates:
        print("[WARN] step2 中无候选基金，跳过新闻搜索", file=sys.stderr)
        write_step("step5", {"news": {}})
        print(json.dumps({}, ensure_ascii=False, indent=2))
        return

    output = {}
    sector_cache = {}

    for fund in candidates:
        code = fund.get("code", "")
        name = fund.get("name", "")
        sector = fund.get("sector", "均衡")

        # 板块为"未知"时，根据名称推断
        if sector in ("未知", "", None):
            sector = infer_sector_by_name(name)

        # 按板块缓存新闻，避免重复请求
        if sector not in sector_cache:
            sector_cache[sector] = fetch_sector_news(sector)

        news = sector_cache[sector]

        # 取最新一条新闻的发布时间作为 published_date
        latest_item = (news["positive"] + news["negative"])[0]
        published_date = ""
        if "(" in latest_item and latest_item.endswith(")"):
            published_date = latest_item[latest_item.rindex("(") + 1:-1]

        output[code] = {
            "bullish": news["positive"][0],
            "bearish": news["negative"][0],
            "sector": sector,
            "published_date": published_date,
        }

    # 写入 step5（generate_recommend.py 通过 data["news"] 读取）
    write_step("step5", {"news": output})
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n[INFO] 已写入 _pipeline_step5.json（{len(output)} 只基金）", file=sys.stderr)


if __name__ == "__main__":
    main()
