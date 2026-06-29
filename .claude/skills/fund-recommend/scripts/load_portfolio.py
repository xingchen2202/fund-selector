#!/usr/bin/env python3
"""
load_portfolio.py — 读取现有组合，计算约束条件
━━━━━━━━━━━━━━━━━━━━
读取 portfolio.json，计算各板块占比、超配板块、VaR 预算。
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
PORTFOLIO_PATH = PROJECT_ROOT / "portfolio.json"
EXCEL_PATH = PROJECT_ROOT / "fund_screening_corrected_20260624.xlsx"

SECTOR_MAP = {
    "004597": "银行", "013477": "科技成长", "008702": "黄金",
    "022015": "债券固收", "017437": "美股QDII", "024725": "科技成长",
    "008888": "科技成长", "025720": "港股", "005164": "均衡",
    "023729": "科技成长", "000216": "黄金", "009033": "黄金",
    "013279": "均衡", "004503": "债券固收", "012349": "港股",
}


def load_portfolio():
    if not PORTFOLIO_PATH.exists():
        print(json.dumps({"error": "portfolio.json不存在", "path": str(PORTFOLIO_PATH)}))
        sys.exit(1)
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def calc_sector_allocation(holdings):
    """计算各板块占比"""
    total = sum(h.get("cost_value", 0) for h in holdings)
    if total == 0:
        return {}, 0

    sector_values = {}
    for h in holdings:
        sector = SECTOR_MAP.get(h["code"], "其他")
        sector_values[sector] = sector_values.get(sector, 0) + h.get("cost_value", 0)

    allocation = {s: round(v / total * 100, 2) for s, v in sector_values.items()}
    return allocation, total


def calc_var_estimate(holdings):
    """简化 VaR 估算（假设组合年化波动率 15%）"""
    total = sum(h.get("cost_value", 0) for h in holdings)
    annual_var = total * 0.15
    monthly_var = annual_var / (12 ** 0.5)
    return round(monthly_var)


def main():
    portfolio = load_portfolio()
    holdings = portfolio.get("funds", [])

    allocation, total = calc_sector_allocation(holdings)
    overloaded = {s: p for s, p in allocation.items() if p > 25}
    monthly_var = calc_var_estimate(holdings)
    var_budget = max(0, 2000 - monthly_var)

    result = {
        "total_value": round(total, 2),
        "sector_allocation": allocation,
        "overloaded_sectors": overloaded,
        "monthly_var_estimate": monthly_var,
        "var_budget_remaining": var_budget,
        "fund_count": len(holdings),
        "fund_codes": [h["code"] for h in holdings],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # P3修复：写入 pipeline
    try:
        pipeline_path = PROJECT_ROOT / "fund-reports" / "_pipeline_data.json"
        pipeline = {}
        if pipeline_path.exists():
            with open(pipeline_path, "r", encoding="utf-8") as f:
                pipeline = json.load(f)
        pipeline["constraints"] = result
        with open(pipeline_path, "w", encoding="utf-8") as f:
            json.dump(pipeline, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 已写入 pipeline['constraints']", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] 写入 pipeline 失败: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
