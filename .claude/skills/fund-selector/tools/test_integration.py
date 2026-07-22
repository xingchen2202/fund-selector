#!/usr/bin/env python3
"""工具链集成场景测试 — 模拟真实分析流程"""
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


def test_pipeline_scale_to_audit():
    """集成场景1：规模验算 → 双源审计。
    基金规模 28.93亿，三源交叉验证一致 → 审计应通过。"""
    rigor = _import("financial_rigor")
    audit = _import("report_audit")

    # Step 1: 规模验算（份额×净值 vs 报告）
    passed = rigor.verify_scale(nav=1.0553, shares=2.74e9, reported_scale=2.893e9)
    assert passed is True, "规模验算应通过"

    # Step 2: 三源交叉验证
    cv = rigor.cross_validate("基金规模", {"MCP实时": 28.93, "季报披露": 29.10, "天天基金": 28.85}, "亿")
    assert cv["all_consistent"] is True, "三源应一致"

    # Step 3: 双源审计判决
    results = json.dumps([
        {"reported": 28.93, "fetched_value": 29.10, "fetched_value2": 28.85}
    ])
    verdict = audit.audit_verdict(results)
    assert verdict["verdict"] == "通过", f"审计应通过: {verdict['verdict']}"


def test_pipeline_constraint_check():
    """集成场景2：推荐组合 → 约束校验。
    3只基金组合，行业分散、预算合规、费率披露 → 应通过。"""
    cv = _import("constraint_validator")

    rec = {
        "funds": [
            {"code": "110011", "name": "易方达", "industry_alloc": {"消费": 12, "金融": 8}, "fee_total": 1.5, "amount": 2000, "is_dca": True},
            {"code": "000001", "name": "华夏", "industry_alloc": {"科技": 15, "医药": 10}, "fee_total": 1.2, "amount": 1500, "is_dca": True},
            {"code": "161725", "name": "招商", "industry_alloc": {"制造": 10, "材料": 8}, "fee_total": 1.3, "amount": 1500, "is_dca": True},
        ],
        "monthly_savings": 5000,
        "total_investment": 50000,
        "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "actual_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "has_emergency_fund": True,
        "has_high_interest_debt": False,
        "has_insurance": True,
        "rebalancing_rule": "季度回顾，偏离>10%触发",
        "disclaimers": ["不构成投资建议"],
    }
    r = cv.validate_constraints(rec)
    assert r["passed"] is True, f"合规组合应通过: {r['failures']}"
    assert len(r["warnings"]) == 0


def test_pipeline_violation_caught():
     """集成场景3：违规组合 → 约束校验应捕获。
     行业重合 25%（>15%）+ 费率缺失 → 应失败。"""
     cv = _import("constraint_validator")
     rec = {
         "funds": [
             {"code": "A", "name": "A", "industry_alloc": {"制造业": 30}, "fee_total": None, "amount": 1000, "is_dca": True},
             {"code": "B", "name": "B", "industry_alloc": {"制造业": 25}, "fee_total": 1.2, "amount": 1000, "is_dca": True},
         ],
         "monthly_savings": 5000,
         "disclaimers": ["免责"],
     }
     r = cv.validate_constraints(rec)
     assert r["passed"] is False
     assert any("穿透" in f for f in r["failures"])
     assert any("费率" in f for f in r["failures"])


def test_audit_downgrade_warning():
     """集成场景4：双源不一致 → 审计降级为警告（非失败）。"""
     audit = _import("report_audit")
     results = json.dumps([
         {"reported": 4.42, "fetched_value": 4.40, "fetched_value2": 5.50}
     ])
     verdict = audit.audit_verdict(results)
     assert verdict["verdict"] == "有条件通过（含警告）", f"应降级: {verdict['verdict']}"
     assert verdict["warned"] == 1


def test_benford_detects_fabrication():
     """集成场景5：Benford 检测区分自然/人为数据。"""
     rigor = _import("financial_rigor")
     import random
     random.seed(42)
     # 自然数据（跨数量级）
     natural = [10 ** random.uniform(0, 6) for _ in range(200)]
     r_natural = rigor.benford_check(natural)
     # 人为均匀分布
     artificial = [float(random.randint(1, 9)) + random.random() for _ in range(200)]
     r_artificial = rigor.benford_check(artificial)
     # 自然数据 MAD 应显著低于人为数据
     assert r_natural["mad"] < r_artificial["mad"], \
         f"自然数据MAD({r_natural['mad']:.4f})应<人为({r_artificial['mad']:.4f})"


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
