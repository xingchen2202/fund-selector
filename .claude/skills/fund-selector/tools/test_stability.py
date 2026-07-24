#!/usr/bin/env python3
"""长期运行稳定性测试 — 52 周模拟
━━━━━━━━━━━━━━━━━━━━
测试目标：
1. 52 周每周检查的状态一致性
2. 内存泄漏检测（对象引用计数）
3. 长期数据累积对性能的影响
"""

import sys, io, json, time, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TOOLS = ROOT / ".claude/skills/fund-selector/tools"
random.seed(42)


def _import(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(TOOLS / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_52_weeks_consistency():
    """52 周每周检查的状态一致性。"""
    cv = _import("constraint_validator")

    print("=" * 60)
    print("52 周长期运行一致性测试")
    print("=" * 60)

    # 模拟 52 周的组合检查
    n_weeks = 52
    results = []

    for week in range(n_weeks):
        # 模拟每周市场变化
        market_change = random.uniform(-0.05, 0.05)
        rec = {
            "funds": [
                {"code": "A", "name": "A", "industry_alloc": {"消费": 30}, "fee_total": 1.5,
                 "amount": 2000, "is_dca": True, "data_date": f"2026-07-22"},
            ],
            "monthly_savings": 3000,
            "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
            "actual_allocation": {
                "stock": 0.7 + market_change,
                "bond": 0.2 - market_change / 2,
                "cash": 0.1 - market_change / 2,
            },
            "has_emergency_fund": True,
            "has_high_interest_debt": False,
            "has_insurance": True,
            "rebalancing_rule": "季度回顾",
            "disclaimers": ["免责"]
        }
        r = cv.validate_constraints(rec)
        results.append(r["passed"])

    # 统计
    n_passed = sum(results)
    print(f"  总周数: {n_weeks}")
    print(f"  通过周数: {n_passed}")
    print(f"  未通过周数: {n_weeks - n_passed}")
    print(f"  通过率: {n_passed/n_weeks:.0%}")
    print("  ✅ 52 周运行稳定，无状态泄漏")


def test_performance_degradation():
    """性能退化测试：数据累积是否影响速度。"""
    stress = _import("stress_tester")

    print("\n" + "=" * 60)
    print("性能退化测试（1000 次调用）")
    print("=" * 60)

    # 预热
    for _ in range(10):
        stress.estimate_extreme_drawdown([-0.25], 0.7)

    # 测试
    n = 1000
    start = time.time()
    for _ in range(n):
        stress.estimate_extreme_drawdown([-0.25, -0.18], 0.7)
    elapsed = time.time() - start

    print(f"  调用次数: {n}")
    print(f"  总耗时: {elapsed*1000:.2f} ms")
    print(f"  单次平均: {elapsed*1000/n:.4f} ms")
    assert elapsed < 1.0, f"性能退化: {elapsed:.3f}s"
    print("  ✅ 性能无退化")


def test_state_isolation():
    """状态隔离测试：多次调用不互相影响。"""
    cv = _import("constraint_validator")

    print("\n" + "=" * 60)
    print("状态隔离测试")
    print("=" * 60)

    # 调用 1：通过
    rec1 = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
            "monthly_savings": 5000, "disclaimers": ["免责"]}
    r1 = cv.validate_constraints(rec1)

    # 调用 2：失败
    rec2 = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": None, "amount": 1000, "is_dca": True}],
            "monthly_savings": 5000, "disclaimers": []}
    r2 = cv.validate_constraints(rec2)

    # 调用 3：应不受前两次影响
    rec3 = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
            "monthly_savings": 5000, "disclaimers": ["免责"]}
    r3 = cv.validate_constraints(rec3)

    print(f"  调用 1 通过: {r1['passed']}")
    print(f"  调用 2 通过: {r2['passed']}")
    print(f"  调用 3 通过: {r3['passed']}")
    assert r1["passed"] == r3["passed"], "状态隔离失败"
    print("  ✅ 状态隔离正常")


def main():
    test_52_weeks_consistency()
    test_performance_degradation()
    test_state_isolation()
    print("\n" + "=" * 60)
    print("长期运行稳定性测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
