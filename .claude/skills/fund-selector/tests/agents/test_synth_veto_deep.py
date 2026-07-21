#!/usr/bin/env python3
"""综合器风险否决深度压测"""
import sys, io, json, importlib
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPORTS = Path(r"C:\Users\22218\Desktop\fund-selector\fund-reports")
AGT = Path(r"C:\Users\22218\Desktop\fund-selector\.claude\skills\fund-selector\agents")
OUTPUTS = REPORTS / "_agent_outputs"


def setup_outputs(files: dict):
    OUTPUTS.mkdir(exist_ok=True)
    for name, data in files.items():
        (OUTPUTS / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def run_synth():
    sys.path.insert(0, str(AGT))
    import synthesize
    importlib.reload(synthesize)
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        synthesize.main()
    return json.loads((REPORTS / "_agent_synthesized.json").read_text(encoding="utf-8"))


def cleanup():
    for f in ["value", "growth", "risk", "cycle"]:
        p = OUTPUTS / f"{f}.json"
        if p.exists():
            p.unlink()
    p = REPORTS / "_agent_synthesized.json"
    if p.exists():
        p.unlink()


def test_single_veto():
    """单基金单视角1星 → 否决，top_pick=None。"""
    setup_outputs({
        "value": {"agent": "value", "rankings": [{"code": "A", "name": "A", "stars": 4}]},
        "growth": {"agent": "growth", "rankings": [{"code": "A", "name": "A", "stars": 5}]},
        "risk": {"agent": "risk", "rankings": [{"code": "A", "name": "A", "stars": 1, "reason": "无法承受亏损"}]},
        "cycle": {"agent": "cycle", "rankings": [{"code": "A", "name": "A", "stars": 3}]},
    })
    try:
        r = run_synth()
        assert r["top_pick"] is None, f"应被否决: {r['top_pick']}"
        assert len(r["vetoes"]) == 1
        a = r["final_rankings"][0]
        assert a["vetoed"] is True
    finally:
        cleanup()


def test_multiple_funds_mixed():
    """多基金：A被否决，B正常 → top_pick应为B。"""
    setup_outputs({
        "value": {"agent": "value", "rankings": [{"code": "A", "name": "A", "stars": 4}, {"code": "B", "name": "B", "stars": 4}]},
        "growth": {"agent": "growth", "rankings": [{"code": "A", "name": "A", "stars": 5}, {"code": "B", "name": "B", "stars": 4}]},
        "risk": {"agent": "risk", "rankings": [{"code": "A", "name": "A", "stars": 1}, {"code": "B", "name": "B", "stars": 4}]},
        "cycle": {"agent": "cycle", "rankings": [{"code": "A", "name": "A", "stars": 3}, {"code": "B", "name": "B", "stars": 3}]},
    })
    try:
        r = run_synth()
        assert r["top_pick"] == "B", f"应首推B: {r['top_pick']}"
        assert len(r["vetoes"]) == 1  # 只有A被否决
        b = next(x for x in r["final_rankings"] if x["code"] == "B")
        assert b["vetoed"] is False
    finally:
        cleanup()


def test_all_vetoed():
    """全部基金被否决 → top_pick=None，共识标注全部否决。"""
    setup_outputs({
        "value": {"agent": "value", "rankings": [{"code": "A", "name": "A", "stars": 4}]},
        "growth": {"agent": "growth", "rankings": [{"code": "A", "name": "A", "stars": 5}]},
        "risk": {"agent": "risk", "rankings": [{"code": "A", "name": "A", "stars": 1}]},
        "cycle": {"agent": "cycle", "rankings": [{"code": "A", "name": "A", "stars": 1}]},
    })
    try:
        r = run_synth()
        assert r["top_pick"] is None
        assert "全部" in r["consensus"] or "否决" in r["consensus"]
    finally:
        cleanup()


def test_no_veto():
    """全部≥2星 → 正常首推最高分。"""
    setup_outputs({
        "value": {"agent": "value", "rankings": [{"code": "A", "name": "A", "stars": 5}]},
        "growth": {"agent": "growth", "rankings": [{"code": "A", "name": "A", "stars": 4}]},
        "risk": {"agent": "risk", "rankings": [{"code": "A", "name": "A", "stars": 3}]},
        "cycle": {"agent": "cycle", "rankings": [{"code": "A", "name": "A", "stars": 4}]},
    })
    try:
        r = run_synth()
        assert r["top_pick"] == "A"
        assert len(r["vetoes"]) == 0
        assert r["final_rankings"][0]["vetoed"] is False
    finally:
        cleanup()


def test_2star_no_veto():
    """最低2星（非1星）→ 不应否决。"""
    setup_outputs({
        "value": {"agent": "value", "rankings": [{"code": "A", "name": "A", "stars": 5}]},
        "growth": {"agent": "growth", "rankings": [{"code": "A", "name": "A", "stars": 4}]},
        "risk": {"agent": "risk", "rankings": [{"code": "A", "name": "A", "stars": 2}]},
        "cycle": {"agent": "cycle", "rankings": [{"code": "A", "name": "A", "stars": 3}]},
    })
    try:
        r = run_synth()
        assert r["top_pick"] == "A", f"2星不应否决: {r['top_pick']}"
        assert len(r["vetoes"]) == 0
    finally:
        cleanup()


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
