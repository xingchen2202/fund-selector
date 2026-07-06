#!/usr/bin/env python3
"""防守 Agent（Defense Agent）— 风控视角排名
━━━━━━━━━━━━━━━━━━━━
目标：从候选池中找出最安全的基金（低回撤、低波动、规模大、经理资深）。

输入：step3 validated_funds JSON
输出：{
  "agent": "defense",
  "rankings": [{"code", "name", "score", "reason"}],
  "top_pick": "code",
  "risk_flags": ["高风险提示"],
  "reasoning": "整体判断"
}

评分维度（满分 100）：
- 最大回撤   35 分（越接近 0 越高）
- 年化波动率 25 分（基于净值序列）
- 经理稳定性 20 分（任职年限）
- 规模+费率  20 分（规模大+费率低=优）
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
    """计算年化波动率（基于日收益率）。"""
    if not nav_series or len(nav_series) < 20:
        return None
    returns = []
    for i in range(1, len(nav_series)):
        if nav_series[i - 1] > 0:
            returns.append((nav_series[i] - nav_series[i - 1]) / nav_series[i - 1])
    if len(returns) < 19:
        return None
    mean_r = sum(returns) / len(returns)
    var_r = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(var_r) * math.sqrt(252)


def score_defense(fund: dict) -> dict:
    """对单只基金打防守分。"""
    code = fund.get("code", "")
    name = fund.get("name", "")
    max_dd = fund.get("max_drawdown")
    mgr_years = fund.get("manager_years") or 0
    scale_wan = fund.get("scale_wan") or (fund.get("scale", 0) * 10000 if fund.get("scale") else 0)
    fee = fund.get("fee_total") or fund.get("fee") or 1.5
    nav = fund.get("nav_series", [])

    score = 0.0
    details = []

    # 关1: 最大回撤（35 分，-15%→满分，-50%→0分）
    if isinstance(max_dd, (int, float)):
        s1 = min(max((0.50 + max_dd) / 0.35 * 35, 0), 35)
        score += s1
        details.append(f"回撤{max_dd:.1%}={s1:.1f}分")

    # 关2: 年化波动率（25 分）
    vol = compute_volatility(nav)
    if vol is not None:
        s2 = min(max((0.30 - vol) / 0.30 * 25, 0), 25)
        score += s2
        details.append(f"波动率{vol:.1%}={s2:.1f}分")
    else:
        details.append("波动率数据缺失=10分")
        score += 10

    # 关3: 经理稳定性（20 分）
    s3 = min(max(mgr_years / 8.0 * 20, 0), 20)
    score += s3
    details.append(f"经理{mgr_years}年={s3:.1f}分")

    # 关4: 规模+费率（20 分）
    scale_score = min(max(scale_wan / 50000 * 10, 0), 10)  # 5亿→满分
    fee_score = min(max((2.0 - fee) / 1.0 * 10, 0), 10)   # 1%→满分
    s4 = scale_score + fee_score
    score += s4
    details.append(f"规模{scale_wan/10000:.1f}亿+费率{fee}%={s4:.1f}分")

    return {
        "code": code,
        "name": name,
        "score": round(score, 1),
        "max_drawdown": max_dd,
        "volatility": round(vol, 4) if vol else None,
        "details": details,
        "reason": f"防守得分 {score:.1f}/100（{'; '.join(details)}）",
    }


def main():
    step3_path = REPORTS_DIR / "_pipeline_step3.json"
    if not step3_path.exists():
        print(json.dumps({"error": "step3 不存在"}, ensure_ascii=False))
        sys.exit(1)

    step3 = json.loads(step3_path.read_text(encoding="utf-8"))
    funds = step3.get("validated_funds", [])

    rankings = [score_defense(f) for f in funds]
    rankings.sort(key=lambda x: x["score"], reverse=True)

    # 风险提示
    risk_flags = []
    for r in rankings:
        if isinstance(r.get("max_drawdown"), (int, float)) and r["max_drawdown"] < -0.35:
            risk_flags.append(f"{r['code']} {r['name']} 回撤{r['max_drawdown']:.0%}接近阈值")

    top = rankings[0] if rankings else {}
    output = {
        "agent": "defense",
        "rankings": rankings,
        "top_pick": top.get("code"),
        "top_score": top.get("score"),
        "risk_flags": risk_flags,
        "reasoning": f"防守视角首推 {top.get('name','?')}（{top.get('score',0)}分），共{len(risk_flags)}个风险提示",
    }

    out_path = REPORTS_DIR / "_agent_defense.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n[防守 Agent] 写入 {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
