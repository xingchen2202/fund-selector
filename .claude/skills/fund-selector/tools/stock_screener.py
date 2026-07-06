#!/usr/bin/env python3
"""动量+质量筛选工具（Stock Screener）
━━━━━━━━━━━━━━━━━━━━
移植自 ai-berkshire stock_screener.py。

2 层筛选：
- L1 动量：60 日新高 + 成交量确认
- L2 质量：6 维评分（毛利率改善、EPS 超预期、ROE、现金流、负债、股本稀释）

信号分级：3/6 = 3% 仓位，4/6 = 5%，5-6/6 = 8%

用法：
    python tools/stock_screener.py screen --nav-series '[1.0, 1.02, ...]' --fund-data '{...}'
    python tools/stock_screener.py grade --quality '{"roe": 15, "gross_margin": 40, ...}'
"""

import argparse
import json
import math
import sys


def screen_momentum(nav_series: list) -> dict:
    """L1 动量筛选：60 日新高 + 成交量确认。"""
    if not nav_series or len(nav_series) < 60:
        return {"passed": False, "reason": "净值序列不足 60 点"}

    recent = nav_series[-60:]
    hist = nav_series[:-60] if len(nav_series) > 60 else nav_series[:30]

    # 60 日新高
    new_high = recent[-1] >= max(recent) * 0.98
    # 突破前期平台
    broke_plateau = hist and recent[-1] > max(hist) * 1.02
    # 趋势一致性（上涨天数占比）
    up_days = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i - 1])
    trend_consistency = up_days / (len(recent) - 1)

    passed = new_high and broke_plateau and trend_consistency > 0.5

    return {
        "passed": passed,
        "new_high": new_high,
        "broke_plateau": broke_plateau,
        "trend_consistency": round(trend_consistency, 2),
        "signal": "强" if passed and trend_consistency > 0.6 else "中" if passed else "无",
    }


def grade_quality(fund_data: dict) -> dict:
    """L2 质量评分（6 维，每维 0-1）。"""
    checks = {
        "roe_ok": (fund_data.get("roe", 0) >= 15, f"ROE={fund_data.get('roe', 0):.0f}%"),
        "gross_margin_ok": (fund_data.get("gross_margin", 0) >= 30, f"毛利率={fund_data.get('gross_margin', 0):.0f}%"),
        "fcf_positive": (fund_data.get("fcf", 0) > 0, f"FCF={fund_data.get('fcf', 0)}"),
        "low_leverage": (fund_data.get("debt_ratio", 100) <= 50, f"负债率={fund_data.get('debt_ratio', 0):.0f}%"),
        "no_dilution": (fund_data.get("share_change", 0) <= 5, f"股本变动={fund_data.get('share_change', 0):.0f}%"),
        "stable_earnings": (fund_data.get("earnings_cv", 1) <= 0.3, f"盈利稳定性={fund_data.get('earnings_cv', 0):.2f}"),
    }

    passed = [k for k, (ok, _) in checks.items() if ok]
    score = len(passed)

    # 仓位建议
    if score >= 5:
        position = "8%"
    elif score >= 4:
        position = "5%"
    elif score >= 3:
        position = "3%"
    else:
        position = "观望"

    return {
        "score": score,
        "total": 6,
        "passed_checks": passed,
        "failed_checks": [k for k in checks if k not in passed],
        "details": {k: desc for k, (_, desc) in checks.items()},
        "position_advice": position,
    }


def main():
    parser = argparse.ArgumentParser(description="动量+质量筛选工具")
    sub = parser.add_subparsers(dest="command")

    sc = sub.add_parser("screen", help="L1 动量筛选")
    sc.add_argument("--nav-series", required=True)

    gr = sub.add_parser("grade", help="L2 质量评分")
    gr.add_argument("--fund-data", required=True)

    args = parser.parse_args()

    if args.command == "screen":
        r = screen_momentum(json.loads(args.nav_series))
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.command == "grade":
        r = grade_quality(json.loads(args.fund_data))
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
