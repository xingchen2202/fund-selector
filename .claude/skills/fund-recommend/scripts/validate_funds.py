#!/usr/bin/env python3
"""
validate_funds.py — 验证候选基金基本面
━━━━━━━━━━━━━━━━━━━━
对每只候选基金调用 cn-mutual-fund MCP 获取详细信息。
实际执行时由 Claude 直接调用 MCP 工具。
"""
import json
import sys


def main():
    """
    实际执行时，Claude 会对每只候选基金调用：
    - get_fund_info(fund_code) → 规模、经理、费率
    - get_fund_nav_history(fund_code, period="3y") → 净值序列
    - get_fund_portfolio(fund_code) → 前十大持仓

    此脚本输出验证模板。
    """
    template = {
        "candidates": [],
        "verified": [],
        "failed": [],
    }
    print(json.dumps(template, ensure_ascii=False, indent=2))
    print("\n[提示] 此脚本为模板。实际执行时，请由 Claude 直接调用 MCP 工具验证。")


if __name__ == "__main__":
    main()
