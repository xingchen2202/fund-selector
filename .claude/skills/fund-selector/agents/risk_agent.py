#!/usr/bin/env python3
"""风控 Agent（李录视角）— 风险信号 + 管理质量
━━━━━━━━━━━━━━━━━━━━
独立分析候选基金的最大风险与不确定性。

评分维度（★1-5，5 星=风险最低）：
- 最大回撤 <20% +1
- 年化波动率 <15% +1
- 经理任职 >3 年 +1
- 规模 >5 亿（不清盘风险）+1
- 费率 <2%（不侵蚀收益）+1
"""
import json
import math
import sys
import io
from pathlib import Path

if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "fund-reports"


def compute_volatility(nav_series: list) -> float:
    if not nav_series or len(nav_series) < 20:
        return None
    rets = [(nav_series[i] - nav_series[i-1]) / nav_series[i-1] for i in range(1, len(nav_series)) if nav_series[i-1] > 0]
    if len(rets) < 19:
        return None
    mr = sum(rets) / len(rets)
    var = sum((r - mr) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252)


def analyze(funds: list) -> dict:
    """李录视角：最大风险 + 不确定性。"""
    rankings = []
    risk_flags = []

    for f in funds:
        code = f.get("code", "")
        name = f.get("name", "")
        max_dd = f.get("max_drawdown")
        nav = f.get("nav_series", [])
        mgr = f.get("manager_years") or 0
        scale = f.get("scale") or 0
        fee = f.get("fee_total") or f.get("fee") or 1.5

        stars = 0
        reasons = []

        # 回撤
        if isinstance(max_dd, (int, float)) and max_dd > -0.20:
            stars += 1
            reasons.append(f"回撤{max_dd:.1%}，优秀")
        elif isinstance(max_dd, (int, float)) and max_dd > -0.35:
            reasons.append(f"回撤{max_dd:.1%}，可接受")
        elif isinstance(max_dd, (int, float)):
            reasons.append(f"回撤{max_dd:.1%}，偏大")
            risk_flags.append(f"{code} {name}: 回撤{max_dd:.0%}超阈值")

        # 波动率
        vol = compute_volatility(nav)
        if vol is not None and vol < 0.15:
            stars += 1
            reasons.append(f"波动率{vol:.1%}，稳定")
        elif vol is not None and vol >= 0.25:
            reasons.append(f"波动率{vol:.1%}，偏大")

        # 经理
        if mgr >= 3:
            stars += 1
            reasons.append(f"经理{mgr}年，稳定")
        else:
            risk_flags.append(f"{code} {name}: 经理仅{mgr}年")

        # 规模
        if scale >= 5:
            stars += 1
            reasons.append(f"规模{scale:.1f}亿，安全")
        elif scale > 0 and scale < 2:
            risk_flags.append(f"{code} {name}: 规模{scale:.1f}亿，有清盘风险")

        # 费率
        if fee <= 2.0:
            stars += 1
            reasons.append(f"费率{fee}%，合理")
        else:
            reasons.append(f"费率{fee}%，偏高")

        accept = isinstance(max_dd, (int, float)) and max_dd > -0.40 and stars >= 3

        rankings.append({
            "code": code,
            "name": name,
            "stars": min(stars, 5),
            "reason": "；".join(reasons),
            "max_loss_acceptable": accept,
        })

    rankings.sort(key=lambda x: x["stars"], reverse=True)
    top = rankings[0] if rankings else {}

    return {
        "agent": "risk",
        "rankings": rankings,
        "top_pick": top.get("code"),
        "risk_flags": risk_flags,
        "summary": f"李录视角首推 {top.get('name','?')}（{top.get('stars',0)} 星），{len(risk_flags)} 个风险提示",
    }


def main():
    step3_path = REPORTS_DIR / "_pipeline_step3.json"
    if not step3_path.exists():
        print(json.dumps({"error": "step3 不存在"}, ensure_ascii=False))
        sys.exit(1)

    funds = json.loads(step3_path.read_text(encoding="utf-8")).get("validated_funds", [])
    result = analyze(funds)

    out_path = REPORTS_DIR / "_agent_outputs/risk.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[风控 Agent] 写入 {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
