#!/usr/bin/env python3
"""极端边界探索 — 系统在极端/异常输入下的行为
━━━━━━━━━━━━━━━━━━━━
测试目标：
1. 所有基金被否决
2. 零相关性 / 100% 相关性
3. 100% 集中度
4. 全负输入
5. 空输入 / 缺失字段
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


def test_zero_correlation():
    """零相关性边界。"""
    stress = _import("stress_tester")
    print("=" * 60)
    print("极端边界：零相关性")
    print("=" * 60)

    for corr in [0.0, 0.01, 0.001]:
        try:
            r = stress.estimate_extreme_drawdown([-0.25], corr)
            print(f"  相关性 {corr}: 回撤 {r['adjusted_drawdown']:.1%}")
        except Exception as e:
            print(f"  相关性 {corr}: 错误 {e}")

    # 零相关不应崩溃
    r = stress.estimate_extreme_drawdown([-0.25], 0.0)
    assert "adjusted_drawdown" in r
    print("  ✅ 零相关性不崩溃")


def test_full_correlation():
    """100% 相关性边界。"""
    stress = _import("stress_tester")
    print("\n" + "=" * 60)
    print("极端边界：100% 相关性")
    print("=" * 60)

    r = stress.estimate_extreme_drawdown([-0.25], 1.0)
    print(f"  相关性 1.0: 回撤 {r['adjusted_drawdown']:.1%}")
    assert r["adjusted_drawdown"] < -0.25
    print("  ✅ 100% 相关性回撤最大")


def test_100_percent_concentration():
    """100% 集中度边界。"""
    cv = _import("constraint_validator")
    print("\n" + "=" * 60)
    print("极端边界：100% 集中度")
    print("=" * 60)

    rec = {
        "funds": [{"code": "A", "name": "A", "industry_alloc": {"半导体": 100}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
        "monthly_savings": 5000,
        "disclaimers": ["免责"]
    }
    r = cv.validate_constraints(rec)
    print(f"  通过: {r['passed']}")
    # 单基金无穿透问题，但 100% 单一行业应警告
    print("  ✅ 100% 集中度不崩溃")


def test_all_negative_inputs():
    """全负输入边界。"""
    print("\n" + "=" * 60)
    print("极端边界：全负输入")
    print("=" * 60)

    pos = _import("position_optimizer")
    # Kelly: 负胜率
    try:
        r = pos.kelly_criterion(-0.1, 1.5)
        print(f"  负胜率: {r}")
    except Exception as e:
        print(f"  负胜率: 错误 {e}")

    # Kelly: 负赔率
    r = pos.kelly_criterion(0.5, -1.0)
    print(f"  负赔率: {r.get('error', r.get('kelly_optimal'))}")
    print("  ✅ 负输入有处理")


def test_empty_inputs():
    """空输入边界。"""
    cv = _import("constraint_validator")
    stress = _import("stress_tester")
    print("\n" + "=" * 60)
    print("极端边界：空输入")
    print("=" * 60)

    # 空基金列表
    r = cv.validate_constraints({"funds": [], "disclaimers": ["免责"]})
    print(f"  空基金: passed={r['passed']}")

    # 完全空输入
    r = cv.validate_constraints({})
    print(f"  空对象: passed={r['passed']}")

    # 空回撤列表
    r = stress.estimate_extreme_drawdown([], 0.5)
    print(f"  空回撤: {r.get('error', 'OK')}")
    print("  ✅ 空输入不崩溃")


def test_all_funds_vetoed():
    """所有基金被否决场景。"""
    print("\n" + "=" * 60)
    print("极端边界：所有基金被否决")
    print("=" * 60)

    AGT = ROOT / ".claude/skills/fund-selector/agents"
    OUTPUTS = ROOT / "fund-reports/_agent_outputs"
    OUTPUTS.mkdir(exist_ok=True)

    # 所有基金风险 1 星
    for name in ["value", "growth", "risk", "cycle"]:
        (OUTPUTS / f"{name}.json").write_text(
            '{"agent":"' + name + '","rankings":[{"code":"A","name":"A","stars":1,"reason":"测试"}]}',
            encoding="utf-8"
        )

    try:
        sys.path.insert(0, str(AGT))
        import synthesize
        import importlib
        importlib.reload(synthesize)
        with io.StringIO() as buf:
            with io.TextIOWrapper(buf, encoding='utf-8'):
                old_stdout = sys.stdout
                sys.stdout = buf
                synthesize.main()
                sys.stdout = old_stdout

        r = json.loads((ROOT / "fund-reports" / "_agent_synthesized.json").read_text(encoding="utf-8"))
        print(f"  首推: {r['top_pick']}")
        print(f"  备选: {r.get('fallback_candidate', {}).get('code')}")
        print(f"  否决数: {len(r['vetoes'])}")
        assert r["top_pick"] is None, "全部否决应无首推"
        assert r.get("fallback_candidate") is not None, "应有备选方案"
        print("  ✅ 全部否决返回备选方案")
    finally:
        for f in ["value", "growth", "risk", "cycle"]:
            p = OUTPUTS / f"{f}.json"
            if p.exists():
                p.unlink()
        p = ROOT / "fund-reports/_agent_synthesized.json"
        if p.exists():
            p.unlink()


def main():
    test_zero_correlation()
    test_full_correlation()
    test_100_percent_concentration()
    test_all_negative_inputs()
    test_empty_inputs()
    test_all_funds_vetoed()
    print("\n" + "=" * 60)
    print("极端边界探索完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
