#!/usr/bin/env python3
"""A 股数据工具（Ashare Data）— 实时行情/财务/估值
━━━━━━━━━━━━━━━━━━━━
封装 cn-financial MCP 调用，提供 CLI 接口。

注意：此工具通过 MCP 获取数据，需要 Claude 调用 MCP 工具。
当前脚本生成 MCP 调用指令，由 Claude 执行。

用法：
    python tools/ashare_data.py quote --code 000001
    python tools/ashare_data.py financials --code 000001
    python tools/ashare_data.py valuation --code 000001
    python tools/ashare_data.py search --keyword 银行
"""

import argparse
import json
import sys


def make_mcp_call(tool: str, params: dict) -> str:
    """生成 MCP 调用指令（供 Claude 执行）。"""
    args_str = ", ".join(f'{k}={json.dumps(v, ensure_ascii=False)}' for k, v in params.items())
    return f"mcp__cn-financial__{tool}({args_str})"


def main():
    parser = argparse.ArgumentParser(description="A 股数据工具 — 生成 MCP 调用指令")
    sub = parser.add_subparsers(dest="command")

    qt = sub.add_parser("quote", help="实时行情")
    qt.add_argument("--code", required=True)

    fn = sub.add_parser("financials", help="财务报表")
    fn.add_argument("--code", required=True)

    vl = sub.add_parser("valuation", help="估值指标")
    vl.add_argument("--code", required=True)

    sr = sub.add_parser("search", help="股票搜索")
    sr.add_argument("--keyword", required=True)

    args = parser.parse_args()

    calls = {
        "quote": ("get_realtime_quote", {"symbol": args.code}),
        "financials": ("get_financial_indicators", {"symbol": args.code}),
        "valuation": ("get_valuation_metrics", {"symbol": args.code, "num_periods": 60}),
        "search": ("search_stock", {"keyword": args.keyword}),
    }

    if args.command in calls:
        tool, params = calls[args.command]
        call_str = make_mcp_call(tool, params)
        print(f"请执行以下 MCP 调用获取数据：\n")
        print(f"  {call_str}\n")
        print(f"返回结果后，使用 financial_rigor.py 做交叉验证。")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
