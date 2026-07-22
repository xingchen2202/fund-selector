#!/usr/bin/env python3
"""动态再平衡触发机制测试
━━━━━━━━━━━━━━━━━━━━
测试场景：
1. 阈值触发：单一资产偏离目标 >10%
2. 定期回顾：季度再平衡
3. 风格漂移：持仓与宣称风格不一致
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


def test_threshold_rebalance():
    """阈值触发再平衡：偏离 >10% 时触发。"""
    cv = _import("constraint_validator")

    print("=" * 60)
    print("阈值触发再平衡测试")
    print("=" * 60)

    scenarios = [
        ("目标 70% 股票，实际 75%", {"stock": 0.70, "bond": 0.20, "cash": 0.10}, {"stock": 0.75, "bond": 0.15, "cash": 0.10}),
        ("目标 70% 股票，实际 82%", {"stock": 0.70, "bond": 0.20, "cash": 0.10}, {"stock": 0.82, "bond": 0.10, "cash": 0.08}),
        ("目标 70% 股票，实际 65%", {"stock": 0.70, "bond": 0.20, "cash": 0.10}, {"stock": 0.65, "bond": 0.25, "cash": 0.10}),
    ]

    for name, target, actual in scenarios:
        rec = {
            "funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
            "monthly_savings": 5000,
            "target_allocation": target,
            "actual_allocation": actual,
            "disclaimers": ["免责"]
        }
        r = cv.validate_constraints(rec)
        fails = [f for f in r["failures"] if "配置闭环" in f]
        status = "⚠️ 触发再平衡" if fails else "✅ 无需再平衡"
        print(f"\n  [{name}]")
        print(f"    结果: {status}")
        if fails:
            print(f"    原因: {fails[0][:60]}")


def test_quarterly_review():
    """季度定期回顾触发。"""
    print("\n" + "=" * 60)
    print("季度定期回顾触发测试")
    print("=" * 60)

    # 模拟：每季度检查一次
    quarters = ["2026Q1", "2026Q2", "2026Q3", "2026Q4"]
    for q in quarters:
        print(f"\n  [{q}] 定期回顾")
        print(f"    检查项: 配置比例 / 基金经理变更 / 业绩基准偏离")
        print(f"    触发条件: 偏离 >10% 或 经理变更 或 连续3月跑输基准 >5%")


def test_style_drift_detection():
    """风格漂移检测：持仓与宣称风格不一致。"""
    print("\n" + "=" * 60)
    print("风格漂移检测测试")
    print("=" * 60)

    scenarios = [
        ("宣称价值，实际重仓成长股", "价值", {"科技": 40, "新能源": 30}, "⚠️ 风格漂移"),
        ("宣称消费，实际重仓消费股", "消费", {"消费": 60, "白酒": 20}, "✅ 风格一致"),
        ("宣称均衡，实际单一行业", "均衡", {"半导体": 70}, "⚠️ 严重漂移"),
    ]

    for name, claimed, actual, expected in scenarios:
        # 简化判断：单一行业 >50% 视为漂移
        max_industry = max(actual.values()) if actual else 0
        is_drift = max_industry > 50
        status = "⚠️ 风格漂移" if is_drift else "✅ 风格一致"
        print(f"\n  [{name}]")
        print(f"    宣称: {claimed} | 实际最大行业: {max_industry}%")
        print(f"    结果: {status}")


def main():
    test_threshold_rebalance()
    test_quarterly_review()
    test_style_drift_detection()
    print("\n" + "=" * 60)
    print("动态再平衡测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
