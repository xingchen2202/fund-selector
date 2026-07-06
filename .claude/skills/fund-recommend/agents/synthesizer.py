#!/usr/bin/env python3
"""综合器（Synthesizer）— 合并进攻+防守双视角
━━━━━━━━━━━━━━━━━━━━
输入：_offense.json + _defense.json
输出：{
  "final_rankings": [{"code", "name", "blended_score", "offense_rank", "defense_rank", "consensus"}],
  "conflicts": [冲突描述],
  "consensus": "整体判断",
  "top_pick": "code"
}

混合得分 = offense_score × 0.5 + defense_score × 0.5
"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "fund-reports"


def main():
    offense_path = REPORTS_DIR / "_agent_offense.json"
    defense_path = REPORTS_DIR / "_agent_defense.json"

    if not offense_path.exists() or not defense_path.exists():
        print(json.dumps({"error": "agent 输出缺失"}, ensure_ascii=False))
        sys.exit(1)

    offense = json.loads(offense_path.read_text(encoding="utf-8"))
    defense = json.loads(defense_path.read_text(encoding="utf-8"))

    # 构建 code → rank 映射
    off_rank = {r["code"]: (i + 1, r["score"]) for i, r in enumerate(offense.get("rankings", []))}
    def_rank = {r["code"]: (i + 1, r["score"]) for i, r in enumerate(defense.get("rankings", []))}

    # 合并所有代码
    all_codes = set(off_rank.keys()) | set(def_rank.keys())

    merged = []
    conflicts = []
    for code in all_codes:
        o_rank, o_score = off_rank.get(code, (99, 0))
        d_rank, d_score = def_rank.get(code, (99, 0))
        blended = round(o_score * 0.5 + d_score * 0.5, 1)

        # 检测冲突：两视角排名差 >= 3
        consensus = "一致"
        if abs(o_rank - d_rank) >= 3:
            if o_rank < d_rank:
                consensus = "进攻强/防守弱"
                conflicts.append(f"{code}：进攻第{o_rank} vs 防守第{d_rank}，风格激进")
            else:
                consensus = "防守强/进攻弱"
                conflicts.append(f"{code}：防守第{d_rank} vs 进攻第{o_rank}，偏保守")

        # 找 name
        name = ""
        for r in offense.get("rankings", []) + defense.get("rankings", []):
            if r["code"] == code:
                name = r["name"]
                break

        merged.append({
            "code": code,
            "name": name,
            "blended_score": blended,
            "offense_rank": o_rank,
            "offense_score": o_score,
            "defense_rank": d_rank,
            "defense_score": d_score,
            "rank_spread": abs(o_rank - d_rank),
            "consensus": consensus,
        })

    merged.sort(key=lambda x: x["blended_score"], reverse=True)
    top = merged[0] if merged else {}

    output = {
        "final_rankings": merged,
        "conflicts": conflicts,
        "top_pick": top.get("code"),
        "top_blended": top.get("blended_score"),
        "consensus": f"综合首推 {top.get('name','?')}（混合{top.get('blended_score',0)}分），{len(conflicts)}个视角冲突",
    }

    out_path = REPORTS_DIR / "_agent_synthesized.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n[综合器] 写入 {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
