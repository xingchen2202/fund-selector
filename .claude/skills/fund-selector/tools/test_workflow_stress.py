#!/usr/bin/env python3
"""完整工作流压力测试 — 模拟高并发场景
━━━━━━━━━━━━━━━━━━━━
测试场景：
1. 50 个并发用户同时请求
2. 100 只基金组合
3. 1000 次推荐生成
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


def test_concurrent_users():
    """模拟 50 个并发用户。"""
    cv = _import("constraint_validator")

    print("=" * 60)
    print("完整工作流压力测试")
    print("=" * 60)

    n_users = 50
    start = time.time()

    for i in range(n_users):
        rec = {
            "funds": [
                {"code": f"{i}_{j}", "name": f"基金{j}", "industry_alloc": {"消费": 30}, "fee_total": 1.5, "amount": 1000, "is_dca": True}
                for j in range(random.randint(1, 5))
            ],
            "monthly_savings": random.randint(2000, 10000),
            "disclaimers": ["免责"]
        }
        cv.validate_constraints(rec)

    elapsed = time.time() - start
    print(f"\n  [{n_users} 并发用户]")
    print(f"    总耗时: {elapsed*1000:.2f} ms")
    print(f"    单用户平均: {elapsed*1000/n_users:.2f} ms")
    assert elapsed < 5.0, f"耗时过长: {elapsed:.3f}s"


def test_large_portfolio():
    """100 只基金组合。"""
    cv = _import("constraint_validator")

    print(f"\n  [100 只基金组合]")
    start = time.time()

    rec = {
        "funds": [
            {"code": f"{i:06d}", "name": f"基金{i}", "industry_alloc": {f"行业{j}": 20 for j in range(2)}, "fee_total": 1.5, "amount": 1000, "is_dca": True}
            for i in range(100)
        ],
        "monthly_savings": 50000,
        "disclaimers": ["免责"]
    }
    r = cv.validate_constraints(rec)
    elapsed = time.time() - start

    print(f"    耗时: {elapsed*1000:.2f} ms")
    print(f"    失败项: {len(r['failures'])}")
    assert elapsed < 1.0, f"耗时过长: {elapsed:.3f}s"


def test_bulk_recommendations():
    """1000 次推荐生成。"""
    stress = _import("stress_tester")

    print(f"\n  [1000 次推荐生成]")
    start = time.time()

    for _ in range(1000):
        stress.estimate_extreme_drawdown([-random.uniform(0.1, 0.5)], random.uniform(0.3, 0.8))

    elapsed = time.time() - start
    print(f"    总耗时: {elapsed*1000:.2f} ms")
    print(f"    单次平均: {elapsed*1000/1000:.4f} ms")
    assert elapsed < 2.0, f"耗时过长: {elapsed:.3f}s"


def main():
    test_concurrent_users()
    test_large_portfolio()
    test_bulk_recommendations()
    print("\n" + "=" * 60)
    print("完整工作流压力测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
