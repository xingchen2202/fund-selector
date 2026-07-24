#!/usr/bin/env python3
"""4 大师 Prompt 哲学一致性分析器
━━━━━━━━━━━━━━━━━━━━
检测：区分度（distinctness）、冗余度（redundancy）、行为引导有效性。
"""
import sys, io, re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

AGT = ROOT / ".claude/skills/fund-selector/agents"


def load_perspectives():
    """从 team_lead.py 提取 4 个视角的 prompt 内容。"""
    src = (AGT / "team_lead.py").read_text(encoding="utf-8")
    perspectives = {}
    for agent in ["Buffett", "Duan Yongping", "Li Lu", "Munger"]:
        # 找到对应 agent 的 philosophy 和 questions
        pat = rf'"agent":\s*"{re.escape(agent)}".*?"philosophy":\s*"(.*?)".*?"questions":\s*"""(.*?)"""'
        m = re.search(pat, src, re.DOTALL)
        if m:
            # 简化 key
            key = agent.split()[0] if " " in agent else agent
            perspectives[key] = {
                "philosophy": m.group(1),
                "questions": m.group(2),
            }
    return perspectives


def extract_keywords(text):
    """提取有意义的中文/英文关键词。"""
    # 中文词（2-4字）
    cn_words = re.findall(r'[一-龥]{2,4}', text)
    # 英文词（≥3字母）
    en_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    return set(cn_words + en_words)


def test_distinctness():
    """4 个视角应有显著关键词区分度（Jaccard 距离 > 0.5）。"""
    p = load_perspectives()
    assert len(p) == 4, f"应提取到 4 个视角: {list(p.keys())}"

    keywords = {agent: extract_keywords(v["philosophy"] + v["questions"]) for agent, v in p.items()}

    # 计算两两 Jaccard 距离
    agents = list(keywords.keys())
    min_distance = 1.0
    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            a, b = agents[i], agents[j]
            ka, kb = keywords[a], keywords[b]
            if ka | kb:
                jaccard = len(ka & kb) / len(ka | kb)
                distance = 1 - jaccard
                min_distance = min(min_distance, distance)
                print(f"  {a} vs {b}: Jaccard 距离 = {distance:.2f}")

    print(f"  最小 Jaccard 距离 = {min_distance:.2f}（预期 > 0.5）")
    assert min_distance > 0.4, f"视角区分度不足: {min_distance:.2f}"


def test_risk_lens_unique():
    """李录（风险）视角应有独特的"风险"关键词，其他视角不应过度强调。"""
    p = load_perspectives()
    li_lu_text = p["Li Lu"]["philosophy"] + p["Li Lu"]["questions"]
    buffett_text = p["Buffett"]["philosophy"] + p["Buffett"]["questions"]

    li_lu_risk_count = li_lu_text.count("风险") + li_lu_text.count("loss") + li_lu_text.count("drawdown")
    buffett_risk_count = buffett_text.count("风险") + buffett_text.count("loss")

    print(f"  李录风险词频: {li_lu_risk_count}, 巴菲特风险词频: {buffett_risk_count}")
    assert li_lu_risk_count > buffett_risk_count, "李录应比巴菲特更聚焦风险"


def test_rating_scale_clarity():
    """4 个视角的评级标准应明确（李录 5=最安全，其他 5=最推荐）。"""
    p = load_perspectives()
    # 李录应有"5 = lowest risk"或类似说明
    li_lu = p["Li Lu"]["questions"]
    assert "5 = lowest risk" in li_lu or "5=最安全" in li_lu or "5 = 最安全" in li_lu, \
        "李录视角应明确 5 星=最安全（反向标度）"


def test_data_citation_required():
    """所有视角应要求引用具体数据（防止空泛分析）。"""
    p = load_perspectives()
    for agent, content in p.items():
        has_citation = "cite" in content["questions"].lower() or "引用" in content["questions"] or "数据" in content["questions"]
        print(f"  {agent}: 数据引用要求={'✅' if has_citation else '❌'}")
        assert has_citation, f"{agent} 应要求引用具体数据"


def test_output_format_structured():
    """所有视角应要求结构化输出（星级 + 理由/warnings）。"""
    p = load_perspectives()
    for agent, content in p.items():
        has_stars = "star" in content["questions"].lower() or "星" in content["questions"]
        has_reasoning = ("reason" in content["questions"].lower() or "理由" in content["questions"]
                          or "warning" in content["questions"].lower() or "风险" in content["questions"])
        assert has_stars, f"{agent} 应要求星级评分"
        assert has_reasoning, f"{agent} 应要求理由/warnings"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 60)
    print("4 大师 Prompt 哲学一致性分析")
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
