#!/usr/bin/env python3
"""测试 Agent 层（Team Lead + 4 视角 + 综合器）"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(r"C:\Users\22218\Desktop\fund-selector")
AGT = REPO / ".claude/skills/fund-selector/agents"
REPORTS = REPO / "fund-reports"


def _import(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(AGT / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_team_lead_generates_prompts():
    """Team Lead 应生成 4 个 prompt 文件"""
    sys.path.insert(0, str(AGT))
    from team_lead import make_prompt
    funds = [{"code": "000001", "name": "测试基金", "scale": 5.0, "scale_unit": "亿",
              "manager": "张三", "manager_years": 5, "fee_total": 1.2,
              "return_1y": 15.0, "return_3y": 45.0, "max_drawdown": -0.20,
              "sector": "均衡", "nav_series": [1.0 + 0.01*i for i in range(60)]}]
    ctx = "测试组合"
    p1 = make_prompt("Buffett", "Value", "philosophy", "questions", funds, ctx)
    p2 = make_prompt("Duan", "Growth", "philosophy", "questions", funds, ctx)
    p3 = make_prompt("Li Lu", "Risk", "philosophy", "questions", funds, ctx)
    p4 = make_prompt("Munger", "Cycle", "philosophy", "questions", funds, ctx)
    assert "Buffett" in p1
    assert "Duan" in p2
    assert "Li Lu" in p3
    assert "Munger" in p4


def test_synthesizer_blend():
    """综合器：平均星级计算正确"""
    # 写临时 agent 输出
    outputs = REPORTS / "_agent_outputs"
    outputs.mkdir(exist_ok=True)
    (outputs / "value.json").write_text(json.dumps({
        "agent": "value",
        "rankings": [{"code": "A", "name": "A", "stars": 5}, {"code": "B", "name": "B", "stars": 3}]
    }), encoding="utf-8")
    (outputs / "growth.json").write_text(json.dumps({
        "agent": "growth",
        "rankings": [{"code": "A", "name": "A", "stars": 3}, {"code": "B", "name": "B", "stars": 4}]
    }), encoding="utf-8")
    (outputs / "risk.json").write_text(json.dumps({
        "agent": "risk",
        "rankings": [{"code": "A", "name": "A", "stars": 4}, {"code": "B", "name": "B", "stars": 4}]
    }), encoding="utf-8")
    (outputs / "cycle.json").write_text(json.dumps({
        "agent": "cycle",
        "rankings": [{"code": "A", "name": "A", "stars": 4}, {"code": "B", "name": "B", "stars": 3}]
    }), encoding="utf-8")
    try:
        sys.path.insert(0, str(AGT))
        from synthesize import main as synth_main
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            synth_main()
        result = json.loads((REPORTS / "_agent_synthesized.json").read_text(encoding="utf-8"))
        # A: (5+3+4+4)/4 = 4.0; B: (3+4+4+3)/4 = 3.5
        a = next(r for r in result["final_rankings"] if r["code"] == "A")
        b = next(r for r in result["final_rankings"] if r["code"] == "B")
        assert a["avg_stars"] == 4.0, f"A 应为 4.0 星: {a['avg_stars']}"
        assert b["avg_stars"] == 3.5, f"B 应为 3.5 星: {b['avg_stars']}"
        assert result["top_pick"] == "A"
    finally:
        # cleanup
        for f in ["value", "growth", "risk", "cycle"]:
            p = outputs / f"{f}.json"
            if p.exists(): p.unlink()


def test_synthesizer_conflict_detection():
    """综合器：星级差 >=2 应标记冲突"""
    outputs = REPORTS / "_agent_outputs"
    outputs.mkdir(exist_ok=True)
    (outputs / "value.json").write_text(json.dumps({
        "agent": "value",
        "rankings": [{"code": "X", "name": "X", "stars": 5}]
    }), encoding="utf-8")
    (outputs / "growth.json").write_text(json.dumps({
        "agent": "growth",
        "rankings": [{"code": "X", "name": "X", "stars": 2}]
    }), encoding="utf-8")
    (outputs / "risk.json").write_text(json.dumps({
        "agent": "risk",
        "rankings": [{"code": "X", "name": "X", "stars": 4}]
    }), encoding="utf-8")
    (outputs / "cycle.json").write_text(json.dumps({
        "agent": "cycle",
        "rankings": [{"code": "X", "name": "X", "stars": 3}]
    }), encoding="utf-8")
    try:
        sys.path.insert(0, str(AGT))
        from synthesize import main as synth_main
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            synth_main()
        result = json.loads((REPORTS / "_agent_synthesized.json").read_text(encoding="utf-8"))
        x = next(r for r in result["final_rankings"] if r["code"] == "X")
        assert x["conflict"] is True, "X 应有冲突（5星 vs 2星）"
        assert len(result["conflicts"]) >= 1
    finally:
        for f in ["value", "growth", "risk", "cycle"]:
            p = outputs / f"{f}.json"
            if p.exists(): p.unlink()


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            sys.stderr.write(f"  ✅ {t.__name__}\n")
        except AssertionError as e:
            failed += 1
            sys.stderr.write(f"  ❌ {t.__name__}: {e}\n")
    sys.stderr.write(f"\n结果：{passed} 通过 / {failed} 失败 / 共 {len(tests)} 条\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
