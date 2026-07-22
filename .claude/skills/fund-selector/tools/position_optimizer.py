#!/usr/bin/env python3
"""仓位优化计算器（Position Optimizer）— Kelly/风险平价/最大回撤约束
━━━━━━━━━━━━━━━━━━━━
量化仓位优化方法，帮助投资者确定合理的资产配置比例。

零外部依赖 — 仅 Python stdlib (math, json, argparse)。

用法：
    python tools/position_optimizer.py kelly --win-rate 0.60 --payoff 1.5
    python tools/position_optimizer.py risk-parity --volatilities 0.18 0.04 0.01
    python tools/position_optimizer.py max-drawdown --tolerable -0.20 --fund-dd -0.25
    python tools/position_optimizer.py risk-budget --budget 0.15 --volatilities 0.18 0.04 0.01
"""

import argparse
import json
import math
import sys
import io

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 仓位上下限
MIN_POSITION = 0.0
MAX_POSITION = 0.40
# Kelly 安全系数（半 Kelly）
KELLY_FRACTION = 0.5


def kelly_criterion(win_rate: float, payoff: float) -> dict:
    """Kelly 准则：最优仓位 = (胜率 × 赔率 - 败率) / 赔率。

    Args:
        win_rate: 胜率（0-1）
        payoff: 赔率（盈亏比，如 1.5 表示赚 1.5 元/亏 1 元）
    """
    if payoff <= 0:
        return {"error": "赔率必须 >0"}

    lose_rate = 1 - win_rate
    kelly = (win_rate * payoff - lose_rate) / payoff
    half_kelly = kelly * KELLY_FRACTION
    # 限制在合理范围
    optimal = max(MIN_POSITION, min(MAX_POSITION, half_kelly))

    return {
        "win_rate": win_rate,
        "payoff": payoff,
        "kelly_optimal": round(kelly, 4),
        "kelly_fraction": KELLY_FRACTION,
        "half_kelly": round(half_kelly, 4),
        "recommended_position": round(optimal, 4),
        "position_pct": f"{optimal:.1%}",
    }


def risk_parity(volatilities: list) -> dict:
    """风险平价：各资产对组合风险贡献相等。

    Args:
        volatilities: 各资产波动率列表（如 [0.18, 0.04, 0.01]）
    """
    if not volatilities or any(v <= 0 for v in volatilities):
        return {"error": "波动率必须 >0"}

    inv_vols = [1 / v for v in volatilities]
    total_inv_vol = sum(inv_vols)
    weights = [iv / total_inv_vol for iv in inv_vols]

    # 组合波动率（假设零相关简化）
    portfolio_vol = 1 / sum(inv_vols)

    return {
        "volatilities": volatilities,
        "weights": [round(w, 4) for w in weights],
        "weight_pcts": [f"{w:.1%}" for w in weights],
        "portfolio_volatility": round(portfolio_vol, 4),
    }


def max_drawdown_constraint(tolerable_drawdown: float, fund_max_drawdown: float) -> dict:
    """最大回撤约束：根据可承受回撤反推仓位上限。

    Args:
        tolerable_drawdown: 可承受最大回撤（负数，如 -0.20）
        fund_max_drawdown: 基金历史最大回撤（负数，如 -0.25）
    """
    if tolerable_drawdown >= 0 or fund_max_drawdown >= 0:
        return {"error": "回撤必须为负数"}

    position_limit = abs(tolerable_drawdown) / abs(fund_max_drawdown)
    safe_limit = position_limit * 0.8  # 安全系数

    return {
        "tolerable_drawdown": tolerable_drawdown,
        "fund_max_drawdown": fund_max_drawdown,
        "position_limit": round(position_limit, 4),
        "position_limit_pct": f"{position_limit:.0%}",
        "safe_position": round(safe_limit, 4),
        "safe_position_pct": f"{safe_limit:.0%}",
    }


def risk_budget_allocation(total_budget: float, volatilities: list,
                            weights: list = None) -> dict:
    """风险预算分配：给定总风险预算，分配各资产风险贡献。

    Args:
        total_budget: 总风险预算（如 0.15 表示 15%）
        volatilities: 各资产波动率
        weights: 各资产权重（可选，默认等权）
    """
    n = len(volatilities)
    if weights is None:
        weights = [1 / n] * n

    total_weight = sum(weights)
    results = []
    for i, (vol, w) in enumerate(zip(volatilities, weights)):
        normalized_w = w / total_weight
        risk_contribution = total_budget * normalized_w
        implied_position = risk_contribution / vol if vol > 0 else 0
        results.append({
            "asset": f"资产{i+1}",
            "weight": round(normalized_w, 4),
            "volatility": vol,
            "risk_contribution": round(risk_contribution, 4),
            "implied_position": round(implied_position, 4),
        })

    return {
        "total_budget": total_budget,
        "allocations": results,
    }


def main():
    parser = argparse.ArgumentParser(description="仓位优化计算器 — Kelly/风险平价/最大回撤约束")
    sub = parser.add_subparsers(dest="command")

    # Kelly 准则
    k = sub.add_parser("kelly", help="Kelly 准则仓位优化")
    k.add_argument("--win-rate", type=float, required=True, help="胜率（0-1）")
    k.add_argument("--payoff", type=float, required=True, help="赔率（盈亏比）")

    # 风险平价
    rp = sub.add_parser("risk-parity", help="风险平价仓位分配")
    rp.add_argument("--volatilities", nargs="+", type=float, required=True)

    # 最大回撤约束
    mdd = sub.add_parser("max-drawdown", help="最大回撤约束仓位上限")
    mdd.add_argument("--tolerable", type=float, required=True, help="可承受回撤（负数）")
    mdd.add_argument("--fund-dd", type=float, required=True, help="基金最大回撤（负数）")

    # 风险预算
    rb = sub.add_parser("risk-budget", help="风险预算分配")
    rb.add_argument("--budget", type=float, required=True, help="总风险预算")
    rb.add_argument("--volatilities", nargs="+", type=float, required=True)

    args = parser.parse_args()

    if args.command == "kelly":
        result = kelly_criterion(args.win_rate, args.payoff)
    elif args.command == "risk-parity":
        result = risk_parity(args.volatilities)
    elif args.command == "max-drawdown":
        result = max_drawdown_constraint(args.tolerable, args.fund_dd)
    elif args.command == "risk-budget":
        result = risk_budget_allocation(args.budget, args.volatilities)
    else:
        parser.print_help()
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
