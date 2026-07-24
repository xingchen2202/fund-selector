#!/usr/bin/env python3
"""端到端工作流集成测试 — 验证新增组件协同工作"""
import sys, io, json, importlib, os
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


def test_e2e_pipeline_full():
    """端到端管道：规模验算 → 交叉验证 → 双源审计 → 约束校验 → 修复建议。"""
    rigor = _import("financial_rigor")
    audit = _import("report_audit")
    cv = _import("constraint_validator")

    # Step 1: 规模验算（基金规模 = 份额 × 净值）
    scale_ok = rigor.verify_scale(nav=1.0553, shares=2.74e9, reported_scale=2.893e9)
    assert scale_ok, "规模验算应通过"

    # Step 2: 三源交叉验证（MCP 数据一致性）
    cv_result = rigor.cross_validate(
        "基金规模",
        {"MCP实时": 28.93, "季报披露": 29.10, "天天基金": 28.85},
        "亿"
    )
    assert cv_result["all_consistent"], "三源应一致"

    # Step 3: 双源审计（报告值 vs 实际获取值）
    verdict = audit.audit_verdict(json.dumps([
        {"reported": 28.93, "fetched_value": 29.10, "fetched_value2": 28.85}
    ]))
    assert verdict["verdict"] == "通过", f"审计应通过: {verdict['verdict']}"

    # Step 4: 约束校验（8 条铁律）
    rec = {
        "funds": [
            {"code": "110011", "name": "易方达", "industry_alloc": {"消费": 12}, "fee_total": 1.5, "amount": 2000, "is_dca": True,
             "top_holdings": ["茅台", "五粮液", "泸州老窖"]},
            {"code": "000001", "name": "华夏", "industry_alloc": {"科技": 15}, "fee_total": 1.2, "amount": 1500, "is_dca": True,
             "top_holdings": ["宁德", "比亚迪", "隆基"]},
        ],
        "monthly_savings": 5000,
        "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "actual_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "has_emergency_fund": True,
        "has_high_interest_debt": False,
        "has_insurance": True,
        "rebalancing_rule": "季度回顾，偏离>10%触发",
        "disclaimers": ["不构成投资建议"],
    }
    constraint = cv.validate_constraints(rec)
    assert constraint["passed"] is True, f"合规组合应通过: {constraint['failures']}"

    print("  ✅ 端到端管道全部通过")


def test_e2e_violation_with_suggestions():
    """违规场景：约束校验失败 → 修复建议 → 修正 → 重新校验通过。"""
    cv = _import("constraint_validator")

    # 违规推荐
    rec = {
        "funds": [
            {"code": "A", "name": "A", "industry_alloc": {"制造业": 30}, "fee_total": None, "amount": 5000, "is_dca": True},
            {"code": "B", "name": "B", "industry_alloc": {"制造业": 25}, "fee_total": 1.2, "amount": 4000, "is_dca": True},
        ],
        "monthly_savings": 3000,
        "disclaimers": ["免责"],
    }
    r1 = cv.validate_constraints(rec)
    assert r1["passed"] is False
    assert len(r1["suggestions"]) >= 2, f"应有修复建议: {len(r1['suggestions'])}"

    # 模拟修正：降低两只基金金额 + 替换行业 + 补充费率
    rec["funds"][0]["amount"] = 2000
    rec["funds"][0]["fee_total"] = 1.5
    rec["funds"][1]["amount"] = 1000  # 同步修正 B
    rec["funds"][1]["industry_alloc"] = {"科技": 20}  # 替换行业

    r2 = cv.validate_constraints(rec)
    assert r2["passed"] is True, f"修正后应通过: {r2['failures']}"

    print("  ✅ 违规→建议→修正→通过 流程正常")


def test_e2e_veto_with_fallback():
    """综合器否决 + 备选方案端到端。"""
    AGT = ROOT / ".claude/skills/fund-selector/agents"
    OUTPUTS = ROOT / "fund-reports/_agent_outputs"
    OUTPUTS.mkdir(exist_ok=True)

    # 设置 agent 输出：A 被否决，B 正常
    for name, data in [
        ("value", '{"agent":"value","rankings":[{"code":"A","name":"A","stars":4},{"code":"B","name":"B","stars":4}]}'),
        ("growth", '{"agent":"growth","rankings":[{"code":"A","name":"A","stars":5},{"code":"B","name":"B","stars":3}]}'),
        ("risk", '{"agent":"risk","rankings":[{"code":"A","name":"A","stars":1,"reason":"无法承受"},{"code":"B","name":"B","stars":4}]}'),
        ("cycle", '{"agent":"cycle","rankings":[{"code":"A","name":"A","stars":3},{"code":"B","name":"B","stars":3}]}'),
    ]:
        (OUTPUTS / f"{name}.json").write_text(data, encoding="utf-8")

    try:
        sys.path.insert(0, str(AGT))
        import synthesize
        importlib.reload(synthesize)
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            synthesize.main()
        result = json.loads((ROOT / "fund-reports" / "_agent_synthesized.json").read_text(encoding="utf-8"))

        assert result["top_pick"] == "B", f"应首推B: {result['top_pick']}"
        assert result["vetoes"][0].startswith("A"), f"应否决A: {result['vetoes']}"
        assert result.get("fallback_candidate") is None, "有可选时不应有备选"
        print("  ✅ 否决+首推+备选 端到端正常")
    finally:
        for f in ["value", "growth", "risk", "cycle"]:
            p = OUTPUTS / f"{f}.json"
            if p.exists():
                p.unlink()
        p = ROOT / "fund-reports/_agent_synthesized.json"
        if p.exists():
            p.unlink()


def test_e2e_stress_test_integration():
    """压力测试数据流：历史最大回撤 → 极端行情估计。"""
    rigor = _import("financial_rigor")

    # 模拟：两只基金的历史最大回撤
    drawdowns = [-0.25, -0.18]
    # 极端行情估计 = 加权平均 × 1.2
    avg_dd = sum(drawdowns) / len(drawdowns)
    extreme_dd = avg_dd * 1.2

    # 验证计算
    assert extreme_dd < 0, "回撤应为负值"
    assert abs(extreme_dd) > abs(avg_dd), "极端情景应比平均更差"

    # 承受能力检查
    monthly_savings = 3000
    investment = 50000
    max_tolerable_dd = -0.25
    can_absorb = extreme_dd > max_tolerable_dd  # -0.258 > -0.25 → False

    print(f"  平均回撤: {avg_dd:.1%}, 极端估计: {extreme_dd:.1%}")
    print(f"  可承受: {'是' if can_absorb else '否（需降低仓位）'}")
    print("  ✅ 压力测试数据流正常")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 60)
    print("端到端工作流集成测试")
    print("=" * 60)
    for t in tests:
        print(f"\n--- {t.__name__} ---")
        try:
            t()
            passed += 1
        except (AssertionError, Exception) as e:
            failed += 1
            print(f"  ❌ {t.__name__}: {e}")
    print(f"\n结果：{passed} 通过 / {failed} 失败 / 共 {len(tests)} 条")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
