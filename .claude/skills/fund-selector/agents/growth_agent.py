#!/usr/bin/env python3
"""成长 Agent（段永平视角）— 商业模式 + 护城河
━━━━━━━━━━━━━━━━━━━━
独立分析候选基金的成长潜力与生意本质。

评分维度（★1-5）：
- 近1年收益 >30% +1
- 动量正（近3月加速）+1
- 赛道景气（AI/电池/半导体/科创）+1
- 费率合理（<1.5%）+1
- 规模适中（不干到百亿难掉头）+1
"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "fund-reports"

HOT_SECTORS = {"人工智能", "AI", "半导体", "芯片", "电池", "新能源", "科创", "有色"}


def compute_momentum(nav_series: list) -> float:
    if not nav_series or len(nav_series) < 60:
        return 0.0
    recent = (nav_series[-1] - nav_series[-20]) / nav_series[-20] if nav_series[-20] > 0 else 0
    older = (nav_series[-20] - nav_series[-60]) / nav_series[-60] if nav_series[-60] > 0 else 0
    return recent - older


def analyze(funds: list) -> dict:
    """段永平视角：商业模式 + 护城河 + 成长性。"""
    rankings = []
    for f in funds:
        code = f.get("code", "")
        name = f.get("name", "")
        ret_1y = f.get("return_1y")
        sector = f.get("sector", "均衡")
        fee = f.get("fee_total") or f.get("fee") or 1.5
        scale = f.get("scale") or 0
        nav = f.get("nav_series", [])

        stars = 0
        reasons = []

        # 收益
        if isinstance(ret_1y, (int, float)) and ret_1y > 30:
            stars += 1
            reasons.append(f"近1年+{ret_1y:.1f}%，成长性强")
        elif isinstance(ret_1y, (int, float)) and ret_1y > 10:
            reasons.append(f"近1年+{ret_1y:.1f}%，尚可")

        # 动量
        mom = compute_momentum(nav)
        if mom > 0.02:
            stars += 1
            reasons.append(f"动量{mom:+.1%}，加速上涨")

        # 赛道
        if any(k in sector for k in HOT_SECTORS):
            stars += 1
            reasons.append(f"{sector}赛道，景气度高")

        # 费率
        if fee <= 1.5:
            stars += 1
            reasons.append(f"费率{fee}%，合理")

        # 规模适中
        if 5 <= scale <= 100:
            stars += 1
            reasons.append(f"规模{scale:.1f}亿，灵活")
        elif scale > 100:
            reasons.append(f"规模{scale:.1f}亿，偏大")

        doing_right = stars >= 4 and fee <= 2.0

        rankings.append({
            "code": code,
            "name": name,
            "stars": min(stars, 5),
            "reason": "；".join(reasons),
            "doing_right_thing": doing_right,
        })

    rankings.sort(key=lambda x: x["stars"], reverse=True)
    top = rankings[0] if rankings else {}

    return {
        "agent": "growth",
        "rankings": rankings,
        "top_pick": top.get("code"),
        "summary": f"段永平视角首推 {top.get('name','?')}（{top.get('stars',0)} 星），关注生意本质+赛道景气",
    }


def main():
    step3_path = REPORTS_DIR / "_pipeline_step3.json"
    if not step3_path.exists():
        print(json.dumps({"error": "step3 不存在"}, ensure_ascii=False))
        sys.exit(1)

    funds = json.loads(step3_path.read_text(encoding="utf-8")).get("validated_funds", [])
    result = analyze(funds)

    out_path = REPORTS_DIR / "_agent_outputs/growth.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[成长 Agent] 写入 {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
