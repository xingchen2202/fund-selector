#!/usr/bin/env python3
"""行为金融偏差评分器（Behavioral Scorer）— 量化投资者行为偏差
━━━━━━━━━━━━━━━━━━━━
对 5 类常见行为偏差进行量化评分（0-100 分，分数越高偏差越严重）。

零外部依赖 — 仅 Python stdlib (json, argparse)。

用法：
    python tools/behavioral_scorer.py score --type chasing --return-1y 0.80
    python tools/behavioral_scorer.py score-all --return-1y 0.80 --concentration 0.45 --drawdown -0.15
    python tools/behavioral_scorer.py advise --scores '{"chasing": 75, "concentration": 60}'
"""

import argparse
import json
import sys
import io

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def score_chasing(return_1y: float) -> dict:
    """追涨杀跌偏差评分。

    评分逻辑：
    - 近 1 年涨幅 >50% → 高风险追涨（75-100 分）
    - 近 1 年涨幅 20-50% → 中风险（40-75 分）
    - 近 1 年涨幅 -20%-20% → 低风险（0-40 分）
    - 近 1 年跌幅 >20% → 恐慌抛售风险（60-90 分）
    """
    if return_1y > 0.50:
        score = min(100, 75 + (return_1y - 0.50) * 100)
        level = "高风险"
        advice = f"近1年涨幅 {return_1y:.0%}，可能已高估，建议等待回调或分批建仓"
    elif return_1y > 0.20:
        score = 40 + (return_1y - 0.20) * 116
        level = "中风险"
        advice = f"近1年涨幅 {return_1y:.0%}，估值可能偏高，建议分批"
    elif return_1y > -0.20:
        score = abs(return_1y) * 200
        level = "低风险"
        advice = f"近1年涨幅 {return_1y:.0%}，估值相对合理"
    else:
        score = min(100, 60 + abs(return_1y + 0.20) * 150)
        level = "恐慌风险"
        advice = f"近1年跌幅 {abs(return_1y):.0%}，恐慌抛售？需分析基本面而非情绪"

    return {
        "bias": "chasing",
        "bias_name": "追涨杀跌",
        "score": round(score),
        "level": level,
        "advice": advice,
    }


def score_concentration(concentration: float) -> dict:
    """过度集中偏差评分。

    评分逻辑：
    - 单一资产占比 >60% → 极高风险（90-100 分）
    - 单一资产占比 40-60% → 高风险（70-90 分）
    - 单一资产占比 20-40% → 中风险（40-70 分）
    - 单一资产占比 <20% → 低风险（0-40 分）
    """
    if concentration > 0.60:
        score = min(100, 90 + (concentration - 0.60) * 250)
        level = "极高风险"
        advice = f"单一资产占比 {concentration:.0%}，严重过度集中，建议立即分散"
    elif concentration > 0.40:
        score = 70 + (concentration - 0.40) * 100
        level = "高风险"
        advice = f"单一资产占比 {concentration:.0%}，过度集中，建议降至 <30%"
    elif concentration > 0.20:
        score = 40 + (concentration - 0.20) * 150
        level = "中风险"
        advice = f"单一资产占比 {concentration:.0%}，建议关注分散度"
    else:
        score = concentration * 200
        level = "低风险"
        advice = f"单一资产占比 {concentration:.0%}，分散度良好"

    return {
        "bias": "concentration",
        "bias_name": "过度集中",
        "score": round(score),
        "level": level,
        "advice": advice,
    }


def score_panic(current_drawdown: float, market_drawdown: float) -> dict:
    """恐慌抛售偏差评分。

    评分逻辑：
    - 当前浮亏 >20% 且市场同步下跌 → 高风险恐慌（70-100 分）
    - 当前浮亏 10-20% → 中风险（40-70 分）
    - 当前浮亏 <10% → 低风险（0-40 分）
    """
    abs_dd = abs(current_drawdown)
    if abs_dd > 0.20:
        score = min(100, 70 + (abs_dd - 0.20) * 150)
        level = "高风险"
        advice = f"当前浮亏 {abs_dd:.0%}，恐慌情绪高。建议：分析基本面，非情绪化决策"
    elif abs_dd > 0.10:
        score = 40 + (abs_dd - 0.10) * 300
        level = "中风险"
        advice = f"当前浮亏 {abs_dd:.0%}，关注但不必恐慌"
    else:
        score = abs_dd * 400
        level = "低风险"
        advice = f"当前浮亏 {abs_dd:.0%}，正常波动范围"

    return {
        "bias": "panic",
        "bias_name": "恐慌抛售",
        "score": round(score),
        "level": level,
        "advice": advice,
    }


def score_all(return_1y: float = 0, concentration: float = 0,
              drawdown: float = 0, market_drawdown: float = 0) -> dict:
    """综合评分：所有偏差维度。"""
    scores = {
        "chasing": score_chasing(return_1y) if return_1y != 0 else None,
        "concentration": score_concentration(concentration) if concentration > 0 else None,
        "panic": score_panic(drawdown, market_drawdown) if drawdown != 0 else None,
    }
    # 过滤 None
    scores = {k: v for k, v in scores.items() if v is not None}

    # 计算综合得分
    all_scores = [v["score"] for v in scores.values()]
    overall = sum(all_scores) / len(all_scores) if all_scores else 0

    return {
        "overall_score": round(overall),
        "overall_level": _overall_level(overall),
        "details": scores,
    }


def _overall_level(score: float) -> str:
    if score >= 75:
        return "高风险（建议暂缓投资，先调整行为）"
    elif score >= 50:
        return "中风险（需警惕，建议分批操作）"
    elif score >= 25:
        return "低风险（基本理性，保持纪律）"
    else:
        return "健康（投资行为良好）"


def main():
    parser = argparse.ArgumentParser(description="行为金融偏差评分器 — 量化投资者行为偏差")
    sub = parser.add_subparsers(dest="command")

    # 子命令 1: 单维度评分
    s = sub.add_parser("score", help="单维度评分")
    s.add_argument("--type", choices=["chasing", "concentration", "panic"], required=True)
    s.add_argument("--return-1y", type=float, default=0, help="近1 年涨幅")
    s.add_argument("--concentration", type=float, default=0, help="单一资产占比")
    s.add_argument("--drawdown", type=float, default=0, help="当前浮亏")

    # 子命令 2: 综合评分
    sa = sub.add_parser("score-all", help="综合评分")
    sa.add_argument("--return-1y", type=float, default=0)
    sa.add_argument("--concentration", type=float, default=0)
    sa.add_argument("--drawdown", type=float, default=0)

    args = parser.parse_args()

    if args.command == "score":
        if args.type == "chasing":
            result = score_chasing(args.return_1y)
        elif args.type == "concentration":
            result = score_concentration(args.concentration)
        elif args.type == "panic":
            result = score_panic(args.drawdown, 0)
        else:
            result = {"error": "未知类型"}
    elif args.command == "score-all":
        result = score_all(args.return_1y, args.concentration, args.drawdown)
    else:
        parser.print_help()
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
