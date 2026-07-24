#!/usr/bin/env python3
"""4 大师哲学命题深度评估
━━━━━━━━━━━━━━━━━━━━
评估每个视角是否抓住其哲学核心，以及是否与基金研究场景适配。
"""
import sys, io, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

AGT = ROOT / ".claude/skills/fund-selector/agents"


def load_perspectives():
    src = (AGT / "team_lead.py").read_text(encoding="utf-8")
    perspectives = {}
    for agent in ["Buffett", "Duan Yongping", "Li Lu", "Munger"]:
        pat = rf'"agent":\s*"{re.escape(agent)}".*?"philosophy":\s*"(.*?)".*?"questions":\s*"""(.*?)"""'
        m = re.search(pat, src, re.DOTALL)
        if m:
            key = agent.split()[0]
            perspectives[key] = {"philosophy": m.group(1), "questions": m.group(2)}
    return perspectives


def test_buffett_moat_focus():
    """巴菲特视角核心：护城河 + 企业质地（非基金指标）。"""
    p = load_perspectives()
    text = p["Buffett"]["philosophy"] + p["Buffett"]["questions"]
    # 应有护城河/ROE/自由现金流等企业分析关键词
    has_moat = "moat" in text.lower() or "护城河" in text
    has_roe = "ROE" in text or "roe" in text
    has_fcf = "free cash flow" in text.lower() or "自由现金流" in text
    print(f"  护城河: {'✅' if has_moat else '❌'}, ROE: {'✅' if has_roe else '❌'}, FCF: {'✅' if has_fcf else '❌'}")
    assert has_moat and has_roe, "巴菲特应聚焦护城河与 ROE"


def test_duan_integrity_focus():
    """段永平视角核心：本分 + 做对的事情 + 不追热点。"""
    p = load_perspectives()
    text = p["Duan"]["philosophy"] + p["Duan"]["questions"]
    has_integrity = "integrity" in text.lower() or "本分" in text or "honest" in text.lower()
    has_right_things = "right things" in text.lower() or "对的事情" in text
    has_no_style_drift = "style drift" in text.lower() or "漂移" in text or "追热点" in text
    print(f"  本分: {'✅' if has_integrity else '❌'}, 做对的事: {'✅' if has_right_things else '❌'}, 不漂移: {'✅' if has_no_style_drift else '❌'}")
    assert has_integrity or has_right_things, "段永平应关注本分/做对的事情"


def test_lilu_risk_first():
    """李录视角核心：风险第一 + "不知道的未知"。"""
    p = load_perspectives()
    text = p["Li"]["philosophy"] + p["Li"]["questions"]
    has_risk_first = "what could go wrong" in text.lower() or "风险" in text
    has_unknown = "unknown" in text.lower() or "不知道" in text
    has_max_loss = "maximum loss" in text.lower() or "最大亏损" in text or "maximum risk" in text.lower()
    print(f"  风险第一: {'✅' if has_risk_first else '❌'}, 未知未知: {'✅' if has_unknown else '❌'}, 最大损失: {'✅' if has_max_loss else '❌'}")
    assert has_risk_first and has_max_loss, "李录应聚焦风险第一与最大损失"


def test_munger_invert():
    """芒格视角核心：反过来想 + 多学科。"""
    p = load_perspectives()
    text = p["Munger"]["philosophy"] + p["Munger"]["questions"]
    has_invert = "invert" in text.lower() or "反过来" in text
    has_multidisciplinary = "multidisciplinary" in text.lower() or "多学科" in text
    has_consensus = "consensus" in text.lower() or "共识" in text
    print(f"  反过来想: {'✅' if has_invert else '❌'}, 多学科: {'✅' if has_multidisciplinary else '❌'}, 共识: {'✅' if has_consensus else '❌'}")
    assert has_invert and has_multidisciplinary, "芒格应聚焦反过来想与多学科"


def test_no_redundant_fund_metrics():
    """4 个视角不应都聚焦"基金筛选指标"（规模/费率/经理任期）。
    例外：段永平可提及 fee/scale（"本分"哲学在基金层面的正当应用：诚实收费、规模克制）。"""
    p = load_perspectives()
    for agent, content in p.items():
        text = content["philosophy"] + content["questions"]
        # 经理任期是纯筛选指标，不应出现在哲学视角
        has_tenure = "manager.*3.*year" in text.lower() or "经理任职" in text or "manager.*year" in text.lower()
        print(f"  {agent}: 经理任期筛选词={'❌ 无' if not has_tenure else '⚠️ 有'}")
        assert not has_tenure, f"{agent} 不应将经理任期（筛选指标）混入哲学视角"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 60)
    print("4 大师哲学命题深度评估")
    print("=" * 60)
    for t in tests:
        print(f"\n--- {t.__name__} ---")
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
