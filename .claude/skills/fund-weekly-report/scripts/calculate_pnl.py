#!/usr/bin/env python3
"""
calculate_pnl.py — 计算基金持仓盈亏
━━━━━━━━━━━━━━━━━━━━
读取 portfolio.json 和 fetch_nav.py 的输出（JSON），
计算每只基金的市值、盈亏金额、盈亏百分比、距回本需涨幅。
输出 JSON 到 stdout。

用法:
    python calculate_pnl.py <portfolio_json_path> <nav_json_path>
    或: python fetch_nav.py portfolio.json | python calculate_pnl.py portfolio.json -

退出码:
    0 — 成功
    1 — 输入错误
"""

import sys
import json
import io
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def calculate(portfolio, nav_data):
    """核心计算逻辑"""
    holdings = []
    nav_map = {item["code"]: item for item in nav_data if item.get("nav")}

    total_value = 0.0
    total_cost = 0.0

    for fund in portfolio["funds"]:
        code = fund["code"]
        name = fund["name"]
        units = fund.get("units", 0)
        cost_nav = fund.get("cost_nav", 0)
        cost_value = fund.get("cost_value", 0)

        nav_entry = nav_map.get(code)
        if not nav_entry:
            holdings.append({
                "code": code,
                "name": name,
                "error": "净值不可用",
            })
            continue

        nav = nav_entry["nav"]
        nav_date = nav_entry["nav_date"]

        # 当前市值
        current_value = round(units * nav, 2)
        # 成本总额
        total_cost_fund = round(units * cost_nav, 2) if cost_nav > 0 else cost_value
        # 盈亏
        pnl_amount = round(current_value - total_cost_fund, 2)
        pnl_pct = round(pnl_amount / total_cost_fund * 100, 2) if total_cost_fund != 0 else 0.0
        # 距回本需涨幅
        recovery_pct = 0.0
        if pnl_pct < 0:
            recovery_pct = round(abs(pnl_pct) / (100 - abs(pnl_pct)) * 100, 2)

        total_value += current_value
        total_cost += total_cost_fund

        holdings.append({
            "code": code,
            "name": name,
            "units": units,
            "cost_nav": cost_nav,
            "cost_value": total_cost_fund,
            "nav": nav,
            "nav_date": nav_date,
            "current_value": current_value,
            "pnl_amount": pnl_amount,
            "pnl_pct": pnl_pct,
            "recovery_pct": recovery_pct,
        })

    # 组合汇总
    total_pnl = round(total_value - total_cost, 2)
    total_pnl_pct = round(total_pnl / total_cost * 100, 2) if total_cost else 0.0

    return {
        "holdings": holdings,
        "summary": {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
        },
    }


def main():
    if len(sys.argv) < 3:
        print("[ERROR] 用法: python calculate_pnl.py <portfolio.json> <nav.json 或 ->",
              file=sys.stderr)
        sys.exit(1)

    portfolio_path = Path(sys.argv[1])
    nav_source = sys.argv[2]

    if not portfolio_path.exists():
        print(f"[ERROR] portfolio.json 不存在: {portfolio_path}", file=sys.stderr)
        sys.exit(1)

    with open(portfolio_path, "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    # 读取 nav 数据：文件或 stdin
    if nav_source == "-":
        nav_data = json.load(sys.stdin)
    else:
        nav_path = Path(nav_source)
        if not nav_path.exists():
            print(f"[ERROR] nav.json 不存在: {nav_path}", file=sys.stderr)
            sys.exit(1)
        with open(nav_path, "r", encoding="utf-8") as f:
            nav_data = json.load(f)

    result = calculate(portfolio, nav_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
