#!/usr/bin/env python3
"""
screen_candidates.py — 从 Excel 候选池筛选基金
━━━━━━━━━━━━━━━━━━━━
读取 fund_screening_corrected_20260624.xlsx，按条件过滤。
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
EXCEL_PATH = PROJECT_ROOT / "fund_screening_corrected_20260624.xlsx"

# 板块映射（代码 → 板块）
SECTOR_MAP = {
    "004597": "银行", "013477": "科技成长", "008702": "黄金",
    "022015": "债券固收", "017437": "美股QDII", "024725": "科技成长",
    "008888": "科技成长", "025720": "港股", "005164": "均衡",
    "023729": "科技成长", "000216": "黄金", "009033": "黄金",
    "013279": "均衡", "004503": "债券固收", "012349": "港股",
}


def load_hold_codes():
    portfolio_path = PROJECT_ROOT / "portfolio.json"
    if not portfolio_path.exists():
        return []
    with open(portfolio_path, "r", encoding="utf-8") as f:
        portfolio = json.load(f)
    return [h["code"] for h in portfolio.get("funds", [])]


def main():
    import pandas as pd

    if not EXCEL_PATH.exists():
        print(json.dumps({"error": f"候选池文件不存在: {EXCEL_PATH}"}))
        sys.exit(1)

    # 读取所有 Sheet，过滤含"防守"或"稳健"的
    import openpyxl
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True)
    sheets = []
    for name in wb.sheetnames:
        if "防守" in name or "稳健" in name:
            try:
                df = pd.read_excel(EXCEL_PATH, sheet_name=name)
                df["_sheet"] = name
                sheets.append(df)
            except Exception:
                pass
    wb.close()

    if not sheets:
        print(json.dumps({"error": "无法读取任何 Sheet"}))
        sys.exit(1)

    candidates = pd.concat(sheets, ignore_index=True)
    total_before = len(candidates)

    # 排除已持有
    hold_codes = load_hold_codes()
    candidates = candidates[~candidates.iloc[:, 0].astype(str).str.zfill(6).isin(hold_codes)]

    # 排除规模 < 2 亿
    if "规模（亿元）" in candidates.columns:
        candidates = candidates[candidates["规模（亿元）"] >= 2]

    # 综合得分排序（如果存在）
    score_cols = [c for c in candidates.columns if "综合" in str(c) or "得分" in str(c) or "评分" in str(c)]
    if score_cols:
        candidates = candidates.sort_values(score_cols[0], ascending=False)

    # 取前 10
    top = candidates.head(10)
    result = {
        "total_before_filter": total_before,
        "total_after_filter": len(candidates),
        "top10": [],
    }

    for _, row in top.iterrows():
        code = str(row["基金代码"]).zfill(6) if "基金代码" in row.index else str(row.iloc[1]).zfill(6)
        name = str(row["基金简称"]) if "基金简称" in row.index else str(row.iloc[2])
        sector = SECTOR_MAP.get(code, "未知")
        score = float(row["综合得分"]) if "综合得分" in row.index else None
        result["top10"].append({
            "code": code,
            "name": name,
            "sector": sector,
            "score": score,
            "sheet": row.get("_sheet", ""),
        })

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
