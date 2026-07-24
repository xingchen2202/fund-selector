#!/usr/bin/env python3
"""测试 Agent 层（Team Lead + 4 视角 + 综合器）"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
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


def test_synthesizer_risk_veto():
    """综合器（新增）：任一视角 1 星 → 直接否决，不再首推。

    场景：成长5星 + 风险1星("无法承受最大亏损") + 价值4星 + 周期3星
    旧行为：平均 3.2 星，仍首推（风险被稀释）❌
    新行为：top_pick 应为 None，标注被否决 ✅
    """
    outputs = REPORTS / "_agent_outputs"
    outputs.mkdir(exist_ok=True)
    (outputs / "value.json").write_text(json.dumps({
        "agent": "value",
        "rankings": [{"code": "Y", "name": "高风险基金", "stars": 4, "reason": "规模大，费率低"}]
    }), encoding="utf-8")
    (outputs / "growth.json").write_text(json.dumps({
        "agent": "growth",
        "rankings": [{"code": "Y", "name": "高风险基金", "stars": 5, "reason": "赛道景气，动量强"}]
    }), encoding="utf-8")
    (outputs / "risk.json").write_text(json.dumps({
        "agent": "risk",
        "rankings": [{"code": "Y", "name": "高风险基金", "stars": 1, "reason": "无法承受最大亏损"}]
    }), encoding="utf-8")
    (outputs / "cycle.json").write_text(json.dumps({
        "agent": "cycle",
        "rankings": [{"code": "Y", "name": "高风险基金", "stars": 3, "reason": "周期顶部"}]
    }), encoding="utf-8")
    try:
        sys.path.insert(0, str(AGT))
        # 强制重新加载模块以拾取最新代码
        import importlib
        import synthesize as synth_mod
        importlib.reload(synth_mod)
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            synth_mod.main()
        result = json.loads((REPORTS / "_agent_synthesized.json").read_text(encoding="utf-8"))
        y = next(r for r in result["final_rankings"] if r["code"] == "Y")
        # 核心断言：1 星风险应触发否决
        assert y.get("vetoed") is True, f"Y 应被否决: {y}"
        assert result["top_pick"] is None, f"被否决基金不应被首推，实际 top_pick={result['top_pick']}"
        assert len(result.get("vetoes", [])) >= 1, "应有否决记录"
    finally:
        for f in ["value", "growth", "risk", "cycle"]:
            p = outputs / f"{f}.json"
            if p.exists(): p.unlink()


# ---------------------------------------------------------------------------
# 编辑/审阅 Agent（prompt 生成器模式）— 回归测试
# ---------------------------------------------------------------------------
def _run_script(name, *args):
    """运行 agents/ 下的脚本。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(AGT / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main


def test_editor_agent_generates_prompt(tmp_path=None):
    """编辑 Agent：输入初稿 → 输出含润色指令的 prompt 文件"""
    editor = _import_agent("editor_agent")
    import tempfile
    tmpdir = tempfile.mkdtemp()
    draft = Path(tmpdir) / "draft.md"
    draft.write_text("# 初稿\n\n基金规模 4.42 亿元。\n", encoding="utf-8")
    out = Path(tmpdir) / "polished.md"
    # 直接调用 main 并注入参数
    import argparse, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        editor.main = None  # guard
    # 通过 subprocess 方式调用更稳妥
    import subprocess
    r = subprocess.run([sys.executable, str(AGT / "editor_agent.py"),
                        "--input", str(draft), "--output", str(out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, f"editor_agent 崩溃: {r.stderr[-200:]}"
    assert out.exists(), "editor_agent 未生成输出文件"
    content = out.read_text(encoding="utf-8")
    assert "润色" in content, "输出应含润色指令"
    assert "初稿" in content, "输出应嵌入初稿内容"
    assert "4.42" in content, "输出应保留关键数据"


def test_reviewer_agent_generates_prompt():
    """审阅 Agent：输入文章 → 输出含审阅维度的 prompt 文件（.review.json）"""
    import subprocess, tempfile
    tmpdir = tempfile.mkdtemp()
    article = Path(tmpdir) / "article.md"
    article.write_text("# 测试文章\n\n基金近1年收益 62.03%。\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(AGT / "reviewer_agent.py"),
                        "--input", str(article)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, f"reviewer_agent 崩溃: {r.stderr[-200:]}"
    review = article.with_suffix(".review.json")
    assert review.exists(), "reviewer_agent 未生成 .review.json"
    content = review.read_text(encoding="utf-8")
    assert "事实核查" in content, "输出应含事实核查维度"
    assert "逻辑核查" in content, "输出应含逻辑核查维度"
    assert "score" in content, "输出应要求评分"
    assert "62.03%" in content, "输出应嵌入文章数据"


def _import_agent(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(AGT / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
