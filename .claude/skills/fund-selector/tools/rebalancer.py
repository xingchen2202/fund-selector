#!/usr/bin/env python3
"""再平衡自动化工具（Rebalancer）— 阈值触发/定期回顾/风格漂移
━━━━━━━━━━━━━━━━━━━━
自动化再平衡决策：触发条件检测 + 再平衡操作生成。

零外部依赖 — 仅 Python stdlib (json, argparse)。

用法：
    python tools/rebalancer.py check-threshold --target '{"stock":0.7,"bond":0.2,"cash":0.1}' --actual '{"stock":0.82,"bond":0.1,"cash":0.08}'
    python tools/rebalancer.py check-style-drift --claimed "均衡" --actual '{"半导体":70}'
    python tools/rebalancer.py generate-actions --target '{"stock":0.7,"bond":0.2}' --actual '{"stock":0.82,"bond":0.1}'
"""

import argparse
import json
import sys
import io

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 再平衡触发阈值
REBALANCE_THRESHOLD = 0.10  # 偏离 >10% 触发
# 风格漂移阈值
STYLE_DRIFT_THRESHOLD = 50  # 单一行业 >50% 视为漂移


def check_threshold(target: dict, actual: dict) -> dict:
    """阈值触发检测：单一资产偏离目标 >10% 时触发再平衡。"""
    triggers = []
    for asset in target:
        t = target.get(asset, 0)
        a = actual.get(asset, 0)
        deviation = abs(t - a)
        if deviation > REBALANCE_THRESHOLD:
            triggers.append({
                "asset": asset,
                "target": t,
                "actual": a,
                "deviation": round(deviation, 4),
                "action": "减仓" if a > t else "加仓",
            })

    return {
        "threshold": REBALANCE_THRESHOLD,
        "triggered": len(triggers) > 0,
        "triggers": triggers,
        "recommendation": "执行再平衡" if triggers else "无需再平衡",
    }


def check_style_drift(claimed_style: str, actual_allocation: dict) -> dict:
    """风格漂移检测：持仓与宣称风格不一致。"""
    max_industry = max(actual_allocation.values()) if actual_allocation else 0
    max_name = max(actual_allocation, key=actual_allocation.get) if actual_allocation else ""
    is_drift = max_industry > STYLE_DRIFT_THRESHOLD

    # 风格匹配判断
    style_patterns = {
        "价值": ["银行", "保险", "地产", "煤炭", "钢铁"],
        "成长": ["科技", "半导体", "新能源", "医药", "AI"],
        "消费": ["白酒", "食品", "家电", "汽车"],
        "均衡": [],  # 均衡风格无特定行业偏好
    }

    return {
        "claimed_style": claimed_style,
        "max_industry": max_name,
        "max_industry_pct": max_industry,
        "is_drift": is_drift,
        "drift_level": "严重漂移" if max_industry > 70 else ("轻度漂移" if is_drift else "风格一致"),
        "advice": (
            f"单一行业 {max_name} 占比 {max_industry}%，与{claimed_style}风格不符，建议调整"
            if is_drift
            else f"持仓风格与{claimed_style}一致，无需调整"
        ),
    }


def generate_rebalance_actions(target: dict, actual: dict) -> dict:
    """生成再平衡操作建议。"""
    actions = []
    for asset in target:
        t = target.get(asset, 0)
        a = actual.get(asset, 0)
        diff = t - a
        if abs(diff) > 0.02:  # 忽略 <2% 的微小偏差
            actions.append({
                "asset": asset,
                "target_pct": f"{t:.0%}",
                "actual_pct": f"{a:.0%}",
                "diff": round(diff, 4),
                "action": f"{'买入' if diff > 0 else '卖出'} {abs(diff):.0%}",
            })

    return {
        "actions": actions,
        "total_changes": len(actions),
        "summary": f"需执行 {len(actions)} 项再平衡操作" if actions else "组合已处于目标配置",
    }


def main():
    parser = argparse.ArgumentParser(description="再平衡自动化工具 — 阈值触发/风格漂移/操作生成")
    sub = parser.add_subparsers(dest="command")

    # 阈值触发检测
    tt = sub.add_parser("check-threshold", help="阈值触发检测")
    tt.add_argument("--target", required=True, help="目标配置 JSON")
    tt.add_argument("--actual", required=True, help="实际配置 JSON")

    # 风格漂移检测
    sd = sub.add_parser("check-style-drift", help="风格漂移检测")
    sd.add_argument("--claimed", required=True, help="宣称风格")
    sd.add_argument("--actual", required=True, help="实际行业配置 JSON")

    # 再平衡操作生成
    ga = sub.add_parser("generate-actions", help="生成再平衡操作")
    ga.add_argument("--target", required=True)
    ga.add_argument("--actual", required=True)

    args = parser.parse_args()

    if args.command == "check-threshold":
        target = json.loads(args.target)
        actual = json.loads(args.actual)
        result = check_threshold(target, actual)
    elif args.command == "check-style-drift":
        actual = json.loads(args.actual)
        result = check_style_drift(args.claimed, actual)
    elif args.command == "generate-actions":
        target = json.loads(args.target)
        actual = json.loads(args.actual)
        result = generate_rebalance_actions(target, actual)
    else:
        parser.print_help()
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
