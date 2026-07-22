#!/usr/bin/env python3
"""输出质量评估框架 — 评估推荐输出的质量
━━━━━━━━━━━━━━━━━━━━
评估维度：
1. 完整性（Completeness）：是否包含所有必要模块
2. 可操作性（Actionability）：建议是否具体可执行
3. 风险披露（Risk Disclosure）：免责声明是否充分
4. 可读性（Readability）：结构是否清晰
"""

import sys, io, json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def evaluate_output_quality(output: dict) -> dict:
    """评估推荐输出质量。

    Args:
        output: 推荐输出字典

    Returns:
        dict: 质量评分（0-100）和详细评估
    """
    scores = {}

    # 1. 完整性（30 分）
    required_fields = ["funds", "allocation", "execution_plan", "risk_warning"]
    present = sum(1 for f in required_fields if f in output and output[f])
    scores["completeness"] = (present / len(required_fields)) * 30

    # 2. 可操作性（30 分）
    actionable_score = 0
    if output.get("funds"):
        # 检查是否有具体金额
        has_amount = all("amount" in f for f in output["funds"])
        if has_amount:
            actionable_score += 15
        # 检查是否有具体基金代码
        has_code = all("code" in f for f in output["funds"])
        if has_code:
            actionable_score += 15
    scores["actionability"] = actionable_score

    # 3. 风险披露（25 分）
    risk_score = 0
    if output.get("risk_warning"):
        risk_score += 10
    if output.get("disclaimers"):
        risk_score += 10
    if output.get("stress_test_result"):
        risk_score += 5
    scores["risk_disclosure"] = risk_score

    # 4. 可读性（15 分）
    readability_score = 0
    if output.get("summary"):
        readability_score += 5
    if output.get("allocation"):
        readability_score += 5
    if output.get("execution_plan"):
        readability_score += 5
    scores["readability"] = readability_score

    # 总分
    total = sum(scores.values())

    return {
        "total_score": round(total),
        "grade": _grade(total),
        "details": scores,
        "improvement_suggestions": _suggestions(scores),
    }


def _grade(score: float) -> str:
    if score >= 90:
        return "A（优秀）"
    elif score >= 75:
        return "B（良好）"
    elif score >= 60:
        return "C（合格）"
    elif score >= 40:
        return "D（待改进）"
    else:
        return "F（不合格）"


def _suggestions(scores: dict) -> list:
    suggestions = []
    if scores["completeness"] < 25:
        suggestions.append("补充缺失模块（配置/执行计划/风险提示）")
    if scores["actionability"] < 25:
        suggestions.append("增加具体金额和基金代码")
    if scores["risk_disclosure"] < 20:
        suggestions.append("强化免责声明和压力测试结果")
    if scores["readability"] < 12:
        suggestions.append("优化结构（摘要/配置/计划分层）")
    return suggestions


def test_quality_evaluation():
    """测试质量评估框架。"""
    print("=" * 60)
    print("输出质量评估框架测试")
    print("=" * 60)

    scenarios = [
        ("完整输出", {
            "funds": [{"code": "A", "name": "A", "amount": 2000}],
            "allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
            "execution_plan": "月投 3000，分批建仓",
            "risk_warning": "投资有风险",
            "disclaimers": ["不构成投资建议"],
            "stress_test_result": {"max_drawdown": -0.25},
            "summary": "推荐稳健组合",
        }),
        ("部分输出", {
            "funds": [{"code": "A", "amount": 2000}],
            "allocation": {"stock": 0.7},
        }),
        ("最小输出", {
            "funds": [{"name": "A"}],
        }),
    ]

    for name, output in scenarios:
        r = evaluate_output_quality(output)
        print(f"\n  [{name}]")
        print(f"    总分: {r['total_score']}/100 ({r['grade']})")
        print(f"    完整性: {r['details']['completeness']:.0f}/30")
        print(f"    可操作性: {r['details']['actionability']:.0f}/30")
        print(f"    风险披露: {r['details']['risk_disclosure']:.0f}/25")
        print(f"    可读性: {r['details']['readability']:.0f}/15")
        if r["improvement_suggestions"]:
            print(f"    改进建议: {r['improvement_suggestions']}")

    print("\n  ✅ 质量评估框架正常")


def main():
    test_quality_evaluation()
    print("\n" + "=" * 60)
    print("输出质量评估框架测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
