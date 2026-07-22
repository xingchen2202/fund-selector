#!/usr/bin/env python3
"""持仓相关性检查工具（Correlation Checker）— 量化基金分散度
━━━━━━━━━━━━━━━━━━━━
检查两只基金的前十大重仓股重叠度，识别"伪分散"。

零外部依赖 — 仅 Python stdlib (json, argparse)。

用法：
    python tools/correlation_checker.py check-overlap --holdings1 茅台 五粮液 宁德 --holdings2 茅台 五粮液 宁德 腾讯
    python tools/correlation_checker.py batch-check --funds '[["茅台","五粮液"],["茅台","五粮液","宁德"]]'
"""

import argparse
import json
import sys
import io

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 重叠警告阈值（≥3 只相同 → 警告）
OVERLAP_WARNING_THRESHOLD = 3


def check_holdings_overlap(holdings1: list, holdings2: list) -> dict:
    """计算两只基金重仓股重叠度。

    Args:
        holdings1: 基金1 持仓列表
        holdings2: 基金2 持仓列表

    Returns:
        dict: 重叠数量、重叠股票、重叠率、是否警告
    """
    set1, set2 = set(holdings1), set(holdings2)
    common = set1 & set2
    min_len = min(len(set1), len(set2)) if set1 and set2 else 1
    overlap_rate = len(common) / min_len

    return {
        "fund1_count": len(set1),
        "fund2_count": len(set2),
        "common_count": len(common),
        "common_stocks": sorted(list(common)),
        "overlap_rate": round(overlap_rate, 4),
        "warning": len(common) >= OVERLAP_WARNING_THRESHOLD,
        "message": (
            f"重仓股重叠 {len(common)} 只（{', '.join(sorted(list(common)[:5]))}），分散效果有限"
            if len(common) >= OVERLAP_WARNING_THRESHOLD
            else f"重仓股重叠 {len(common)} 只，分散度良好"
        ),
    }


def batch_check(funds_holdings: list) -> list:
    """批量检查多只基金的两两重叠度。

    Args:
        funds_holdings: 多只基金的持仓列表，如 [["茅台","五粮液"], ["茅台","宁德"]]

    Returns:
        list: 两两检查结果
    """
    results = []
    for i in range(len(funds_holdings)):
        for j in range(i + 1, len(funds_holdings)):
            r = check_holdings_overlap(funds_holdings[i], funds_holdings[j])
            r["fund1_index"] = i
            r["fund2_index"] = j
            results.append(r)
    return results


def main():
    parser = argparse.ArgumentParser(description="持仓相关性检查工具 — 量化基金分散度")
    sub = parser.add_subparsers(dest="command")

    # 子命令 1: 检查两只基金重叠
    chk = sub.add_parser("check-overlap", help="检查两只基金重仓股重叠度")
    chk.add_argument("--holdings1", nargs="+", required=True, help="基金1 持仓列表")
    chk.add_argument("--holdings2", nargs="+", required=True, help="基金2 持仓列表")

    # 子命令 2: 批量检查
    bat = sub.add_parser("batch-check", help="批量检查多只基金两两重叠度")
    bat.add_argument("--funds", required=True, help="JSON 格式的持仓列表")

    args = parser.parse_args()

    if args.command == "check-overlap":
        result = check_holdings_overlap(args.holdings1, args.holdings2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "batch-check":
        funds = json.loads(args.funds)
        results = batch_check(funds)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
