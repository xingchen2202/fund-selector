#!/usr/bin/env python3
"""周期 Agent（芒格视角）— 行业格局 + 竞争态势
━━━━━━━━━━━━━━━━━━━━
独立分析候选基金重仓行业的周期位置与竞争格局。

评分维度（★1-5）：
- 行业处于复苏/扩张期 +1
- 竞争格局清晰（龙头明确）+1
- 政策友好 +1
- 估值处于历史低位 +1
- 催化剂可见 +1
"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "fund-reports"

# 行业周期判断（基于近期政策和景气度）
CYCLE_MAP = {
    "人工智能": {"phase": "扩张期", "stars": 5, "policy": "强支持"},
    "AI": {"phase": "扩张期", "stars": 5, "policy": "强支持"},
    "半导体": {"phase": "复苏期", "stars": 4, "policy": "国产替代"},
    "芯片": {"phase": "复苏期", "stars": 4, "policy": "国产替代"},
    "电池": {"phase": "扩张期", "stars": 5, "policy": "新能源政策"},
    "新能源": {"phase": "扩张期", "stars": 4, "policy": "碳中和"},
    "有色": {"phase": "震荡期", "stars": 3, "policy": "中性"},
    "银行": {"phase": "复苏期", "stars": 3, "policy": "息差企稳"},
    "消费": {"phase": "震荡期", "stars": 3, "policy": "中性"},
    "医药": {"phase": "复苏期", "stars": 4, "policy": "创新药支持"},
    "均衡": {"phase": "不确定", "stars": 3, "policy": "—"},
}


def analyze(funds: list) -> dict:
    """芒格视角：行业格局 + 竞争态势 + 周期位置。"""
    rankings = []
    for f in funds:
        code = f.get("code", "")
        name = f.get("name", "")
        sector = f.get("sector", "均衡")
        ret_1y = f.get("return_1y")
        nav = f.get("nav_series", [])

        info = CYCLE_MAP.get(sector, CYCLE_MAP["均衡"])
        stars = info["stars"]
        reasons = [f"{sector}行业处于{info['phase']}，政策{info['policy']}"]

        # 近期表现验证周期
        if isinstance(ret_1y, (int, float)) and ret_1y > 30:
            reasons.append(f"近1年+{ret_1y:.1f}%，景气度验证")
        elif isinstance(ret_1y, (int, float)) and ret_1y < -10:
            reasons.append(f"近1年{ret_1y:.1f}%，景气度存疑")

        # 估值分位（基于净值序列高低点）
        if nav:
            try:
                current = nav[-1]
                high = max(nav)
                low = min(nav)
                if high > low:
                    percentile = (current - low) / (high - low)
                    if percentile > 0.7:
                        reasons.append(f"当前处于历史 {percentile:.0%} 分位，偏贵")
                        stars = max(stars - 1, 1)
                    elif percentile < 0.3:
                        reasons.append(f"当前处于历史 {percentile:.0%} 分位，偏便宜")
                        stars = min(stars + 1, 5)
            except Exception:
                pass

        timing = stars >= 4

        rankings.append({
            "code": code,
            "name": name,
            "stars": min(stars, 5),
            "reason": "；".join(reasons),
            "good_timing": timing,
        })

    rankings.sort(key=lambda x: x["stars"], reverse=True)
    top = rankings[0] if rankings else {}

    return {
        "agent": "cycle",
        "rankings": rankings,
        "top_pick": top.get("code"),
        "summary": f"芒格视角首推 {top.get('name','?')}（{top.get('stars',0)} 星），关注{top.get('sector','?')}行业周期位置",
    }


def main():
    step3_path = REPORTS_DIR / "_pipeline_step3.json"
    if not step3_path.exists():
        print(json.dumps({"error": "step3 不存在"}, ensure_ascii=False))
        sys.exit(1)

    funds = json.loads(step3_path.read_text(encoding="utf-8")).get("validated_funds", [])
    result = analyze(funds)

    out_path = REPORTS_DIR / "_agent_outputs/cycle.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[周期 Agent] 写入 {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
