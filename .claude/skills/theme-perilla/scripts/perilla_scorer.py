#!/usr/bin/env python3
"""紫苏叶五因子瓶颈评分器
━━━━━━━━━━━━━━━━━━━━
移植自 Serenity股神紫苏叶理论（Bilibili BV1fT7z6QE2S）。

对给定主题产业链中的上市公司，按五因子模型评分：
1. 细分市占率前三
2. 毛利率 > 30%
3. 机构持仓 < 10%（被忽视）
4. 技术/认证壁垒
5. 产能约束

符合 3 条以上 → 标注为"潜在瓶颈节点"。
评分 ≥ 12/15 → 紫苏叶级（战略稀缺）。

用法：
    python scripts/perilla_scorer.py --theme AI算力 --output report.json
"""

import argparse
import json
import sys
from pathlib import Path

# 五因子定义
FACTORS = {
    "market_share": {
        "name": "细分市占率",
        "weight": 3,
        "description": "细分行业市占率前3",
        "check": lambda data: data.get("market_share_rank") is not None and data["market_share_rank"] <= 3,
    },
    "gross_margin": {
        "name": "毛利率",
        "weight": 3,
        "description": "毛利率 > 30%",
        "check": lambda data: data.get("gross_margin") is not None and data["gross_margin"] > 30,
    },
    "institutional": {
        "name": "机构持仓",
        "weight": 3,
        "description": "机构持仓 < 10%（被忽视）",
        "check": lambda data: data.get("institutional_pct") is not None and data["institutional_pct"] < 10,
    },
    "moat": {
        "name": "技术壁垒",
        "weight": 3,
        "description": "技术/认证壁垒（难以替代）",
        "check": lambda data: data.get("has_moat") is True,
    },
    "capacity": {
        "name": "产能约束",
        "weight": 3,
        "description": "产能约束（供给弹性低）",
        "check": lambda data: data.get("capacity_constrained") is True,
    },
}


def score_company(company: dict) -> dict:
    """对单家公司打紫苏叶分。"""
    score = 0
    evidence = []
    missing = []

    for factor_id, factor in FACTORS.items():
        try:
            if factor["check"](company):
                score += factor["weight"]
                evidence.append(f"{factor['name']} ✓")
            else:
                missing.append(factor["name"])
        except Exception:
            missing.append(f"{factor['name']}（数据缺失）")

    # 评级
    if score >= 12:
        level = "紫苏叶级（战略稀缺）"
        recommend = "强烈推荐"
    elif score >= 9:
        level = "潜在瓶颈"
        recommend = "关注"
    else:
        level = "普通持仓"
        recommend = "观望"

    return {
        "code": company.get("code"),
        "name": company.get("name"),
        "score": score,
        "max_score": 15,
        "level": level,
        "recommend": recommend,
        "evidence": evidence,
        "missing": missing,
    }


def analyze_theme(theme: str, companies: list) -> dict:
    """对主题产业链做紫苏叶穿透分析。"""
    results = []
    for c in companies:
        results.append(score_company(c))

    results.sort(key=lambda x: x["score"], reverse=True)

    bottleneck_count = sum(1 for r in results if r["score"] >= 12)
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0

    return {
        "theme": theme,
        "analysis_method": "紫苏叶五因子瓶颈评分",
        "source": "Serenity股神紫苏叶理论（Bilibili BV1fT7z6QE2S）",
        "total_companies": len(results),
        "bottleneck_count": bottleneck_count,
        "average_score": round(avg_score, 1),
        "perilla_index": round(avg_score / 15 * 100, 1),
        "companies": results,
        "top_bottlenecks": [r for r in results if r["score"] >= 12],
    }


def main():
    parser = argparse.ArgumentParser(description="紫苏叶五因子瓶颈评分器")
    parser.add_argument("--theme", required=True, help="热门主题（如 AI算力）")
    parser.add_argument("--companies", help="公司数据 JSON 文件路径")
    parser.add_argument("--output", help="输出 JSON 文件路径")
    args = parser.parse_args()

    # 读取公司数据（若提供）
    companies = []
    if args.companies and Path(args.companies).exists():
        companies = json.loads(Path(args.companies).read_text(encoding="utf-8"))

    result = analyze_theme(args.theme, companies)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
