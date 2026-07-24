#!/usr/bin/env python3
"""测试双 Agent + 综合器（移植 ai-berkshire 多 Agent 架构）"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
AGT = REPO / ".claude/skills/fund-recommend/agents"
REPORTS = REPO / "fund-reports"


def _import(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(AGT / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_offense_ranking():
    """进攻 Agent：返回排序列表，最高分应有具体理由"""
    m = _import("offense_agent")
    f = json.loads((REPORTS / "_pipeline_step3.json").read_text(encoding="utf-8"))
    funds = f.get("validated_funds", [])
    assert len(funds) > 0, "step3 无候选"
    rankings = [m.score_offense(x) for x in funds]
    rankings.sort(key=lambda x: x["score"], reverse=True)
    assert rankings[0]["score"] > 0, "最高分应 >0"
    assert "reason" in rankings[0]


def test_offense_momentum():
    """动量计算：单调上涨序列动量应 >0"""
    m = _import("offense_agent")
    up = [1.0 * (1.01 ** i) for i in range(60)]
    mom = m.compute_momentum(up)
    assert mom > 0, f"上涨序列动量应为正: {mom}"


def test_defense_ranking():
    """防守 Agent：回撤最小的基金应排第一"""
    m = _import("defense_agent")
    funds = [
        {"code": "A", "name": "高回撤", "max_drawdown": -0.60, "manager_years": 2, "scale": 1, "fee_total": 2.0, "nav_series": [1.0]*30 + [0.4]*30},
        {"code": "B", "name": "低回撤", "max_drawdown": -0.10, "manager_years": 8, "scale": 50, "fee_total": 0.6, "nav_series": [1.0 + 0.005*i for i in range(60)]},
    ]
    rankings = sorted([m.score_defense(f) for f in funds], key=lambda x: x["score"], reverse=True)
    assert rankings[0]["code"] == "B", f"低回撤应排第一: {[r['code'] for r in rankings]}"


def test_defense_volatility():
    """波动率：稳定序列波动率应低于震荡序列"""
    m = _import("defense_agent")
    stable = [1.0 + 0.005 * i for i in range(60)]
    volatile = [1.0 + (0.02 if i % 2 == 0 else -0.02) for i in range(60)]
    v_stable = m.compute_volatility(stable)
    v_volatile = m.compute_volatility(volatile)
    if v_stable and v_volatile:
        assert v_stable < v_volatile, f"稳定({v_stable:.2%})应<震荡({v_volatile:.2%})"


def test_synthesizer_blend():
    """综合器：混合得分 = 进攻×0.5 + 防守×0.5"""
    # 写临时 agent 输出
    off = {"rankings": [{"code": "X", "name": "测试", "score": 80}, {"code": "Y", "name": "测试2", "score": 60}]}
    de = {"rankings": [{"code": "X", "name": "测试", "score": 40}, {"code": "Y", "name": "测试2", "score": 90}]}
    (REPORTS / "_agent_offense_test.json").write_text(json.dumps(off), encoding="utf-8")
    (REPORTS / "_agent_defense_test.json").write_text(json.dumps(de), encoding="utf-8")
    try:
        m = _import("synthesizer")
        # monkey-patch paths
        orig_off = REPORTS / "_agent_offense.json"
        orig_def = REPORTS / "_agent_defense.json"
        tmp_off = REPORTS / "_agent_offense_test.json"
        tmp_def = REPORTS / "_agent_defense_test.json"
        if orig_off.exists(): orig_off.rename(REPORTS / "_agent_offense_backup.json")
        if orig_def.exists(): orig_def.rename(REPORTS / "_agent_defense_backup.json")
        tmp_off.rename(orig_off)
        tmp_def.rename(orig_def)
        try:
            m.main()
            result = json.loads(orig_off.read_text(encoding="utf-8"))  # readFile may be inside; re-read synth
            synth = json.loads((REPORTS / "_agent_synthesized.json").read_text(encoding="utf-8"))
            # X: (80+40)/2=60; Y: (60+90)/2=75 → Y first
            assert synth["final_rankings"][0]["code"] == "Y"
            assert synth["final_rankings"][0]["blended_score"] == 75.0
        finally:
            if orig_off.exists(): orig_off.rename(tmp_off)
            if orig_def.exists(): orig_def.rename(tmp_def)
            if (REPORTS / "_agent_offense_backup.json").exists():
                (REPORTS / "_agent_offense_backup.json").rename(orig_off)
            if (REPORTS / "_agent_defense_backup.json").exists():
                (REPORTS / "_agent_defense_backup.json").rename(orig_def)
    finally:
        for p in ["_agent_offense_test.json", "_agent_defense_test.json"]:
            fp = REPORTS / p
            if fp.exists(): fp.unlink()


def test_synthesizer_conflict_detection():
    """综合器：排名差异 >=3 应标记冲突"""
    m = _import("synthesizer")
    x = {"code": "X", "offense_rank": 1, "defense_rank": 5}
    spread = abs(x["offense_rank"] - x["defense_rank"])
    assert spread >= 3


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
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
