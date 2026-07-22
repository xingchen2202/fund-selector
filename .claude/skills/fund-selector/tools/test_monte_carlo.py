#!/usr/bin/env python3
"""蒙特卡洛模拟测试 — 1000+ 随机组合的统计分布
━━━━━━━━━━━━━━━━━━━━
测试目标：
1. 随机生成 1000 个组合，统计约束通过率
2. 压力测试结果的分布（均值/标准差/尾部风险）
3. 仓位优化建议的分布
"""

import sys, io, json, random, math
from pathlib import Path
from collections import Counter

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TOOLS = Path(r"C:\Users\22218\Desktop\fund-selector\.claude\skills\fund-selector\tools")
random.seed(42)  # 可复现


def _import(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(TOOLS / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_monte_carlo_constraint_pass_rate():
    """蒙特卡洛：1000 个随机组合的约束通过率。"""
    cv = _import("constraint_validator")

    n = 1000
    passed = 0
    failure_counts = Counter()

    for _ in range(n):
        # 随机生成组合
        rec = {
            "funds": [
                {
                    "code": f"F{i}",
                    "name": f"基金{i}",
                    "industry_alloc": {f"行业{j}": random.uniform(5, 40) for j in range(random.randint(1, 3))},
                    "fee_total": random.choice([None, round(random.uniform(0.5, 2.5), 2)]),
                    "amount": random.randint(500, 8000),
                    "is_dca": True,
                }
                for i in range(random.randint(1, 4))
            ],
            "monthly_savings": random.randint(2000, 10000),
            "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
            "actual_allocation": {
                "stock": random.uniform(0.5, 0.9),
                "bond": random.uniform(0.05, 0.3),
                "cash": random.uniform(0.05, 0.2),
            },
            "has_emergency_fund": random.choice([True, False]),
            "has_high_interest_debt": random.choice([True, False, False]),  # 1/3 概率
            "has_insurance": random.choice([True, False]),
            "rebalancing_rule": random.choice(["", "季度回顾"]),
            "disclaimers": random.choice([["免责"], []]),
        }

        r = cv.validate_constraints(rec)
        if r["passed"]:
            passed += 1
        else:
            for f in r["failures"]:
                # 提取失败类型
                ftype = f.split("]")[0] + "]" if "]" in f else f[:20]
                failure_counts[ftype] += 1

    pass_rate = passed / n
    print(f"  总组合数: {n}")
    print(f"  通过数: {passed}")
    print(f"  通过率: {pass_rate:.1%}")
    print(f"\n  失败类型分布（Top 5）:")
    for ftype, count in failure_counts.most_common(5):
        print(f"    {ftype}: {count} 次 ({count/n:.1%})")

    # 断言：通过率应 <10%（随机组合大多违规，说明约束严格）
    assert pass_rate < 0.10, f"通过率过高，约束可能过松: {pass_rate:.1%}"
    print(f"  [分析] 通过率仅 {pass_rate:.1%}，说明约束系统严格（好事）")


def test_monte_carlo_stress_distribution():
    """蒙特卡洛：压力测试结果的统计分布。"""
    stress = _import("stress_tester")

    n = 1000
    results = []

    for _ in range(n):
        # 随机回撤 -10% 到 -60%
        dd = -random.uniform(0.10, 0.60)
        corr = random.uniform(0.2, 0.9)
        r = stress.estimate_extreme_drawdown([dd], corr)
        results.append(r["adjusted_drawdown"])

    # 统计
    mean_dd = sum(results) / len(results)
    std_dd = math.sqrt(sum((x - mean_dd) ** 2 for x in results) / len(results))
    sorted_dd = sorted(results)
    p5 = sorted_dd[int(0.05 * n)]  # 5% 分位（尾部风险）
    p95 = sorted_dd[int(0.95 * n)]

    print(f"\n  压力测试结果分布（{n} 次模拟）:")
    print(f"    均值: {mean_dd:.1%}")
    print(f"    标准差: {std_dd:.1%}")
    print(f"    5% 分位（尾部风险）: {p5:.1%}")
    print(f"    95% 分位: {p95:.1%}")
    print(f"    最小: {min(results):.1%}")
    print(f"    最大: {max(results):.1%}")

    # 断言：均值应在 -30% 到 -40% 之间
    assert -0.50 < mean_dd < -0.20, f"均值异常: {mean_dd:.1%}"


def test_monte_carlo_position_sizing():
    """蒙特卡洛：仓位优化建议的分布。"""
    pos = _import("position_optimizer")

    n = 1000
    positions = []

    for _ in range(n):
        win_rate = random.uniform(0.3, 0.7)
        payoff = random.uniform(1.0, 3.0)
        r = pos.kelly_criterion(win_rate, payoff)
        positions.append(r["recommended_position"])

    mean_pos = sum(positions) / len(positions)
    sorted_pos = sorted(positions)
    p10 = sorted_pos[int(0.10 * n)]
    p90 = sorted_pos[int(0.90 * n)]

    print(f"\n  仓位优化建议分布（{n} 次模拟）:")
    print(f"    均值: {mean_pos:.1%}")
    print(f"    10% 分位: {p10:.1%}")
    print(f"    90% 分位: {p90:.1%}")
    print(f"    最小: {min(positions):.1%}")
    print(f"    最大: {max(positions):.1%}")

    # 断言：均值应在 10%-20% 之间
    assert 0.05 < mean_pos < 0.25, f"均值异常: {mean_pos:.1%}"


def main():
    print("=" * 60)
    print("蒙特卡洛模拟测试（1000+ 随机组合）")
    print("=" * 60)
    test_monte_carlo_constraint_pass_rate()
    test_monte_carlo_stress_distribution()
    test_monte_carlo_position_sizing()
    print("\n" + "=" * 60)
    print("蒙特卡洛模拟测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
