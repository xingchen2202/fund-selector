#!/usr/bin/env python3
"""对抗性输入与边界安全测试 — 极端值、异常输入、韧性"""
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


def test_extreme_large_values():
    """极大值（万亿级规模）不应崩溃。"""
    m = _import("financial_rigor")
    r = m.verify_scale(nav=1.0, shares=1e12, reported_scale=1e12)
    assert r is True, "极大值应正常计算"


def test_extreme_small_values():
    """极小值（接近零）不应崩溃。"""
    m = _import("financial_rigor")
    r = m.verify_scale(nav=0.0001, shares=1000, reported_scale=0.1)
    assert isinstance(r, bool), "极小值应返回布尔"


def test_negative_nav():
    """负净值（不可能但不应崩溃）。"""
    m = _import("financial_rigor")
    r = m.verify_scale(nav=-1.5, shares=1e8, reported_scale=-1.5e8)
    assert isinstance(r, bool)


def test_zero_shares():
    """零份额 → 计算规模=0。"""
    m = _import("financial_rigor")
    r = m.verify_scale(nav=1.0, shares=0, reported_scale=0)
    assert isinstance(r, bool)


def test_cross_validate_extreme_outlier():
    """极端异常值（100x 偏差）应被检出。"""
    m = _import("financial_rigor")
    r = m.cross_validate("规模", {"A": 4.42, "B": 4.38, "C": 999.99}, "亿", tolerance_pct=2.0)
    assert r["all_consistent"] is False, "极端异常值应被检出"


def test_cross_validate_many_sources():
    """多源（5个）应正常处理。"""
    m = _import("financial_rigor")
    r = m.cross_validate("规模", {"A": 4.42, "B": 4.38, "C": 4.45, "D": 4.40, "E": 4.43}, "亿")
    assert r["all_consistent"] is True


def test_report_audit_malformed_json():
    """畸形 JSON 输入应优雅处理（不崩溃）。"""
    m = _import("report_audit")
    r = m.audit_verdict("not valid json {{{")
    assert r["verdict"] == "无法审计", f"畸形JSON应返回'无法审计': {r}"


def test_report_audit_empty_field():
     """空字段/缺失字段应优雅处理。"""
     m = _import("report_audit")
     results = json.dumps([{"reported": None, "fetched_value": None}])
     r = m.audit_verdict(results)
     assert isinstance(r["verdict"], str)


def test_constraint_validator_empty():
    """完全空输入不应崩溃。"""
    m = _import("constraint_validator")
    r = m.validate_constraints({})
    assert isinstance(r["passed"], bool), "空输入应返回布尔"


def test_constraint_validator_negative_amount():
    """负金额（异常）应被处理。"""
    m = _import("constraint_validator")
    rec = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": -5000, "is_dca": True}],
           "monthly_savings": 3000, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    assert isinstance(r["passed"], bool)


def test_stock_screener_empty_data():
    """空质量数据：仅 no_dilution(0<=5)通过 = 1分。"""
    m = _import("stock_screener")
    r = m.grade_quality({})
    # 空数据：roe=0(失败), margin=0(失败), fcf=0(失败), debt=100(失败), dilution=0(通过), cv=1(失败) = 1分
    assert r["score"] == 1, f"空数据应 1 分: {r['score']}"
    assert r["position_advice"] == "观望"


def test_benford_few_samples():
    """Benford 样本不足 50 应返回 None。"""
    m = _import("financial_rigor")
    r = m.benford_check([1.0, 2.0, 3.0])
    assert r is None, "样本不足应返回 None"


def test_valuation_all_zero():
    """估值全零输入。"""
    m = _import("financial_rigor")
    r = m.verify_valuation(0, eps=0, bps=0)
    assert isinstance(r, dict)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
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
