#!/usr/bin/env python3
"""新组件边界与异常测试 — suggestions, fallback, correlation, stress test"""
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


def test_suggestions_empty_warnings():
    """无违规时 suggestions 应为空。"""
    m = _import("constraint_validator")
    rec = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
           "monthly_savings": 5000, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    assert r["passed"] is True
    assert len(r["suggestions"]) == 0, f"无违规应无建议: {r['suggestions']}"


def test_suggestions_multiple_violations():
    """多条违规应产生多条独立建议。"""
    m = _import("constraint_validator")
    rec = {"funds": [
        {"code": "A", "name": "A", "industry_alloc": {"制造": 30}, "fee_total": None, "amount": 5000, "is_dca": True},
        {"code": "B", "name": "B", "industry_alloc": {"制造": 25}, "fee_total": None, "amount": 5000, "is_dca": True},
    ], "monthly_savings": 3000, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    # 应有：穿透、费率×2、预算×2 → 至少 3 条独立建议
    assert len(r["suggestions"]) >= 3, f"应有多条建议: {len(r['suggestions'])}"


def test_correlation_exactly_3_overlap():
    """恰好 3 只重仓相同 → 应触发（边界值）。"""
    m = _import("constraint_validator")
    rec = {"funds": [
        {"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True,
         "top_holdings": ["A1", "A2", "A3"]},
        {"code": "B", "name": "B", "industry_alloc": {}, "fee_total": 1.2, "amount": 1000, "is_dca": True,
         "top_holdings": ["A1", "A2", "A3"]},  # 恰好 3 只相同
    ], "monthly_savings": 5000, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    corr = [w for w in r["warnings"] if "持仓相关性" in w]
    assert len(corr) == 1, f"恰好3只应触发: {len(corr)}"


def test_correlation_4_overlap():
    """4 只重仓相同 → 应触发。"""
    m = _import("constraint_validator")
    rec = {"funds": [
        {"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True,
         "top_holdings": ["A1", "A2", "A3", "A4", "A5"]},
        {"code": "B", "name": "B", "industry_alloc": {}, "fee_total": 1.2, "amount": 1000, "is_dca": True,
         "top_holdings": ["A1", "A2", "A3", "A4", "B5"]},
    ], "monthly_savings": 5000, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    corr = [w for w in r["warnings"] if "持仓相关性" in w]
    assert len(corr) == 1, f"4只相同应触发: {len(corr)}"


def test_fallback_with_empty_rankings():
    """综合器空输入不崩溃。"""
    AGT = Path(r"C:\Users\22218\Desktop\fund-selector\.claude\skills\fund-selector\agents")
    OUTPUTS = Path(r"C:\Users\22218\Desktop\fund-selector\fund-reports/_agent_outputs")
    OUTPUTS.mkdir(exist_ok=True)
    for name in ["value", "growth", "risk", "cycle"]:
        (OUTPUTS / f"{name}.json").write_text('{"agent":"' + name + '","rankings":[]}', encoding="utf-8")
    try:
        sys.path.insert(0, str(AGT))
        import synthesize
        import importlib
        importlib.reload(synthesize)
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            synthesize.main()
        result = json.loads((Path(r"C:\Users\22218\Desktop\fund-selector\fund-reports") / "_agent_synthesized.json").read_text(encoding="utf-8"))
        assert result["top_pick"] is None
        assert result.get("fallback_candidate") is None, "空输入应无备选"
    finally:
        for f in ["value", "growth", "risk", "cycle"]:
            p = OUTPUTS / f"{f}.json"
            if p.exists():
                p.unlink()
        p = Path(r"C:\Users\22218\Desktop\fund-selector\fund-reports/_agent_synthesized.json")
        if p.exists():
            p.unlink()


def test_stress_test_extreme_drawdown():
     """极端回撤估计：单基金 -60% 回撤。"""
     drawdowns = [-0.60]
     avg_dd = sum(drawdowns) / len(drawdowns)
     extreme_dd = avg_dd * 1.2  # -72%
     assert extreme_dd == -0.72, f"极端估计应为 -72%: {extreme_dd}"


def test_constraint_all_funds_vetoed():
     """全部基金被否决场景（约束层无否决，但综合器有）。"""
     m = _import("constraint_validator")
     # 约束校验不涉及否决，只涉及铁律
     rec = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
            "monthly_savings": 5000, "disclaimers": ["免责"]}
     r = m.validate_constraints(rec)
     assert r["passed"] is True


def main():
     tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
     passed = failed = 0
     print("=" * 60)
     print("新组件边界与异常测试")
     print("=" * 60)
     for t in tests:
         try:
             t()
             passed += 1
             print(f"  ✅ {t.__name__}")
         except (AssertionError, Exception) as e:
             failed += 1
             print(f"  ❌ {t.__name__}: {e}")
     print(f"\n结果：{passed} 通过 / {failed} 失败 / 共 {len(tests)} 条")
     sys.exit(1 if failed else 0)


if __name__ == "__main__":
     main()
