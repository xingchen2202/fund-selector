#!/usr/bin/env python3
"""黑天鹅事件压力测试 — 模拟历史极端行情
━━━━━━━━━━━━━━━━━━━━
测试 skill 在以下场景的响应：
1. 2015 年股灾（沪深300 -43%）
2. 2020 年疫情（沪深300 -34%）
3. 2022 年加息（沪深300 -21%）
4. 假设黑天鹅（-60%）
"""

import sys, io, json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TOOLS = Path(r"C:\Users\22218\Desktop\fund-selector\.claude\skills\fund-selector\tools")


def _import(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(TOOLS / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 历史极端行情数据
BLACK_SWAN_SCENARIOS = {
    "2015股灾": {"drawdown": -0.43, "recovery_months": 18, "trigger": "杠杆牛破裂"},
    "2020疫情": {"drawdown": -0.34, "recovery_months": 6, "trigger": "COVID-19"},
    "2022加息": {"drawdown": -0.21, "recovery_months": 12, "trigger": "美联储加息"},
    "假设黑天鹅": {"drawdown": -0.60, "recovery_months": 36, "trigger": "系统性风险"},
}


def test_black_swan_stress():
    """黑天鹅压力测试：极端回撤下的组合承受力。"""
    stress = _import("stress_tester")

    print("=" * 60)
    print("黑天鹅事件压力测试")
    print("=" * 60)

    for name, data in BLACK_SWAN_SCENARIOS.items():
        result = stress.estimate_extreme_drawdown(
            historical_drawdowns=[data["drawdown"]],
            correlation=0.8  # 高相关性（恐慌时相关性趋同）
        )
        can_absorb = result["can_absorb"]
        print(f"\n  [{name}] {data['trigger']}")
        print(f"    历史回撤: {data['drawdown']:.0%}")
        print(f"    极端估计: {result['adjusted_drawdown']:.1%}")
        print(f"    可承受: {'✅' if can_absorb else '❌'}")
        print(f"    恢复周期: {data['recovery_months']} 个月")
        if not can_absorb:
            print(f"    [建议] {result['recommendation']}")


def test_portfolio_survival():
    """组合生存性测试：极端行情下定投能否持续。"""
    stress = _import("stress_tester")

    print("\n" + "=" * 60)
    print("组合生存性测试（月投 3000 × 12 个月）")
    print("=" * 60)

    scenarios = [
        ("保守组合", [-0.10, -0.08], 0.3),
        ("稳健组合", [-0.20, -0.15], 0.5),
        ("进取组合", [-0.35, -0.25], 0.7),
        ("激进组合", [-0.50, -0.40], 0.8),
    ]

    for name, drawdowns, corr in scenarios:
        result = stress.stress_test_portfolio(
            historical_drawdowns=drawdowns,
            monthly_amounts=[3000] * len(drawdowns),
            correlation=corr,
            months=12
        )
        total_invested = result["total_invested"]
        extreme_loss = result["extreme_loss_estimate"]
        loss_pct = result["loss_ratio"]

        print(f"\n  [{name}]")
        print(f"    投入本金: ¥{total_invested:,.0f}")
        print(f"    极端浮亏: ¥{extreme_loss:,.0f} ({loss_pct:.1%})")
        print(f"    可承受: {'✅' if result['can_absorb'] else '❌'}")
        print(f"    应急预案: {result['emergency_plan']}")


def test_recovery_timeline():
    """恢复时间线测试：极端行情后多久回本。"""
    print("\n" + "=" * 60)
    print("恢复时间线测试（定投回本模拟）")
    print("=" * 60)

    scenarios = [
        ("-20% 回撤", -0.20, 0.08),   # 年化 8% 恢复
        ("-35% 回撤", -0.35, 0.08),
        ("-50% 回撤", -0.50, 0.08),
    ]

    for name, drawdown, recovery_rate in scenarios:
        # 简化计算：定投摊薄后的实际回撤
        actual_drawdown = drawdown * 0.6  # 定投摊薄效应
        # 回本所需月数
        months_to_recover = int(abs(actual_drawdown) / (recovery_rate / 12))

        print(f"\n  [{name}]")
        print(f"    定投摊薄后回撤: {actual_drawdown:.1%}")
        print(f"    年化恢复速率: {recovery_rate:.0%}")
        print(f"    预估回本时间: ~{months_to_recover} 个月")


def main():
    test_black_swan_stress()
    test_portfolio_survival()
    test_recovery_timeline()
    print("\n" + "=" * 60)
    print("黑天鹅压力测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
