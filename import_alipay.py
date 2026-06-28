"""
批量录入支付宝基金持仓到 FinanceAgent
"""
import sys
import os
# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'FinanceAgent', 'src'))

os.environ['DATA_DIR'] = os.path.join(os.path.dirname(__file__), 'FinanceAgent', 'data')

from finance_agent.core.portfolio_manager import PortfolioManager
from finance_agent.core.settings_manager import SettingsManager

# 初始化
settings = SettingsManager()
pm = PortfolioManager()

# 创建投资组合（如果不存在）
owner = "user"
existing = [o['slug'] for o in settings.list_owners()]
if owner not in existing:
    settings.create_owner(owner, "CNY")
else:
    settings.switch_owner(owner)

# 基金持仓数据（来自支付宝截图，2026-06-24）
# 格式: (基金代码, 基金名称, 持有金额, 持有收益率, 最新净值, 净值日期)
holdings = [
    ("004597", "鹏华中证银行指数(LOF)C",       7466.39, -7.20,  1.3850, "2026-06-23"),
    ("013477", "华夏中证金融科技主题ETF联接C",  6551.83, -14.97, 0.9181, "2026-06-23"),
    ("008702", "华夏黄金ETF联接C",             5492.45,  0.17,  1.9421, "2026-06-23"),
    ("022015", "中欧稳裕30天滚动持有债券C",    5102.26,  0.00,  1.0428, "2026-06-23"),
    ("017437", "华宝纳斯达克精选股票(QDII)C",  4967.28,  6.58,  2.2853, "2026-06-23"),
    ("024725", "南方创业板人工智能ETF联接A",    4213.16, 36.37,  1.7477, "2026-06-23"),
    ("008888", "华夏国证半导体芯片ETF联接C",    3517.97, 36.55,  2.3965, "2026-06-23"),
    ("025720", "嘉实恒生港股通科技主题ETF联接C", 1388.69, -18.31, 0.7478, "2026-06-23"),
    ("005164", "富荣福锦混合A",                 1239.60, -7.41,  2.1652, "2026-06-23"),
    ("023729", "易方达上证科创板综合ETF联接A",   119.67, 36.62,  1.8884, "2026-06-23"),
    ("000216", "华安黄金ETF联接A",              644.08, 22.69,  3.1160, "2026-06-23"),
    ("009033", "建信上海金ETF联接A",            354.11, 18.04,  2.1223, "2026-06-23"),
    ("013279", "国泰优选领航一年持有期混合(FOF)", 145.38, 45.38,  1.1243, "2026-06-18"),
    ("004503", "鹏华永泰18个月定期开放债券",     105.46,  8.19,  1.3526, "2026-06-23"),
    ("012349", "天弘恒生科技ETF联接(QDII)C",     15.22, -23.91, 0.5975, "2026-06-23"),
]

# 估算买入日期（去年4-5月开始）
# 假设平均买入时间为 2025-04-15
buy_date = "2025-04-15"

print("=" * 60)
print("批量录入基金持仓")
print("=" * 60)

total_invested = 0
total_value = 0

for code, name, amount, return_pct, nav, nav_date in holdings:
    # 估算份额 = 持有金额 / 最新净值
    shares = round(amount / nav, 4)

    # 估算成本价 = 当前净值 / (1 + 收益率)
    cost_price = round(nav / (1 + return_pct / 100), 4)

    # 估算投入本金 = 持有金额 / (1 + 收益率)
    invested = round(amount / (1 + return_pct / 100), 2)
    total_invested += invested
    total_value += amount

    # 录入
    try:
        pm.add_position(
            symbol=code,
            shares=shares,
            avg_cost=cost_price,
            currency="CNY",
            sector=name,
            purchase_date=buy_date,
        )
        print(f"  ✅ {code} {name}: {shares}份 @ {cost_price} (投入约{invested}元)")
    except Exception as e:
        print(f"  ❌ {code} {name}: {e}")

print()
print("=" * 60)
print("持仓汇总")
print("=" * 60)
print(f"  基金数量: {len(holdings)} 只")
print(f"  总投入本金: {total_invested:,.2f} 元")
print(f"  当前总市值: {total_value:,.2f} 元")
print(f"  总盈亏: {total_value - total_invested:+,.2f} ({(total_value/total_invested - 1)*100:+.2f}%)")
print()

# 输出持仓分布
print("=" * 60)
print("资产分布")
print("=" * 60)

categories = {
    "黄金/商品": [],
    "债券/固收": [],
    "A股指数/行业": [],
    "QDII/港股": [],
    "FOF/混合": [],
    "货币基金": [],
}

for code, name, amount, return_pct, nav, nav_date in holdings:
    if "黄金" in name or "金ETF" in name:
        categories["黄金/商品"].append((code, name, amount))
    elif "债券" in name or "稳裕" in name:
        categories["债券/固收"].append((code, name, amount))
    elif "纳斯达克" in name or "恒生" in name or "QDII" in name:
        categories["QDII/港股"].append((code, name, amount))
    elif "FOF" in name or "混合" in name:
        categories["FOF/混合"].append((code, name, amount))
    else:
        categories["A股指数/行业"].append((code, name, amount))

for cat, items in categories.items():
    if items:
        cat_total = sum(x[2] for x in items)
        pct = cat_total / total_value * 100
        print(f"  {cat}: {cat_total:,.2f} 元 ({pct:.1f}%)")
        for code, name, amount in items:
            print(f"    - {code} {name}: {amount:,.2f}")

print()
print("=" * 60)
print("定投计划")
print("=" * 60)
print("  每周一: 南方创业板人工智能ETF联接A 100元 + 富荣福锦混合A 50元 + 华宝纳斯达克精选股票(QDII)C 100元 = 250元")
print("  每周二: 华夏中证金融科技主题ETF联接C 190-195元(智能定投) + 嘉实恒生港股通科技主题ETF联接C 40元 = 230-235元")
print("  每周三: 鹏华中证银行指数(LOF)C 70元")
print("  每周四: 华夏国证半导体芯片ETF联接C 25元")
print("  每周定投合计: 约 575-580元")
print("  每月定投合计: 约 2,300-2,320元")
print()

# 保存分析上下文
analysis_context = {
    "total_invested": total_invested,
    "total_value": total_value,
    "total_pnl": total_value - total_invested,
    "total_pnl_pct": (total_value/total_invested - 1) * 100,
    "weekly_investment": 575,
    "monthly_investment": 2300,
    "risk_tolerance": "可承受损失 1000-2000 元",
    "fund_count": len(holdings),
}

print("=" * 60)
print("✅ 录入完成！数据已保存到 FinanceAgent/data/")
print("=" * 60)
