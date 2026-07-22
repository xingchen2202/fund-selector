#!/usr/bin/env python3
"""压力测试工具（Stress Tester）— 极端行情估计与组合承压测试
━━━━━━━━━━━━━━━━━━━━
v2.0 升级：分层阈值 + 恢复时间线 + 情景对比 + 应急预案。

零外部依赖 — 仅 Python stdlib (math, json, argparse)。

用法：
    python tools/stress_tester.py estimate-drawdown --drawdowns -0.25 -0.18 --correlation 0.7
    python tools/stress_tester.py stress-test --drawdowns -0.25 -0.18 --amounts 2000 1500 --correlation 0.7
    python tools/stress_tester.py compare-scenarios --drawdowns -0.25 -0.18 --amounts 2000 1500
    python tools/stress_tester.py recovery-timeline --drawdown -0.35 --recovery-rate 0.08
"""

import argparse
import json
import math
import sys
import io

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 极端情景系数
EXTREME_FACTOR = 1.2
# 分层阈值（v2.0 新增）
TIER_THRESHOLDS = {
    "green": -0.10,    # 绿色：可承受，无需预案
    "yellow": -0.25,   # 黄色：可承受但需应急预案
    "red": -0.40,      # 红色：不可承受，需降仓
}


def get_risk_tier(drawdown: float) -> dict:
    """根据回撤幅度返回风险等级。"""
    abs_dd = abs(drawdown)
    if abs_dd <= abs(TIER_THRESHOLDS["green"]):
        return {"tier": "green", "label": "低风险", "action": "无需应急预案"}
    elif abs_dd <= abs(TIER_THRESHOLDS["yellow"]):
        return {"tier": "yellow", "label": "中风险", "action": "需应急预案（暂停加仓+季度复盘）"}
    elif abs_dd <= abs(TIER_THRESHOLDS["red"]):
        return {"tier": "orange", "label": "高风险", "action": "建议降低仓位或增加低相关资产"}
    else:
        return {"tier": "red", "label": "极高风险", "action": "必须降低仓位，考虑止损"}


def estimate_extreme_drawdown(historical_drawdowns: list, correlation: float = 0.7) -> dict:
    """基于历史回撤 + 相关性，估计组合极端行情回撤。"""
    if not historical_drawdowns:
        return {"error": "回撤列表不能为空"}

    avg_dd = sum(historical_drawdowns) / len(historical_drawdowns)
    extreme_dd = avg_dd * EXTREME_FACTOR
    correlation_adjustment = 1 + (correlation - 0.5) * 0.3
    adjusted_dd = extreme_dd * correlation_adjustment

    tier = get_risk_tier(adjusted_dd)

    return {
        "average_drawdown": round(avg_dd, 4),
        "extreme_drawdown": round(extreme_dd, 4),
        "correlation": correlation,
        "correlation_adjustment": round(correlation_adjustment, 4),
        "adjusted_drawdown": round(adjusted_dd, 4),
        "risk_tier": tier["tier"],
        "risk_label": tier["label"],
        "recommendation": tier["action"],
    }


def stress_test_portfolio(historical_drawdowns: list, monthly_amounts: list,
                           correlation: float = 0.7, months: int = 12) -> dict:
    """压力测试：极端行情下的定投承受能力。"""
    total_monthly = sum(monthly_amounts)
    total_invested = total_monthly * months

    result = estimate_extreme_drawdown(historical_drawdowns, correlation)
    if "error" in result:
        return result

    extreme_loss = total_invested * abs(result["adjusted_drawdown"])
    loss_ratio = abs(result["adjusted_drawdown"])

    result.update({
        "total_monthly": total_monthly,
        "total_invested": total_invested,
        "months": months,
        "extreme_loss_estimate": round(extreme_loss, 2),
        "loss_ratio": round(loss_ratio, 4),
        "emergency_plan": _generate_emergency_plan(result["risk_tier"], loss_ratio),
    })

    return result


def compare_scenarios(historical_drawdowns: list, monthly_amounts: list) -> dict:
    """对比不同相关性假设下的压力测试结果。"""
    scenarios = {}
    for corr, label in [(0.3, "低相关"), (0.5, "中相关"), (0.7, "高相关"), (0.9, "极高相关")]:
        result = stress_test_portfolio(historical_drawdowns, monthly_amounts, corr)
        scenarios[label] = {
            "correlation": corr,
            "adjusted_drawdown": result["adjusted_drawdown"],
            "risk_tier": result["risk_tier"],
            "extreme_loss": result["extreme_loss_estimate"],
        }
    return scenarios


def recovery_timeline(drawdown: float, recovery_rate: float = 0.08, monthly_amount: float = 0) -> dict:
    """计算恢复时间线。

    Args:
        drawdown: 回撤幅度（负数）
        recovery_rate: 年化恢复速率
        monthly_amount: 月定投金额（>0 时计算定投摊薄效应）
    """
    abs_dd = abs(drawdown)

    # 定投摊薄效应
    if monthly_amount > 0:
        # 简化：定投摊薄约 40% 的回摊
        dca_mitigation = 0.6
        effective_dd = abs_dd * dca_mitigation
    else:
        effective_dd = abs_dd
        dca_mitigation = 1.0

    # 回本所需月数
    monthly_recovery = recovery_rate / 12
    if monthly_recovery > 0:
        months_to_recover = int(math.ceil(effective_dd / monthly_recovery))
    else:
        months_to_recover = float("inf")

    return {
        "original_drawdown": round(drawdown, 4),
        "dca_mitigation": dca_mitigation,
        "effective_drawdown": round(-effective_dd, 4),
        "recovery_rate_annual": recovery_rate,
        "months_to_recover": months_to_recover,
        "years_to_recover": round(months_to_recover / 12, 1),
    }


def _generate_emergency_plan(tier: str, loss_ratio: float) -> str:
    """根据风险等级生成应急预案。"""
    plans = {
        "green": "无需应急预案，正常持有",
        "yellow": f"浮亏 >{abs(TIER_THRESHOLDS['yellow']):.0%} 时：暂停加仓 + 季度复盘",
        "orange": f"浮亏 >{abs(TIER_THRESHOLDS['red']):.0%} 时：减仓至安全水平 + 增加防御资产",
        "red": "立即减仓至组合回撤 <25%，等待市场企稳",
    }
    return plans.get(tier, "请人工评估")


def main():
    parser = argparse.ArgumentParser(description="压力测试工具 v2.0 — 分层阈值 + 恢复时间线 + 情景对比")
    sub = parser.add_subparsers(dest="command")

    # 子命令 1: 估计极端回撤
    est = sub.add_parser("estimate-drawdown", help="估计组合极端行情回撤")
    est.add_argument("--drawdowns", nargs="+", type=float, required=True)
    est.add_argument("--correlation", type=float, default=0.7)

    # 子命令 2: 组合压力测试
    st = sub.add_parser("stress-test", help="极端行情下的定投承受能力")
    st.add_argument("--drawdowns", nargs="+", type=float, required=True)
    st.add_argument("--amounts", nargs="+", type=float, required=True)
    st.add_argument("--correlation", type=float, default=0.7)
    st.add_argument("--months", type=int, default=12)

    # 子命令 3: 情景对比（v2.0 新增）
    cmp_parser = sub.add_parser("compare-scenarios", help="对比不同相关性假设")
    cmp_parser.add_argument("--drawdowns", nargs="+", type=float, required=True)
    cmp_parser.add_argument("--amounts", nargs="+", type=float, required=True)

    # 子命令 4: 恢复时间线（v2.0 新增）
    rec = sub.add_parser("recovery-timeline", help="计算恢复时间线")
    rec.add_argument("--drawdown", type=float, required=True)
    rec.add_argument("--recovery-rate", type=float, default=0.08)
    rec.add_argument("--monthly-amount", type=float, default=0, help="月定投金额（0=一次性投入）")

    args = parser.parse_args()

    if args.command == "estimate-drawdown":
        result = estimate_extreme_drawdown(args.drawdowns, args.correlation)
    elif args.command == "stress-test":
        result = stress_test_portfolio(args.drawdowns, args.amounts, args.correlation, args.months)
    elif args.command == "compare-scenarios":
        result = compare_scenarios(args.drawdowns, args.amounts)
    elif args.command == "recovery-timeline":
        result = recovery_timeline(args.drawdown, args.recovery_rate, args.monthly_amount)
    else:
        parser.print_help()
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
