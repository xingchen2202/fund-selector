#!/usr/bin/env python3
"""
calc_var_impact.py — 计算加入新基金后的组合 VaR 变化
━━━━━━━━━━━━━━━━━━━━
简化 VaR 计算：假设基金年化波动率 15%，与现有组合相关性 0.5。
"""
import json
import math


def calc_marginal_var(
    new_fund_value: float,
    existing_value: float,
    existing_var: float,
    new_fund_vol: float = 0.15,
    correlation: float = 0.5,
) -> dict:
    """计算加入新基金后的边际 VaR"""
    new_fund_var = new_fund_value * new_fund_vol / math.sqrt(12)
    combined_value = existing_value + new_fund_value
    combined_var = math.sqrt(
        existing_var**2 + new_fund_var**2 + 2 * correlation * existing_var * new_fund_var
    )
    marginal_var = combined_var - existing_var
    return {
        "new_fund_var": round(new_fund_var, 2),
        "combined_var": round(combined_var, 2),
        "marginal_var": round(marginal_var, 2),
        "exceeds_budget": marginal_var > 2000,
    }


def main():
    import sys
    if len(sys.argv) < 3:
        print(json.dumps({"error": "用法: calc_var_impact.py <new_fund_value> <existing_var>"}))
        sys.exit(1)

    new_value = float(sys.argv[1])
    existing_var = float(sys.argv[2])
    result = calc_marginal_var(new_value, 0, existing_var)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
