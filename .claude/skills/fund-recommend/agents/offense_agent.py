#!/usr/bin/env python3
"""进攻 Agent（Offense Agent）— 成长视角排名
━━━━━━━━━━━━━━━━━━━━
目标：从候选池中找出最具进攻性的基金（高收益、强动量、景气赛道）。

输入：step3 validated_funds JSON
输出：{
  "agent": "offense",
  "rankings": [{"code", "name", "score", "reason"}],
  "top_pick": "code",
  "sector_bias": ["板块1", "板块2"],
  "reasoning": "整体判断"
}

评分维度（满分 100）：
- 近1年收益  40 分
- 近3年收益  20 分（成立不满3年按成立以来折算）
- 动量      20 分（近3月 vs 近1年趋势）
- 赛道景气   20 分（板块近期表现）
"""
import json
import math
import sys
import io
from pathlib import Path

if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
REPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "fund-reports"


def compute_momentum(nav_series: list) -> float:
    """计算近3月相对近1年的动量（>0 表示加速上涨）。"""
    if not nav_series or len(nav_series) < 60:
        return 0.0
    recent = nav_series[-60:]   # 近3月（约60个交易日）
    older = nav_series[:-60] if len(nav_series) > 60 else nav_series[:30]
    if not older or older[0] <= 0:
        return 0.0
    recent_ret = (recent[-1] - recent[0]) / recent[0] if recent[0] > 0 else 0
    older_ret = (older[-1] - older[0]) / older[0] if older[0] > 0 else 0
    return recent_ret - older_ret


def score_offense(fund: dict) -> dict:
    """对单只基金打进攻分。"""
    code = fund.get("code", "")
    name = fund.get("name", "")
    return_1y = fund.get("return_1y")
    return_3y = fund.get("return_3y")
    sector = fund.get("sector", "均衡")
    nav = fund.get("nav_series", [])

    score = 0.0
    details = []

    # 关1: 近1年收益（40 分）
    if isinstance(return_1y, (int, float)):
        s1 = min(max(return_1y / 80.0 * 40, 0), 40)  # 80% → 满分
        score += s1
        details.append(f"近1年+{return_1y:.1%}={s1:.1f}分")

    # 关2: 近3年收益（20 分，不足3年按成立以来）
    ret_3y = return_3y
    if ret_3y is None:
        ret_3y = fund.get("return_since_inception")
    if isinstance(ret_3y, (int, float)):
        s2 = min(max(ret_3y / 150.0 * 20, 0), 20)
        score += s2
        details.append(f"3年+{ret_3y:.1%}={s2:.1f}分")

    # 关3: 动量（20 分）
    mom = compute_momentum(nav)
    s3 = min(max((mom + 0.1) / 0.3 * 20, 0), 20)
    score += s3
    details.append(f"动量{mom:+.1%}={s3:.1f}分")

    # 关4: 赛道景气（20 分，基于板块近期涨幅）
    hot_sectors = {"人工智能", "半导体", "新能源", "电池", "科创", "有色"}
    s4 = 16 if any(k in sector for k in hot_sectors) else 10
    score += s4
    details.append(f"赛道{sector}={s4:.0f}分")

    return {
        "code": code,
        "name": name,
        "score": round(score, 1),
        "sector": sector,
        "details": details,
        "reason": f"进攻得分 {score:.1f}/100（{'; '.join(details)}）",
    }


def main():
    step3_path = REPORTS_DIR / "_pipeline_step3.json"
    if not step3_path.exists():
        print(json.dumps({"error": "step3 不存在"}, ensure_ascii=False))
        sys.exit(1)

    step3 = json.loads(step3_path.read_text(encoding="utf-8"))
    funds = step3.get("validated_funds", [])

    rankings = [score_offense(f) for f in funds]
    rankings.sort(key=lambda x: x["score"], reverse=True)

    # 统计板块偏好
    sector_count = {}
    for r in rankings[:3]:
        s = r.get("sector", "均衡")
        sector_count[s] = sector_count.get(s, 0) + 1
    sector_bias = sorted(sector_count, key=sector_count.get, reverse=True)

    top = rankings[0] if rankings else {}
    output = {
        "agent": "offense",
        "rankings": rankings,
        "top_pick": top.get("code"),
        "top_score": top.get("score"),
        "sector_bias": sector_bias,
        "reasoning": f"进攻视角首推 {top.get('name','?')}（{top.get('score',0)}分），偏好{'/'.join(sector_bias)}赛道",
    }

    out_path = REPORTS_DIR / "_agent_offense.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n[进攻 Agent] 写入 {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
