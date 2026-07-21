#!/usr/bin/env python3
"""综合器（Synthesizer）— 合并 4 大师视角 + 冲突检测
━━━━━━━━━━━━━━━━━━━━
读取 4 个 Agent 输出，生成综合研判。

用法：
    python agents/synthesize.py

输入：
    _agent_outputs/value.json
    _agent_outputs/growth.json
    _agent_outputs/risk.json
    _agent_outputs/cycle.json

输出：
    _agent_synthesized.json
"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "fund-reports"
OUTPUTS_DIR = REPORTS_DIR / "_agent_outputs"


def load_agent(name: str) -> dict:
    p = OUTPUTS_DIR / f"{name}.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    agents = ["value", "growth", "risk", "cycle"]
    data = {a: load_agent(a) for a in agents}

    # 检查缺失
    missing = [a for a, d in data.items() if not d]
    if missing:
        print(f"[WARN] 缺失 Agent 输出: {missing}", file=sys.stderr)

    # 构建 code → {agent: rank} 映射
    all_codes = set()
    rankings = {}  # code → {agent_name: rank}

    for agent_name, agent_data in data.items():
        for i, r in enumerate(agent_data.get("rankings", [])):
            code = r.get("code", "")
            all_codes.add(code)
            if code not in rankings:
                rankings[code] = {}
            rankings[code][agent_name] = {
                "rank": i + 1,
                "stars": r.get("stars", 0),
                "reason": r.get("reason", ""),
            }

    # 综合打分（平均星级 + 风险否决机制）
    merged = []
    conflicts = []
    vetoes = []  # 新增：风险否决列表
    for code in all_codes:
        agent_ranks = rankings.get(code, {})
        stars_list = [v["stars"] for v in agent_ranks.values() if v.get("stars")]
        avg_stars = sum(stars_list) / len(stars_list) if stars_list else 0

        # 冲突检测：星级差 >= 2
        if stars_list and max(stars_list) - min(stars_list) >= 2:
            conflicts.append(f"{code}：最高{max(stars_list)}星 vs 最低{min(stars_list)}星，视角分歧大")

        # 新增：风险否决 — 任一视角 1 星（尤其风控/合规）→ 直接否决
        vetoed = False
        veto_reasons = []
        for agent_name, rank_info in agent_ranks.items():
            s = rank_info.get("stars", 5)
            reason = rank_info.get("reason", "")
            if s <= 1:
                vetoed = True
                veto_reasons.append(f"{agent_name} {s}星（{reason}）")

        # 找 name
        name = ""
        for a in agents:
            for r in data.get(a, {}).get("rankings", []):
                if r.get("code") == code:
                    name = r.get("name", "")
                    break

        merged.append({
            "code": code,
            "name": name,
            "avg_stars": round(avg_stars, 1),
            "agent_ranks": agent_ranks,
            "conflict": max(stars_list) - min(stars_list) >= 2 if stars_list else False,
            "vetoed": vetoed,
            "veto_reasons": veto_reasons,
        })

        if vetoed:
            vetoes.append(f"{code}（{name}）：被否决 — {'; '.join(veto_reasons)}")

    merged.sort(key=lambda x: x["avg_stars"], reverse=True)

    # 首推：优先选择未被否决的最高分
    top = {}
    for m in merged:
        if not m.get("vetoed"):
            top = m
            break

    # 否决后备选：若全部被否决，返回最接近合规的候选（最高分但标注风险）
    fallback = None
    if not top and merged:
        fallback = {
            "code": merged[0].get("code"),
            "name": merged[0].get("name"),
            "avg_stars": merged[0].get("avg_stars"),
            "note": "虽未达最优且被否决，但为当前最高分候选，建议谨慎考虑或扩大筛选范围"
        }

    output = {
        "final_rankings": merged,
        "conflicts": conflicts,
        "vetoes": vetoes,
        "top_pick": top.get("code") if top else None,
        "top_avg_stars": top.get("avg_stars") if top else None,
        "top_vetoed": False if top else True,
        "fallback_candidate": fallback,  # 新增：否决后备选
        "consensus": (
            f"综合首推 {top.get('name','?')}（{top.get('avg_stars',0)} 星），{len(conflicts)} 个视角冲突"
            if top
            else f"⚠️ 所有候选均被风险否决，建议扩大筛选范围或调整风险偏好"
        ),
    }

    out_path = REPORTS_DIR / "_agent_synthesized.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n[综合器] 写入 {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
