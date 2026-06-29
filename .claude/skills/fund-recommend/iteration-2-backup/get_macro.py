#!/usr/bin/env python3
"""
get_macro.py — 获取宏观经济数据并判断经济周期
━━━━━━━━━━━━━━━━━━━━
独立调用 cn-financial MCP 工具，输出结构化判断结果。
此脚本通过 subprocess 调用 MCP，实际使用时由 Claude 直接调用 MCP 工具。
"""
import json
import sys


def main():
    """
    实际执行时，Claude 会直接调用以下 MCP 工具：
    - get_macro_pmi()
    - get_macro_money_supply()
    - get_valuation_metrics(symbol="000300", num_periods=60)
    - get_north_bound_flow()

    此脚本输出期望的数据结构模板，供 Claude 填充。
    """
    template = {
        "pmi": {"available": None, "manufacturing": None, "non_manufacturing": None, "trend": None},
        "money_supply": {"available": None, "m2_yoy": None, "m1_yoy": None},
        "valuation": {"available": None, "hs300_pe": None, "hs300_pe_percentile": None},
        "north_bound": {"available": None, "recent_flow": None},
        "cycle_judgment": {"phase": None, "confidence": None, "direction": None},
        "unavailable": [],
    }
    print(json.dumps(template, ensure_ascii=False, indent=2))
    print("\n[提示] 此脚本为模板。实际执行时，请由 Claude 直接调用 MCP 工具填充数据。")
    print("填充后，Claude 应将 macro 数据写入 _pipeline_data.json['macro']")


if __name__ == "__main__":
    main()
