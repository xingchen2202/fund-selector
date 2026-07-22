#!/usr/bin/env python3
"""压力测试工具（Stress Tester）— 极端行情估计与组合承压测试
━━━━━━━━━━━━━━━━━━━━
移植自 FUND_ANALYSIS_WORKFLOW.md Step5，从"文档说明"升级为"可执行计算"。

零外部依赖 — 仅 Python stdlib (math, json, argparse)。

用法：
    python tools/stress_tester.py estimate-drawdown --drawdowns -0.25 -0.18 --correlation 0.7
    python tools/stress_tester.py stress-test --drawdowns -0.25 -0.18 --amounts 2000 1500 --correlation 0.7
"""

import argparse
import json
import math
import sys
import io

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 极端情景系数（历史极端行情比平均更差）
EXTREME_FACTOR = 1.2
# 可承受回撤阈值（默认 -25%）
MAX_TOLERABLE_DRAWDOWN = -0.25


def estimate_extreme_drawdown(historical_drawdowns: list, correlation: float = 0.7) -> dict:
    """基于历史回撤 + 相关性，估计组合极端行情回撤。

    Args:
        historical_drawdowns: 各基金历史最大回撤列表（负数，如 [-0.25, -0.18]）
        correlation: 基金间相关性（0-1，默认 0.7）

    Returns:
        dict: 包含平均回撤、极端估计、相关性调整、承受能力判断
    """
    if not historical_drawdowns:
        return {"error": "回撤列表不能为空"}

    avg_dd = sum(historical_drawdowns) / len(historical_drawdowns)
    extreme_dd = avg_dd * EXTREME_FACTOR

    # 相关性调整：高相关性 → 极端回撤更大（分散效果差）
    correlation_adjustment = 1 + (correlation - 0.5) * 0.3
    adjusted_dd = extreme_dd * correlation_adjustment

    can_absorb = adjusted_dd > MAX_TOLERABLE_DRAWDOWN

    return {
        "average_drawdown": round(avg_dd, 4),
        "extreme_drawdown": round(extreme_dd, 4),
        "correlation": correlation,
        "correlation_adjustment": round(correlation_adjustment, 4),
        "adjusted_drawdown": round(adjusted_dd, 4),
        "max_tolerable": MAX_TOLERABLE_DRAWDOWN,
        "can_absorb": can_absorb,
        "recommendation": "可承受" if can_absorb else "需降低仓位或增加低相关资产",
    }


def stress_test_portfolio(historical_drawdowns: list, monthly_amounts: list,
                           correlation: float = 0.7, months: int = 12) -> dict:
    """压力测试：极端行情下的定投承受能力。

    Args:
        historical_drawdowns: 各基金历史最大回撤
        monthly_amounts: 各基金月定投金额
        correlation: 基金间相关性
        months: 定投期数（默认 12 个月）

    Returns:
        dict: 压力测试结果
    """
    total_monthly = sum(monthly_amounts)
    total_invested = total_monthly * months

    # 极端回撤估计
    result = estimate_extreme_drawdown(historical_drawdowns, correlation)

    # 极端行情下的浮亏
    extreme_loss = total_invested * abs(result["adjusted_drawdown"])

    # 承受能力：浮亏是否超过总资金的 25%
    loss_ratio = abs(result["adjusted_drawdown"])
    can_absorb = loss_ratio < abs(MAX_TOLERABLE_DRAWDOWN)

    result.update({
        "total_monthly": total_monthly,
        "total_invested": total_invested,
        "months": months,
        "extreme_loss_estimate": round(extreme_loss, 2),
        "loss_ratio": round(loss_ratio, 4),
        "can_absorb": can_absorb,
        "emergency_plan": (
            "无需应急预案" if can_absorb
            else f"浮亏 >{abs(MAX_TOLERABLE_DRAWDOWN):.0%} 时启动应急预案：暂停加仓 + 季度复盘"
        ),
    })

    return result


def main():
    parser = argparse.ArgumentParser(description="压力测试工具 — 极端行情估计与组合承压测试")
    sub = parser.add_subparsers(dest="command")

    # 子命令 1: 估计极端回撤
    est = sub.add_parser("estimate-drawdown", help="估计组合极端行情回撤")
    est.add_argument("--drawdowns", nargs="+", type=float, required=True,
                     help="各基金历史最大回撤（负数，如 -0.25 -0.18）")
    est.add_argument("--correlation", type=float, default=0.7,
                     help="基金间相关性（0-1，默认 0.7）")

    # 子命令 2: 组合压力测试
    st = sub.add_parser("stress-test", help="极端行情下的定投承受能力")
    st.add_argument("--drawdowns", nargs="+", type=float, required=True,
                    help="各基金历史最大回撤")
    st.add_argument("--amounts", nargs="+", type=float, required=True,
                    help="各基金月定投金额")
    st.add_argument("--correlation", type=float, default=0.7,
                    help="基金间相关性")
    st.add_argument("--months", type=int, default=12,
                    help="定投期数（默认 12）")

    args = parser.parse_args()

    if args.command == "estimate-drawdown":
        result = estimate_extreme_drawdown(args.drawdowns, args.correlation)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "stress-test":
        result = stress_test_portfolio(args.drawdowns, args.amounts, args.correlation, args.months)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
