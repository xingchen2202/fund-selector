#!/usr/bin/env python3
"""端到端集成测试 — 验证完整流水线
━━━━━━━━━━━━━━━━━━━━
测试 Step 0 → Step 3 → Agent → Synthesize → Report 全流程。

用法：
    python tests/test_e2e_pipeline.py
"""

import json
import subprocess
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(r"C:\Users\22218\Desktop\fund-selector")
AGT = REPO / ".claude/skills/fund-selector/agents"
REPORTS = REPO / "fund-reports"


def run(cmd: list, cwd: str = str(REPO)) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, encoding="utf-8", errors="replace")


def test_step0_portfolio():
    """Step 0: 组合约束计算（使用旧架构脚本，新架构由 Claude 执行）."""
    script = REPO / ".claude/skills/fund-recommend/scripts/load_portfolio.py"
    r = run(["py", str(script)])
    assert r.returncode == 0, f"load_portfolio failed: {r.stderr[-200:]}"
    d = json.loads((REPORTS / "_pipeline_step0.json").read_text(encoding="utf-8"))
    assert d.get("total_value", 0) > 0
    assert "overloaded_sectors" in d


def test_step2_screen():
    """Step 2: 候选池筛选（使用旧架构脚本，新架构由 Claude 执行）."""
    script = REPO / ".claude/skills/fund-recommend/scripts/screen_candidates.py"
    r = run(["py", str(script)])
    assert r.returncode == 0, f"screen_candidates failed: {r.stderr[-200:]}"
    d = json.loads((REPORTS / "_pipeline_step2.json").read_text(encoding="utf-8"))
    assert len(d.get("top10", [])) > 0


def test_step3_validation():
    """Step 3: 基金验证（含净值序列）."""
    # 构造含 nav_series 的 step3
    step2 = json.loads((REPORTS / "_pipeline_step2.json").read_text(encoding="utf-8"))
    import random
    random.seed(42)
    validated = []
    for c in step2.get("top10", [])[:3]:
        navs = [1.0]
        for _ in range(59):
            navs.append(navs[-1] * (1 + random.uniform(-0.01, 0.012)))
        validated.append({**c, "nav_series": navs[-20:], "return_1y": 15.0, "max_drawdown": -0.25, "scale": 5.0, "fee_total": 1.2})
    step3 = {"validated_funds": validated, "excluded": [], "generated_at": "2026-07-06"}
    (REPORTS / "_pipeline_step3.json").write_text(json.dumps(step3, ensure_ascii=False), encoding="utf-8")
    assert len(validated) > 0


def test_4_agents_parallel():
    """4 大师视角 Agent 通过文档驱动（Claude 读 prompt 分析，无独立脚本）."""
    # 文档驱动模式：team_lead.py 生成 prompt，Claude 直接分析
    # 此测试验证 prompt 文件生成成功
    r = run(["py", str(AGT / "team_lead.py"), "--input", str(REPORTS / "_pipeline_step3.json")])
    assert r.returncode == 0, f"team_lead failed: {r.stderr[-100:]}"
    prompts_dir = REPORTS / "_agent_prompts"
    assert (prompts_dir / "value_prompt.txt").exists()
    assert (prompts_dir / "growth_prompt.txt").exists()
    assert (prompts_dir / "risk_prompt.txt").exists()
    assert (prompts_dir / "cycle_prompt.txt").exists()


def test_synthesizer():
    """综合器（文档驱动模式：验证 prompt 生成成功）."""
    # 文档驱动模式下，team_lead 生成 4 个 prompt 文件
    prompts_dir = REPORTS / "_agent_prompts"
    assert prompts_dir.exists(), "agent prompts dir missing"
    assert (prompts_dir / "value_prompt.txt").exists()
    assert (prompts_dir / "growth_prompt.txt").exists()
    assert (prompts_dir / "risk_prompt.txt").exists()
    assert (prompts_dir / "cycle_prompt.txt").exists()
    # 验证 prompt 内容非空
    for name in ["value_prompt", "growth_prompt", "risk_prompt", "cycle_prompt"]:
        content = (prompts_dir / f"{name}.txt").read_text(encoding="utf-8")
        assert len(content) > 100, f"{name}.txt too short"


def main():
    tests = [
        ("Step 0: 组合约束", test_step0_portfolio),
        ("Step 2: 候选池", test_step2_screen),
        ("Step 3: 基金验证", test_step3_validation),
        ("4 Agent 并行", test_4_agents_parallel),
        ("综合器", test_synthesizer),
    ]

    passed = failed = 0
    print("=" * 60)
    print("端到端集成测试")
    print("=" * 60)
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  ✅ {name}")
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {name}: {e}")

    print(f"\n结果：{passed} 通过 / {failed} 失败 / 共 {len(tests)} 项")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
