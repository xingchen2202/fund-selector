#!/usr/bin/env python3
"""数据验证工具（Data Validator）— 双源交叉验证
━━━━━━━━━━━━━━━━━━━━
确保关键数据点至少有两个独立来源。

用法：
    python tools/data_validator.py validate --field 规模 --primary 4.42 --secondary 4.38 --tolerance 0.01
    python tools/data_validator.py batch --data '{"规模": {"primary": 4.42, "secondary": 4.38}, ...}'
"""

import argparse
import json
import sys


def validate_single(field: str, primary: float, secondary: float, tolerance: float = 0.01) -> dict:
    """验证单一数据点的双源一致性。"""
    if primary == 0 and secondary == 0:
        return {"field": field, "status": "无法验证", "deviation": 0}

    deviation = abs(primary - secondary) / max(abs(primary), abs(secondary), 1e-10)
    consistent = deviation <= tolerance

    return {
        "field": field,
        "primary": primary,
        "secondary": secondary,
        "deviation": round(deviation * 100, 2),
        "tolerance": tolerance * 100,
        "status": "✅ 一致" if consistent else "❌ 不一致",
        "consistent": consistent,
    }


def batch_validate(data: dict, tolerance: float = 0.01) -> dict:
    """批量验证多个数据点。"""
    results = []
    for field, sources in data.items():
        primary = sources.get("primary", sources.get("mcp", 0))
        secondary = sources.get("secondary", sources.get("excel", 0))
        r = validate_single(field, primary, secondary, tolerance)
        results.append(r)

    consistent_count = sum(1 for r in results if r.get("consistent"))
    total = len(results)

    return {
        "results": results,
        "summary": {
            "total": total,
            "consistent": consistent_count,
            "inconsistent": total - consistent_count,
            "pass_rate": round(consistent_count / total * 100, 1) if total else 0,
        },
        "verdict": "通过" if consistent_count == total else "有条件通过" if consistent_count >= total * 0.8 else "不通过",
    }


def main():
    parser = argparse.ArgumentParser(description="数据验证工具 — 双源交叉验证")
    sub = parser.add_subparsers(dest="command")

    vs = sub.add_parser("validate", help="验证单一数据点")
    vs.add_argument("--field", required=True)
    vs.add_argument("--primary", type=float, required=True)
    vs.add_argument("--secondary", type=float, required=True)
    vs.add_argument("--tolerance", type=float, default=0.01)

    ba = sub.add_parser("batch", help="批量验证")
    ba.add_argument("--data", required=True)
    ba.add_argument("--tolerance", type=float, default=0.01)

    args = parser.parse_args()

    if args.command == "validate":
        r = validate_single(args.field, args.primary, args.secondary, args.tolerance)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.command == "batch":
        r = batch_validate(json.loads(args.data), args.tolerance)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
