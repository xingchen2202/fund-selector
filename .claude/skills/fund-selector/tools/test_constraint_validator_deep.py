#!/usr/bin/env python3
"""约束校验器深度压测 — 真实复杂场景"""
import sys, io
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


def test_3fund_complex_overlap():
    """三基金复杂穿透：A-B 重合高，A-C 重合低，B-C 重合高。"""
    m = _import()
    rec = {"funds": [
        {"code": "A", "name": "A", "industry_alloc": {"制造业": 30, "金融": 10}, "fee_total": 1.5, "amount": 1000, "is_dca": True},
        {"code": "B", "name": "B", "industry_alloc": {"制造业": 25, "科技": 15}, "fee_total": 1.2, "amount": 1000, "is_dca": True},
        {"code": "C", "name": "C", "industry_alloc": {"科技": 20, "消费": 18}, "fee_total": 1.3, "amount": 1000, "is_dca": True},
    ], "monthly_savings": 5000, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    # A-B 制造业 min(30,25)=25% >15% → 失败；B-C 科技 min(15,20)=15% → 不超（=15%）
    assert r["passed"] is False
    assert any("A" in f and "B" in f and "制造业" in f for f in r["failures"]), f"应检测到A-B制造业重合: {r['failures']}"


def test_budget_double_dca_with_idle_cash():
    """加倍定投 + 有闲置现金流 → 警告但不失败（需标注来源）。"""
    m = _import()
    rec = {"funds": [
        {"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 5000, "is_dca": True},
    ], "monthly_savings": 3000, "valuation_percentile": 0.05, "idle_cash_flow": 12000, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    # 估值<10%触发加倍，超额=5000-3000=2000，闲置12000可支撑6个月 → 警告
    assert any("预算" in w or "加倍" in w or "超额" in w for w in r["failures"] + r["warnings"])


def test_budget_double_dca_no_idle_cash():
    """加倍定投 + 无闲置现金流 → 应失败（无法支撑）。"""
    m = _import()
    rec = {"funds": [
        {"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 5000, "is_dca": True},
    ], "monthly_savings": 3000, "valuation_percentile": 0.05, "idle_cash_flow": 0, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    assert r["passed"] is False
    assert any("预算硬平衡" in f for f in r["failures"])


def test_allocation_tolerance_pass():
    """配置比例偏差 5%（边界内）→ 应通过。"""
    m = _import()
    rec = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
           "monthly_savings": 5000,
           "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
           "actual_allocation": {"stock": 0.67, "bond": 0.22, "cash": 0.11},  # 偏差3%/2%/1%
           "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    assert r["passed"] is True, f"5%内偏差应通过: {r['failures']}"


def test_allocation_tolerance_fail():
    """配置比例偏差 8%（超边界）→ 应失败。"""
    m = _import()
    rec = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
           "monthly_savings": 5000,
           "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
           "actual_allocation": {"stock": 0.62, "bond": 0.25, "cash": 0.13},  # 股票偏差8%
           "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    assert r["passed"] is False
    assert any("配置闭环" in f for f in r["failures"])


def test_missing_data_graceful():
    """缺失大量字段 → 不应崩溃，返回合理结果。"""
    m = _import()
    rec = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
           "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    # 无 target_allocation → 跳过配置闭环检查；无 monthly_savings → 跳过预算检查
    assert r["passed"] is True


def test_empty_funds():
    """空基金列表 → 不应崩溃。"""
    m = _import()
    rec = {"funds": [], "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    assert r["passed"] is True


def test_fee_missing_multiple():
    """多基金中部分费率缺失 → 应逐个检出。"""
    m = _import()
    rec = {"funds": [
        {"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True},
        {"code": "B", "name": "B", "industry_alloc": {}, "fee_total": None, "amount": 1000, "is_dca": True},
        {"code": "C", "name": "C", "industry_alloc": {}, "fee_total": None, "amount": 1000, "is_dca": True},
    ], "monthly_savings": 5000, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    assert r["passed"] is False
    fee_fails = [f for f in r["failures"] if "费率穿透" in f]
    assert len(fee_fails) == 2, f"应检出2个费率缺失: {fee_fails}"


def test_rebalancing_missing():
    """未设定再平衡 → 警告。"""
    m = _import()
    rec = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
           "monthly_savings": 5000, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    assert any("再平衡" in w for w in r["warnings"])


def test_all_constraints_combined():
    """全约束合规的推荐 → 应完全通过且无警告。"""
    m = _import()
    rec = {
        "funds": [
            {"code": "A", "name": "A", "industry_alloc": {"制造业": 10, "金融": 8}, "fee_total": 1.5, "amount": 2000, "is_dca": True},
            {"code": "B", "name": "B", "industry_alloc": {"科技": 15, "消费": 10}, "fee_total": 1.2, "amount": 1500, "is_dca": True},
        ],
        "monthly_savings": 5000,
        "total_investment": 50000,
        "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "actual_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "valuation_percentile": 0.25,
        "has_emergency_fund": True,
        "has_high_interest_debt": False,
        "has_insurance": True,
        "rebalancing_rule": "季度回顾，偏离>10%触发",
        "disclaimers": ["不构成投资建议"],
    }
    r = m.validate_constraints(rec)
    assert r["passed"] is True, f"合规推荐应通过: {r['failures']}"
    assert len(r["warnings"]) == 0, f"不应有警告: {r['warnings']}"


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
