#!/usr/bin/env python3
"""
perilla_analysis.py — 紫苏叶视角的持仓穿透分析
━━━━━━━━━━━━━━━━━━━━
对候选基金的前十大持仓股，检查是否符合"瓶颈节点"标准。
实际执行时由 Claude 直接调用 cn-financial MCP 工具。
"""
import json
import sys


def main():
    """
    实际执行时，Claude 会对每只持仓股调用：
    - get_financial_indicators(stock_code) → ROE、毛利率

    紫苏叶标准（来自 ../_shared/perilla-framework.md）：
    - 市值 50-300 亿
    - 毛利率 > 30%
    - 机构持仓比例 < 10%
    - 细分领域市占率前三

    符合 3 条以上 → 标注为"潜在瓶颈节点"

    注意：持仓数据来自基金季报，滞后一个季度。
    """
    template = {
        "fund_holdings_analysis": [],
        "data_lag_note": "持仓数据来自基金季报，滞后一个季度",
    }
    print(json.dumps(template, ensure_ascii=False, indent=2))
    print("\n[提示] 此脚本为模板。实际执行时，请由 Claude 直接调用 MCP 工具。")


if __name__ == "__main__":
    main()
