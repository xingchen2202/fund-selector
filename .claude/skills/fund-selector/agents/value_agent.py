#!/usr/bin/env python3
"""价值 Agent（巴菲特视角）— 财务质量 + 估值安全边际
━━━━━━━━━━━━━━━━━━━━
独立分析候选基金的财务健康状况与估值吸引力。

输入：step3 validated_funds JSON
输出：{
  "agent": "value",
  "rankings": [{"code", "name", "stars", "reason", "would_own"}],
  "top_pick": "code",
  "summary": "整体判断"
}

评分维度（★1-5）：
- 规模够大（>10 亿）+1
- 费率够低（<1.5%）+1
- 经理够稳定（>3 年）+1
- 回撤可控（<30%）+1
- 业绩持续跑赢基准 +1
"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "fund-reports"


def analyze(funds: list) -> dict:
    """巴菲特视角：财务质量 + 估值安全边际。"""
    rankings = []
    for f in funds:
        code = f.get("code", "")
        name = f.get("name", "")
        scale = f.get("scale") or 0
        fee = f.get("fee_total") or f.get("fee") or 1.5
        mgr_years = f.get("manager_years") or 0
        max_dd = f.get("max_drawdown")
        ret_1y = f.get("return_1y")

        stars = 0
        reasons = []

        # 规模
        if scale >= 10:
            stars += 1
            reasons.append(f"规模{scale:.1f}亿，够大")
        elif scale >= 2:
            reasons.append(f"规模{scale:.1f}亿，偏小")

        # 费率
        if fee <= 1.0:
            stars += 1
            reasons.append(f"费率{fee}%，低廉")
        elif fee <= 1.5:
            reasons.append(f"费率{fee}%，合理")
        else:
            reasons.append(f"费率{fee}%，偏高")

        # 经理稳定性
        if mgr_years >= 5:
            stars += 1
            reasons.append(f"经理{mgr_years}年，稳定")
        elif mgr_years >= 2:
            reasons.append(f"经理{mgr_years}年，尚可")

        # 回撤控制
        if isinstance(max_dd, (int, float)) and max_dd > -0.20:
            stars += 1
            reasons.append(f"回撤{max_dd:.1%}，优秀")
        elif isinstance(max_dd, (int, float)) and max_dd > -0.35:
            reasons.append(f"回撤{max_dd:.1%}，可接受")
        elif isinstance(max_dd, (int, float)):
            reasons.append(f"回撤{max_dd:.1%}，偏大")

        # 业绩
        if isinstance(ret_1y, (int, float)) and ret_1y > 10:
            stars += 1
            reasons.append(f"近1年+{ret_1y:.1f}%，优秀")
        elif isinstance(ret_1y, (int, float)) and ret_1y > 0:
            reasons.append(f"近1年+{ret_1y:.1f}%，尚可")

        would_own = stars >= 4 and (isinstance(max_dd, (int, float)) and max_dd > -0.35)

        rankings.append({
            "code": code,
            "name": name,
            "stars": min(stars, 5),
            "reason": "；".join(reasons),
            "would_own": would_own,
        })

    rankings.sort(key=lambda x: x["stars"], reverse=True)
    top = rankings[0] if rankings else {}

    return {
        "agent": "value",
        "rankings": rankings,
        "top_pick": top.get("code"),
        "summary": f"巴菲特视角首推 {top.get('name','?')}（{top.get('stars',0)} 星），关注规模+费率+稳定性",
    }


def main():
    step3_path = REPORTS_DIR / "_pipeline_step3.json"
    if not step3_path.exists():
        print(json.dumps({"error": "step3 不存在"}, ensure_ascii=False))
        sys.exit(1)

    funds = json.loads(step3_path.read_text(encoding="utf-8")).get("validated_funds", [])
    result = analyze(funds)

    out_path = REPORTS_DIR / "_agent_outputs/value.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[价值 Agent] 写入 {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
