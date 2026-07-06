#!/usr/bin/env python3
"""报告审计工具（Report Audit）— 15% 随机抽样验证
━━━━━━━━━━━━━━━━━━━━
移植自 ai-berkshire report_audit.py。

用法：
    python tools/report_audit.py extract --report <报告.md> [--sample-rate 0.15]
    python tools/report_audit.py verdict --results '<JSON抽样结果>'
"""

import argparse
import json
import random
import re
import sys
import io

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from pathlib import Path


def extract_data_points(report_path: str, sample_rate: float = 0.15) -> dict:
    """从报告中提取可验证的数据点，随机抽样。"""
    text = Path(report_path).read_text(encoding="utf-8")

    # 提取模式：数字 + 单位（亿/万/%/元/倍/年）
    patterns = [
        (r'(\d+\.?\d*)\s*亿', '亿元'),
        (r'(\d+\.?\d*)\s*万', '万元'),
        (r'(\d+\.?\d*)\s*%', '百分比'),
        (r'(\d+\.?\d*)\s*倍', '倍'),
        (r'(\d+\.?\d*)年', '年'),
        (r'PE[（(]TTM[）)]\s*[:：]?\s*(\d+\.?\d*)', 'PE'),
        (r'PB\s*[:：]?\s*(\d+\.?\d*)', 'PB'),
    ]

    data_points = []
    for pat, unit in patterns:
        for m in re.finditer(pat, text):
            val = m.group(1)
            # 取上下文（前后 30 字）
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            context = text[start:end].replace('\n', ' ')
            data_points.append({
                "value": val,
                "unit": unit,
                "context": context,
                "position": m.start(),
            })

    # 随机抽样
    n_sample = max(1, int(len(data_points) * sample_rate))
    sampled = random.sample(data_points, min(n_sample, len(data_points)))

    return {
        "total_points": len(data_points),
        "sampled_count": len(sampled),
        "sample_rate": sample_rate,
        "samples": sampled,
        "instruction": f"请验证以下 {len(sampled)} 个数据点（抽样率 {sample_rate:.0%}），"
                       f"标注每个数据点的来源和准确性。",
    }


def audit_verdict(results_json: str) -> dict:
    """根据验证结果输出审计结论。"""
    try:
        results = json.loads(results_json)
    except Exception:
        results = []

    total = len(results)
    if total == 0:
        return {"verdict": "无法审计", "pass_rate": 0, "passed": 0, "failed": 0}

    passed = sum(1 for r in results if r.get("verified") is True)
    failed = total - passed
    pass_rate = passed / total * 100

    verdict = "通过" if pass_rate >= 90 else "有条件通过" if pass_rate >= 75 else "不通过"

    return {
        "verdict": verdict,
        "pass_rate": round(pass_rate, 1),
        "passed": passed,
        "failed": failed,
        "total": total,
        "failed_items": [r for r in results if r.get("verified") is not True],
    }


def main():
    parser = argparse.ArgumentParser(description="报告审计工具 — 15% 随机抽样验证")
    sub = parser.add_subparsers(dest="command")

    ex = sub.add_parser("extract", help="从报告提取数据点并抽样")
    ex.add_argument("--report", required=True)
    ex.add_argument("--sample-rate", type=float, default=0.15)

    ve = sub.add_parser("verdict", help="根据验证结果输出审计结论")
    ve.add_argument("--results", required=True)

    args = parser.parse_args()

    if args.command == "extract":
        result = extract_data_points(args.report, args.sample_rate)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "verdict":
        result = audit_verdict(args.results)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
