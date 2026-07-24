#!/usr/bin/env python3
"""大规模组合负载测试 — 100+ 基金的筛选与校验
━━━━━━━━━━━━━━━━━━━━
测试目标：
1. 大规模组合（10/50/100 只基金）的约束校验速度
2. 内存占用（大规模数据字典）
3. 相关性矩阵计算复杂度（O(n^2)）
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


def generate_fund(index):
    """生成模拟基金数据。"""
    industries = ["消费", "科技", "医药", "金融", "制造", "能源", "材料", "公用"]
    return {
        "code": f"{index:06d}",
        "name": f"基金{index}",
        "industry_alloc": {ind: random.uniform(5, 40) for ind in random.sample(industries, random.randint(1, 3))},
        "fee_total": round(random.uniform(0.5, 2.5), 2),
        "amount": random.randint(500, 5000),
        "is_dca": True,
        "top_holdings": [f"股票{j}" for j in range(random.randint(3, 10))],
    }


def test_constraint_validation_speed():
    """约束校验速度测试：10/50/100 只基金。"""
    cv = _import("constraint_validator")

    print("=" * 60)
    print("大规模组合约束校验速度测试")
    print("=" * 60)

    for n_funds in [10, 50, 100]:
        funds = [generate_fund(i) for i in range(n_funds)]
        rec = {
            "funds": funds,
            "monthly_savings": 10000,
            "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
            "actual_allocation": {"stock": 0.75, "bond": 0.15, "cash": 0.1},
            "has_emergency_fund": True,
            "has_high_interest_debt": False,
            "has_insurance": True,
            "rebalancing_rule": "季度回顾",
            "disclaimers": ["免责"]
        }

        start = time.time()
        r = cv.validate_constraints(rec)
        elapsed = time.time() - start

        print(f"\n  [{n_funds} 只基金]")
        print(f"    耗时: {elapsed*1000:.2f} ms")
        print(f"    通过: {r['passed']}")
        print(f"    失败项: {len(r['failures'])}")
        print(f"    警告项: {len(r['warnings'])}")

        # 断言：100 只基金应在 1 秒内完成
        assert elapsed < 1.0, f"[{n_funds}] 耗时过长: {elapsed:.3f}s"


def test_correlation_matrix_complexity():
    """相关性矩阵计算复杂度：O(n^2)。"""
    corr = _import("correlation_checker")

    print("\n" + "=" * 60)
    print("相关性矩阵计算复杂度测试")
    print("=" * 60)

    for n in [10, 50, 100]:
        funds = [[f"股票{j}" for j in range(random.randint(3, 10))] for _ in range(n)]

        start = time.time()
        result = corr.batch_check(funds)
        elapsed = time.time() - start

        n_pairs = len(result)
        print(f"\n  [{n} 只基金]")
        print(f"    两两组合数: {n_pairs}")
        print(f"    耗时: {elapsed*1000:.2f} ms")
        print(f"    警告数: {sum(1 for r in result if r['warning'])}")

        # 断言：应在 2 秒内完成
        assert elapsed < 2.0, f"[{n}] 耗时过长: {elapsed:.3f}s"


def test_stress_test_speed():
    """压力测试速度：多基金组合。"""
    stress = _import("stress_tester")

    print("\n" + "=" * 60)
    print("压力测试速度测试")
    print("=" * 60)

    for n in [10, 50, 100]:
        drawdowns = [-random.uniform(0.10, 0.50) for _ in range(n)]
        amounts = [random.randint(500, 3000) for _ in range(n)]

        start = time.time()
        r = stress.stress_test_portfolio(drawdowns, amounts, correlation=0.6, months=12)
        elapsed = time.time() - start

        print(f"\n  [{n} 只基金]")
        print(f"    耗时: {elapsed*1000:.2f} ms")
        print(f"    极端回撤: {r['adjusted_drawdown']:.1%}")

        assert elapsed < 0.5, f"[{n}] 耗时过长: {elapsed:.3f}s"


def main():
    test_constraint_validation_speed()
    test_correlation_matrix_complexity()
    test_stress_test_speed()
    print("\n" + "=" * 60)
    print("大规模组合负载测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
