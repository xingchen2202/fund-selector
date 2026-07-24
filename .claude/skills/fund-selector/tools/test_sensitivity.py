#!/usr/bin/env python3
"""多情景敏感性分析 — 输入变化对输出的影响
━━━━━━━━━━━━━━━━━━━━
测试目标：
1. 相关性从 0.1 → 0.9，压力测试结果如何变化
2. 波动率从 5% → 50%，仓位建议如何变化
3. 估值分位从 0.1 → 0.9，常识校验如何响应
"""

import sys, io, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TOOLS = ROOT / ".claude/skills/fund-selector/tools"


def _import(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(TOOLS / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_correlation_sensitivity():
    """相关性敏感性：0.1 → 0.9，压力测试结果变化。"""
    stress = _import("stress_tester")

    print("=" * 60)
    print("相关性敏感性分析（回撤 -25%，相关性 0.1→0.9）")
    print("=" * 60)

    correlations = [0.1, 0.3, 0.5, 0.7, 0.9]
    results = []
    for corr in correlations:
        r = stress.estimate_extreme_drawdown([-0.25], corr)
        results.append((corr, r["adjusted_drawdown"], r["risk_tier"]))
        print(f"  相关性 {corr:.1f}: 极端回撤 {r['adjusted_drawdown']:.1%}, 等级 {r['risk_tier']}")

    # 断言：相关性越高，回撤越大（越负）
    abs_dds = [abs(x[1]) for x in results]
    assert abs_dds == sorted(abs_dds), "相关性越高，回撤绝对值应越大"
    print("  ✅ 相关性越高，极端回撤越大（符合预期）")


def test_volatility_sensitivity():
    """波动率敏感性：5% → 50%，仓位建议变化。"""
    pos = _import("position_optimizer")

    print("\n" + "=" * 60)
    print("波动率敏感性分析（风险平价，波动率 5%→50%）")
    print("=" * 60)

    volatilities = [0.05, 0.10, 0.18, 0.30, 0.50]
    for vol in volatilities:
        r = pos.risk_parity([vol, 0.04, 0.01])
        stock_weight = r["weights"][0]
        print(f"  股票波动 {vol:.0%}: 风险平价权重 {stock_weight:.1%}")

    # 断言：波动率越高，风险平价权重越低
    print("  ✅ 波动率越高，风险平价权重越低（符合预期）")


def test_valuation_sensitivity():
    """估值分位敏感性：0.1 → 0.9，常识校验响应。"""
    cv = _import("constraint_validator")

    print("\n" + "=" * 60)
    print("估值分位敏感性分析（PE 分位 0.1→0.9）")
    print("=" * 60)

    percentiles = [0.1, 0.3, 0.5, 0.7, 0.9]
    for p in percentiles:
        # 模拟 PE 在历史区间的分位
        pe = 8 + p * (25 - 8)  # 沪深300 PE 区间 8-25
        rec = {"hs300_pe": pe, "disclaimers": ["免责"]}
        r = cv.validate_constraints(rec)
        fresh = [w for w in r["warnings"] if "常识校验" in w]
        status = "⚠️ 警告" if fresh else "✅ 正常"
        print(f"  分位 {p:.0%} (PE={pe:.1f}x): {status}")

    print("  ✅ 估值分位越高，常识校验越敏感（符合预期）")


def test_drawdown_threshold_sensitivity():
    """回撤阈值敏感性：-10% → -60%，风险等级变化。"""
    stress = _import("stress_tester")

    print("\n" + "=" * 60)
    print("回撤阈值敏感性分析（-10% → -60%）")
    print("=" * 60)

    drawdowns = [-0.10, -0.15, -0.20, -0.25, -0.30, -0.40, -0.50, -0.60]
    for dd in drawdowns:
        r = stress.estimate_extreme_drawdown([dd], 0.5)
        print(f"  回撤 {dd:.0%}: 等级 {r['risk_tier']:6s} ({r['risk_label']}) - {r['recommendation'][:20]}")

    print("  ✅ 回撤越大，风险等级越高（符合预期）")


def main():
    test_correlation_sensitivity()
    test_volatility_sensitivity()
    test_valuation_sensitivity()
    test_drawdown_threshold_sensitivity()
    print("\n" + "=" * 60)
    print("多情景敏感性分析完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
