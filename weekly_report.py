#!/usr/bin/env python3
"""
基金持仓周报生成器
━━━━━━━━━━━━━━━━━━━━
读取 portfolio.json，通过 akshare 获取最新净值，
计算每只基金的市值、盈亏、回本涨幅，输出文字报告。

数据获取策略:
  1. 批量获取: fund_open_fund_daily_em() 覆盖绝大多数开放式基金
  2. 回退接口: fund_open_fund_info_em() 覆盖 FOF/QDII 等净值延迟的品种

用法:
    python weekly_report.py              # 生成报告
    python weekly_report.py --update     # 更新 portfolio.json 中的 units / cost_nav
    python weekly_report.py --json       # 输出 JSON 格式（供其他程序消费）

依赖:
    pip install akshare pandas
"""

import json
import sys
import os
import io
from datetime import datetime
from pathlib import Path

# Windows GBK 兼容性修复
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ──────────────────────────────────────────────
# 路径配置
# ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PORTFOLIO_FILE = SCRIPT_DIR / "portfolio.json"

# ──────────────────────────────────────────────
# akshare 延迟导入（首次 import 较慢）
# ──────────────────────────────────────────────
def import_akshare():
    import akshare as ak
    return ak


# ──────────────────────────────────────────────
# 加载持仓
# ──────────────────────────────────────────────
def load_portfolio():
    if not PORTFOLIO_FILE.exists():
        print(f"[ERROR] 找不到持仓文件: {PORTFOLIO_FILE}")
        print("        请先在 portfolio.json 中录入你的基金持仓。")
        sys.exit(1)
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────
# 获取最新净值 — 两步策略
# ──────────────────────────────────────────────
def fetch_nav_batch(fund_codes):
    """
    两步获取净值:
    Step 1: 批量从 fund_open_fund_daily_em() 获取（高效）
    Step 2: 对缺失/空值的基金，用 fund_open_fund_info_em() 回退

    返回 dict: {code: (nav, nav_date)}
    """
    ak = import_akshare()
    results = {code: (None, None) for code in fund_codes}
    need_fallback = []

    # ── Step 1: 批量接口 ──
    print("  [1/2] 批量获取开放式基金净值...", file=sys.stderr)
    try:
        df_daily = ak.fund_open_fund_daily_em()
        code_col = df_daily.columns[0]       # 基金代码
        name_col = df_daily.columns[1]       # 基金简称
        # 找到最新日期的净值列（格式: YYYY-MM-DD-单位净值）
        nav_cols = [c for c in df_daily.columns if "单位净值" in c]
        nav_cols.sort(reverse=True)           # 最新日期在前
        latest_nav_col = nav_cols[0] if nav_cols else None
        latest_nav_date = latest_nav_col.split("-")[0] if latest_nav_col else None

        for code in fund_codes:
            row = df_daily[df_daily[code_col] == code]
            if not row.empty and latest_nav_col:
                nav_val = row[latest_nav_col].values[0]
                if nav_val and str(nav_val).strip() and str(nav_val) != "nan":
                    results[code] = (float(nav_val), latest_nav_date)
                else:
                    need_fallback.append(code)
            else:
                need_fallback.append(code)
    except Exception as e:
        print(f"  [!] 批量接口异常: {e}", file=sys.stderr)
        need_fallback.extend([c for c in fund_codes if results[c][0] is None])

    # ── Step 2: 回退接口（FOF/QDII 等） ──
    if need_fallback:
        print(f"  [2/2] 回退获取 {len(need_fallback)} 只基金净值 (FOF/QDII)...", file=sys.stderr)
        for i, code in enumerate(need_fallback, 1):
            try:
                df_info = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
                if df_info is not None and not df_info.empty:
                    df_info = df_info.sort_values("净值日期")
                    latest = df_info.iloc[-1]
                    nav = float(latest["单位净值"])
                    nav_date = str(latest["净值日期"])
                    results[code] = (nav, nav_date)
                    print(f"    [{i}/{len(need_fallback)}] {code} ✓ {nav}", file=sys.stderr)
                else:
                    print(f"    [{i}/{len(need_fallback)}] {code} ✗ 无数据", file=sys.stderr)
            except Exception as e:
                print(f"    [{i}/{len(need_fallback)}] {code} ✗ {str(e)[:60]}", file=sys.stderr)

    return results


# ──────────────────────────────────────────────
# 计算持仓数据
# ──────────────────────────────────────────────
def calculate_holdings(portfolio, nav_data):
    """
    计算每只基金的:
    - 当前市值 = units × 最新净值
    - 盈亏金额 = 当前市值 - 成本
    - 盈亏比例 = 盈亏金额 / 成本
    - 回本需涨幅 = |loss%| / (1 - |loss%)

    如果 units == 0（首次运行），用 cost_value / cost_nav 反推份额。
    """
    holdings = []
    for fund in portfolio["funds"]:
        code = fund["code"]
        name = fund["name"]
        units = fund.get("units", 0)
        cost_nav = fund.get("cost_nav", 0)
        cost_value = fund.get("cost_value", 0)

        nav_info = nav_data.get(code)
        if nav_info is None or nav_info[0] is None:
            holdings.append({
                "code": code,
                "name": name,
                "error": "净值获取失败",
            })
            continue

        nav, nav_date = nav_info

        # 首次运行: 用持有金额和净值反推份额
        if units == 0 and cost_nav == 0 and cost_value > 0:
            units = round(cost_value / nav, 4)

        current_value = round(units * nav, 2)
        pnl_amount = round(current_value - cost_value, 2)
        pnl_pct = round(pnl_amount / cost_value * 100, 2) if cost_value != 0 else 0

        # 回本涨幅计算: |loss%| / (1 - |loss%|)
        if pnl_pct < 0:
            recovery_pct = round(abs(pnl_pct) / (100 - abs(pnl_pct)) * 100, 2)
        else:
            recovery_pct = 0

        holdings.append({
            "code": code,
            "name": name,
            "units": units,
            "cost_nav": cost_nav,
            "cost_value": cost_value,
            "nav": nav,
            "nav_date": nav_date,
            "current_value": current_value,
            "pnl_amount": pnl_amount,
            "pnl_pct": pnl_pct,
            "recovery_pct": recovery_pct,
        })

    return holdings


# ──────────────────────────────────────────────
# 输出: 文字报告
# ──────────────────────────────────────────────
def print_report(holdings):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 60)
    print(f"  基金持仓周报 — {now}")
    print("=" * 60)
    print()

    # ── 持仓明细 ──
    print("一、持仓明细")
    print("-" * 64)
    print(f"  {'基金名称':<22} {'代码':<8} {'市值':>8} {'盈亏':>9} {'盈亏%':>7}")
    print("-" * 64)

    total_value = 0.0
    total_cost = 0.0
    profit_funds = []
    loss_funds = []
    failed_funds = []

    for h in holdings:
        if "error" in h:
            failed_funds.append(h)
            continue

        total_value += h["current_value"]
        total_cost += h["cost_value"]

        if h["pnl_pct"] >= 0:
            profit_funds.append(h)
        else:
            loss_funds.append(h)

        sign = "+" if h["pnl_pct"] >= 0 else ""
        name_short = h["name"][:20]
        print(
            f"  {name_short:<22} {h['code']:<8} "
            f"{h['current_value']:>8.2f} "
            f"{sign}{h['pnl_amount']:>8.2f} "
            f"{sign}{h['pnl_pct']:>6.2f}%"
        )

    print("-" * 64)

    # ── 汇总 ──
    total_pnl = round(total_value - total_cost, 2)
    total_pnl_pct = round(total_pnl / total_cost * 100, 2) if total_cost else 0

    print()
    print("二、汇总")
    print(f"  总市值：  ¥{total_value:>10,.2f}")
    print(f"  总成本：  ¥{total_cost:>10,.2f}")
    sign = "+" if total_pnl >= 0 else ""
    print(f"  总盈亏：  {sign}¥{total_pnl:>10,.2f}  ({sign}{total_pnl_pct:.2f}%)")
    print()

    # ── 盈利持仓 ──
    if profit_funds:
        print("三、盈利持仓")
        for h in sorted(profit_funds, key=lambda x: x.get("pnl_pct", 0), reverse=True):
            print(
                f"  ▲ {h['name'][:20]:<20} +{h['pnl_pct']:>6.2f}%  "
                f"(+¥{h['pnl_amount']:,.2f})"
            )
        print()

    # ── 亏损持仓 + 回本涨幅 ──
    if loss_funds:
        print("四、亏损持仓（距回本涨幅）")
        for h in sorted(loss_funds, key=lambda x: x.get("pnl_pct", 0)):
            print(
                f"  ▼ {h['name'][:20]:<20} {h['pnl_pct']:>6.2f}%  "
                f"(¥{h['pnl_amount']:,.2f})  "
                f"→ 回本需 +{h['recovery_pct']:.2f}%"
            )
        print()

    # ── 获取失败 ──
    if failed_funds:
        print("五、数据获取失败")
        for h in failed_funds:
            print(f"  ✗ {h['name']}（{h['code']}）")
        print()

    # ── 免责声明 ──
    print("=" * 60)
    print("  数据来源：天天基金网 (via akshare)")
    print("  仅供参考，不构成投资建议。投资有风险，入市需谨慎。")
    print("=" * 60)


# ──────────────────────────────────────────────
# 输出: JSON 格式
# ──────────────────────────────────────────────
def print_json(holdings):
    output = {
        "report_time": datetime.now().isoformat(),
        "holdings": [],
        "summary": {},
    }
    total_value = 0.0
    total_cost = 0.0
    for h in holdings:
        if "error" not in h:
            total_value += h["current_value"]
            total_cost += h["cost_value"]
        output["holdings"].append(h)

    total_pnl = round(total_value - total_cost, 2)
    output["summary"] = {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": total_pnl,
        "total_pnl_pct": round(total_pnl / total_cost * 100, 2) if total_cost else 0,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


# ──────────────────────────────────────────────
# 更新 portfolio.json（填充 units / cost_nav）
# ──────────────────────────────────────────────
def update_portfolio(portfolio, holdings):
    updated = 0
    for fund in portfolio["funds"]:
        for h in holdings:
            if h["code"] == fund["code"] and "error" not in h:
                fund["units"] = h["units"]
                fund["cost_nav"] = h["nav"]
                updated += 1
                break

    portfolio["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)
    print(f"\n  [✓] 已更新 {updated} 只基金的 units / cost_nav → {PORTFOLIO_FILE}")


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    update_mode = "--update" in args
    json_mode = "--json" in args

    # 1. 加载持仓
    print("  加载持仓数据...", file=sys.stderr)
    portfolio = load_portfolio()
    fund_codes = [f["code"] for f in portfolio["funds"]]

    # 2. 获取最新净值
    print(f"  获取 {len(fund_codes)} 只基金净值...", file=sys.stderr)
    nav_data = fetch_nav_batch(fund_codes)

    # 3. 计算持仓
    print("  计算持仓盈亏...", file=sys.stderr)
    holdings = calculate_holdings(portfolio, nav_data)

    # 4. 输出
    if json_mode:
        print_json(holdings)
    else:
        print_report(holdings)

    # 5. 可选: 更新持仓文件
    if update_mode:
        update_portfolio(portfolio, holdings)


if __name__ == "__main__":
    main()
