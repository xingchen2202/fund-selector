#!/usr/bin/env python3
"""测试约束校验器 — 8 条铁律程序化执行"""
import sys
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TOOLS = ROOT / ".claude/skills/fund-selector/tools"


def _import():
    import importlib.util
    spec = importlib.util.spec_from_file_location("cv", str(TOOLS / "constraint_validator.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pass():
    """合规推荐应通过。"""
    m = _import()
    rec = {
        "funds": [
            {"code": "A", "name": "基金A", "industry_alloc": {"制造业": 20, "金融": 10}, "fee_total": 1.5, "amount": 2000, "is_dca": True},
            {"code": "B", "name": "基金B", "industry_alloc": {"科技": 25, "消费": 15}, "fee_total": 1.2, "amount": 1000, "is_dca": True},
        ],
        "monthly_savings": 3000,
        "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "actual_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "has_emergency_fund": True,
        "has_high_interest_debt": False,
        "has_insurance": True,
        "rebalancing_rule": "季度回顾，偏离>10%触发",
        "disclaimers": ["不构成投资建议"],
    }
    r = m.validate_constraints(rec)
    assert r["passed"] is True, f"应通过: {r['failures']}"
    assert len(r["failures"]) == 0


def test_industry_overlap_fail():
    """行业重合>15% 应失败。"""
    m = _import()
    rec = {
        "funds": [
            {"code": "A", "name": "基金A", "industry_alloc": {"制造业": 30}, "fee_total": 1.5, "amount": 1000, "is_dca": True},
            {"code": "B", "name": "基金B", "industry_alloc": {"制造业": 25}, "fee_total": 1.2, "amount": 1000, "is_dca": True},
        ],
        "monthly_savings": 5000,
        "has_emergency_fund": True,
        "disclaimers": ["免责声明"],
    }
    r = m.validate_constraints(rec)
    assert r["passed"] is False
    assert any("穿透防重叠" in f for f in r["failures"])


def test_budget_exceed_fail():
    """定投超月储蓄 应失败。"""
    m = _import()
    rec = {
        "funds": [{"code": "A", "name": "基金A", "industry_alloc": {}, "fee_total": 1.5, "amount": 5000, "is_dca": True}],
        "monthly_savings": 3000,
        "valuation_percentile": 0.5,
        "has_emergency_fund": True,
        "disclaimers": ["免责声明"],
    }
    r = m.validate_constraints(rec)
    assert r["passed"] is False
    assert any("预算硬平衡" in f for f in r["failures"])


def test_allocation_mismatch_fail():
    """配置比例偏差>5% 应失败。"""
    m = _import()
    rec = {
        "funds": [{"code": "A", "name": "基金A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
        "monthly_savings": 5000,
        "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "actual_allocation": {"stock": 0.5, "bond": 0.3, "cash": 0.2},
        "has_emergency_fund": True,
        "disclaimers": ["免责声明"],
    }
    r = m.validate_constraints(rec)
    assert r["passed"] is False
    assert any("配置闭环" in f for f in r["failures"])


def test_fee_missing_fail():
    """费率缺失 应失败。"""
    m = _import()
    rec = {
        "funds": [{"code": "A", "name": "基金A", "industry_alloc": {}, "fee_total": None, "amount": 1000, "is_dca": True}],
        "monthly_savings": 5000,
        "has_emergency_fund": True,
        "disclaimers": ["免责声明"],
    }
    r = m.validate_constraints(rec)
    assert r["passed"] is False
    assert any("费率穿透" in f for f in r["failures"])


def test_commonsense_warning():
    """PE 异常应警告。"""
    m = _import()
    rec = {"hs300_pe": 3.0, "disclaimers": ["免责声明"]}
    r = m.validate_constraints(rec)
    assert any("常识校验" in w for w in r["warnings"])


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {t.__name__}: {e}")
    print(f"\n结果：{passed} 通过 / {failed} 失败 / 共 {len(tests)} 条")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
