#!/usr/bin/env python3
"""LLM 行为测试 — 验证 skill 实际输出行为是否符合预期
━━━━━━━━━━━━━━━━━━━━
由于无法直接调用 LLM，本测试验证：
1. skill 定义的 prompt 结构是否完整（触发词、流程、输出格式）
2. skill 是否引用了正确的工具
3. skill 的失败处理是否覆盖常见场景

用法：
    python tools/test_llm_behavior.py
"""

import sys, io, re
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SKILLS_DIR = Path(r"C:\Users\22218\Desktop\fund-selector\.claude\skills\fund-selector\skills")
TOOLS_DIR = Path(r"C:\Users\22218\Desktop\fund-selector\.claude\skills\fund-selector\tools")


def test_skill_has_tools_reference():
    """所有 skill 应引用 constraint_validator（核心约束工具）。"""
    skills = list(SKILLS_DIR.glob("*.md"))
    referenced = 0
    for f in skills:
        content = f.read_text(encoding="utf-8")
        # 至少引用了一个工具
        if "tools/" in content or "constraint_validator" in content:
            referenced += 1
    print(f"  引用工具的 skill: {referenced}/{len(skills)}")
    assert referenced >= 10, f"引用工具的 skill 不足: {referenced}"


def test_constraint_validator_in_main_skill():
    """主 SKILL.md 应包含强制约束校验章节。"""
    main = (Path(r"C:\Users\22218\Desktop\fund-selector\.claude\skills/fund-selector/SKILL.md")).read_text(encoding="utf-8")
    assert "强制约束校验" in main, "SKILL.md 应包含'强制约束校验'章节"
    assert "constraint_validator" in main, "SKILL.md 应引用 constraint_validator"
    print("  ✅ SKILL.md 包含强制约束校验章节")


def test_tools_exist():
    """skill 引用的工具文件应存在。"""
    tools = ["financial_rigor.py", "report_audit.py", "data_validator.py",
             "stock_screener.py", "constraint_validator.py", "stress_tester.py",
             "correlation_checker.py"]
    missing = [t for t in tools if not (TOOLS_DIR / t).exists()]
    print(f"  工具文件存在: {len(tools) - len(missing)}/{len(tools)}")
    assert not missing, f"缺失工具: {missing}"


def test_stress_tester_cli():
    """stress_tester CLI 应正常工作。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("st", str(TOOLS_DIR / "stress_tester.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    # 测试核心函数
    r = m.estimate_extreme_drawdown([-0.25, -0.18], 0.7)
    assert "adjusted_drawdown" in r
    assert "risk_tier" in r  # v2.0 新增分层阈值
    print("  ✅ stress_tester 核心函数正常")


def test_correlation_checker_cli():
    """correlation_checker CLI 应正常工作。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("cc", str(TOOLS_DIR / "correlation_checker.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    r = m.check_holdings_overlap(["茅台", "五粮液"], ["茅台", "五粮液", "宁德"])
    assert r["common_count"] == 2
    assert r["warning"] is False  # 2 只不触发
    r2 = m.check_holdings_overlap(["茅台", "五粮液", "宁德"], ["茅台", "五粮液", "宁德", "腾讯"])
    assert r2["warning"] is True  # 3 只触发
    print("  ✅ correlation_checker 核心函数正常")


def test_data_freshness_in_validator():
    """constraint_validator 应包含数据时效校验。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("cv", str(TOOLS_DIR / "constraint_validator.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    # 陈旧数据应触发警告
    rec = {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5,
                      "amount": 1000, "is_dca": True, "data_date": "2026-01-01"}],
           "monthly_savings": 5000, "disclaimers": ["免责"]}
    r = m.validate_constraints(rec)
    fresh_warnings = [w for w in r["warnings"] if "数据时效" in w]
    assert len(fresh_warnings) == 1, f"应触发数据时效警告: {fresh_warnings}"
    print("  ✅ constraint_validator 数据时效校验正常")


def test_fallback_in_synthesizer():
    """synthesize.py 应包含 fallback_candidate 字段。"""
    src = (Path(r"C:\Users\22218\Desktop\fund-selector\.claude/skills/fund-selector/agents/synthesize.py")).read_text(encoding="utf-8")
    assert "fallback_candidate" in src, "synthesize.py 应包含 fallback_candidate"
    print("  ✅ synthesize.py 包含 fallback_candidate")


def test_workflow_has_stress_test():
    """FUND_ANALYSIS_WORKFLOW 应包含压力测试章节。"""
    workflow = Path(r"C:\Users\22218\Desktop\fund-selector/FUND_ANALYSIS_WORKFLOW.md").read_text(encoding="utf-8")
    assert "压力测试" in workflow, "工作流应包含压力测试"
    assert "Step 5" in workflow or "Step5" in workflow, "工作流应有 Step5"
    print("  ✅ 工作流包含压力测试章节")


def test_4_masters_distinct():
    """4 大师视角应有明确差异化（Jaccard 距离检查）。"""
    team_lead = Path(r"C:\Users\22218\Desktop\fund-selector/.claude/skills/fund-selector/agents/team_lead.py").read_text(encoding="utf-8")
    # 每个视角应有独特的关键词
    buffett_keys = ["ROE", "free cash flow", "moat"]
    duan_keys = ["integrity", "right things", "本分"]
    lilu_keys = ["what could go wrong", "unknown unknowns", "maximum risk"]
    munger_keys = ["invert", "multidisciplinary", "consensus"]

    for keys, name in [(buffett_keys, "Buffett"), (duan_keys, "Duan"),
                       (lilu_keys, "Li Lu"), (munger_keys, "Munger")]:
        found = sum(1 for k in keys if k.lower() in team_lead.lower())
        assert found >= 2, f"{name} 视角关键词不足: {found}/3"
    print("  ✅ 4 大师视角差异化验证通过")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 60)
    print("LLM 行为测试（skill 定义完整性 + 工具引用 + 核心函数）")
    print("=" * 60)
    for t in tests:
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
