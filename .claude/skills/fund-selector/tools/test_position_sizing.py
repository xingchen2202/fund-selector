#!/usr/bin/env python3
"""仓位优化与风险预算测试
━━━━━━━━━━━━━━━━━━━━
测试方法：
1. Kelly 准则（简化版）
2. 风险平价（Risk Parity）
3. 最大回撤约束
"""

import sys, io, json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def test_kelly_criterion():
    """Kelly 准则：最优仓位 = (胜率 × 赔率 - 败率) / 赔率"""
    print("=" * 60)
    print("Kelly 准则仓位优化（简化版）")
    print("=" * 60)

    scenarios = [
        ("稳健型基金", 0.60, 1.5, 0.12),   # 胜率 60%，赔率 1.5，预期收益 12%
        ("成长型基金", 0.50, 2.0, 0.18),   # 胜率 50%，赔率 2.0，预期收益 18%
        ("激进型基金", 0.40, 3.0, 0.25),   # 胜率 40%，赔率 3.0，预期收益 25%
    ]

    for name, win_rate, payoff, expected_return in scenarios:
        lose_rate = 1 - win_rate
        # Kelly 公式：f* = (p × b - q) / b
        kelly = (win_rate * payoff - lose_rate) / payoff
        # 半 Kelly（更保守）
        half_kelly = kelly / 2
        # 限制在 0-40%
        optimal = max(0, min(0.40, half_kelly))

        print(f"\n  [{name}]")
        print(f"    胜率: {win_rate:.0%} | 赔率: {payoff:.1f} | 预期收益: {expected_return:.0%}")
        print(f"    Kelly 最优: {kelly:.1%}")
        print(f"    半 Kelly（推荐）: {half_kelly:.1%}")
        print(f"    实际配置上限: {optimal:.1%}")


def test_risk_parity():
    """风险平价：各资产对组合风险贡献相等。"""
    print("\n" + "=" * 60)
    print("风险平价仓位分配")
    print("=" * 60)

    # 三类资产：股票、债券、商品
    assets = [
        ("股票型", 0.18, 0.60),   # 波动率 18%，预期收益 60%（牛市）
        ("债券型", 0.04, 0.05),   # 波动率 4%，预期收益 5%
        ("货币型", 0.01, 0.025),  # 波动率 1%，预期收益 2.5%
    ]

    # 风险平价权重 = 1/波动率 / Σ(1/波动率)
    inv_vols = [1 / vol for _, vol, _ in assets]
    total_inv_vol = sum(inv_vols)
    weights = [iv / total_inv_vol for iv in inv_vols]

    print("\n  资产风险贡献均衡分配：")
    for (name, vol, ret), w in zip(assets, weights):
        print(f"    {name}: {w:.1%} (波动率 {vol:.0%}, 预期收益 {ret:.0%})")

    # 加权波动率
    portfolio_vol = sum(w * vol for (_, vol, _), w in zip(assets, weights))
    print(f"\n  组合加权波动率: {portfolio_vol:.2%}")


def test_max_drawdown_constraint():
    """最大回撤约束：根据可承受回撤反推仓位上限。"""
    print("\n" + "=" * 60)
    print("最大回撤约束仓位上限")
    print("=" * 60)

    scenarios = [
        ("保守型（最大承受 -10%）", -0.10, -0.25),
        ("稳健型（最大承受 -20%）", -0.20, -0.25),
        ("进取型（最大承受 -35%）", -0.35, -0.25),
    ]

    for name, max_tolerable, fund_max_dd in scenarios:
        # 仓位上限 = 可承受回撤 / 基金最大回撤
        position_limit = abs(max_tolerable) / abs(fund_max_dd)
        # 安全系数 0.8
        safe_limit = position_limit * 0.8

        print(f"\n  [{name}]")
        print(f"    可承受回撤: {max_tolerable:.0%}")
        print(f"    基金最大回撤: {fund_max_dd:.0%}")
        print(f"    仓位上限: {position_limit:.0%}")
        print(f"    安全仓位（×0.8）: {safe_limit:.0%}")


def test_risk_budget_allocation():
    """风险预算分配：给定总风险预算，分配各资产风险贡献。"""
    print("\n" + "=" * 60)
    print("风险预算分配（总风险预算 15%）")
    print("=" * 60)

    total_risk_budget = 0.15

    assets = [
        ("股票型", 0.18, 0.60),
        ("债券型", 0.04, 0.30),
        ("货币型", 0.01, 0.10),
    ]

    # 风险预算按权重分配
    total_weight = sum(w for _, _, w in assets)
    print(f"\n  总风险预算: {total_risk_budget:.0%}")
    for name, vol, weight in assets:
        risk_contribution = total_risk_budget * (weight / total_weight)
        implied_position = risk_contribution / vol
        print(f"    {name}: 风险贡献 {risk_contribution:.2%} → 隐含仓位 {implied_position:.0%}")


def main():
    test_kelly_criterion()
    test_risk_parity()
    test_max_drawdown_constraint()
    test_risk_budget_allocation()
    print("\n" + "=" * 60)
    print("仓位优化与风险预算测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
