#!/usr/bin/env python3
"""
screen_candidates.py — 从 Excel 候选池筛选基金
━━━━━━━━━━━━━━━━━━━━
读取 fund_screening_corrected_20260624.xlsx，按条件过滤。
修复P1：增加实时规模验证，排除规模<2亿的基金。
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
EXCEL_PATH = PROJECT_ROOT / "fund_screening_corrected_20260624.xlsx"

# 规模阈值：2亿 = 20000万元
SCALE_THRESHOLD_WAN = 20000

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


def get_fund_scale_wan(fund_code):
    """通过 AKShare 获取基金规模（万元），失败返回 None"""
    try:
        import akshare as ak
        df = ak.fund_individual_basic_info_xq(symbol=fund_code)
        if df is not None and not df.empty:
            # 返回格式是 item/value 两列
            scale_row = df[df["item"] == "最新规模"]
            if not scale_row.empty:
                scale_str = str(scale_row["value"].values[0])
                # 解析 "44.81万" → 44.81, "2.5亿" → 25000
                if "万" in scale_str:
                    num = float(scale_str.replace("万", "").replace("亿", ""))
                    return num  # 返回万元
                elif "亿" in scale_str:
                    num = float(scale_str.replace("亿", ""))
                    return num * 10000  # 亿转万
    except Exception as e:
        print(f"[WARN] AKShare获取{fund_code}规模失败: {e}", file=sys.stderr)
    return None


def validate_scale(candidates_list):
    """
    P1修复：实时规模验证
    对每只候选基金调用AKShare获取实际规模，低于2亿的排除。
    返回 (通过列表, 排除列表)。
    """
    validated = []
    excluded = []

    for fund in candidates_list:
        code = fund["code"]
        scale_wan = get_fund_scale_wan(code)

        if scale_wan is None:
            # 无法获取规模，标注但保留（避免误排除）
            fund["scale_note"] = "规模数据不可用，需人工核实"
            validated.append(fund)
            print(f"[WARN] {code} 规模数据不可用，保留待人工核实", file=sys.stderr)
        elif scale_wan < SCALE_THRESHOLD_WAN:
            # 规模不足，排除
            reason = f"规模{scale_wan}万 < {SCALE_THRESHOLD_WAN}万（2亿）阈值"
            excluded.append({
                "code": code,
                "name": fund.get("name", ""),
                "scale_wan": scale_wan,
                "reason": reason,
            })
            print(f"[EXCLUDE] {code} {fund.get('name', '')} {reason}", file=sys.stderr)
        else:
            fund["actual_scale_wan"] = scale_wan
            validated.append(fund)

    if excluded:
        print(f"[INFO] 因规模不足被排除: {len(excluded)}只", file=sys.stderr)
        for e in excluded:
            print(f"  - {e['code']} {e['name']}: {e['reason']}", file=sys.stderr)

    return validated, excluded


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

    # P1修复：Excel无规模列，此处不再依赖Excel筛选
    # 原代码: if "规模（亿元）" in candidates.columns: ...  ← 已删除

    # 综合得分排序（如果存在）
    score_cols = [c for c in candidates.columns if "综合" in str(c) or "得分" in str(c) or "评分" in str(c)]
    if score_cols:
        candidates = candidates.sort_values(score_cols[0], ascending=False)

    # 取前15（预留空间给规模排除）
    top_n = candidates.head(15)

    # 转为 dict 列表供 validate_scale 处理
    top_list = []
    for _, row in top_n.iterrows():
        code = str(row["基金代码"]).zfill(6) if "基金代码" in row.index else str(row.iloc[1]).zfill(6)
        name = str(row["基金简称"]) if "基金简称" in row.index else str(row.iloc[2])
        sector = SECTOR_MAP.get(code, "未知")
        score = float(row["综合得分"]) if "综合得分" in row.index else None
        top_list.append({
            "code": code,
            "name": name,
            "sector": sector,
            "score": score,
            "sheet": row.get("_sheet", ""),
        })

    # P1修复：实时规模验证
    print("[INFO] 开始实时规模验证（AKShare）...", file=sys.stderr)
    validated, excluded = validate_scale(top_list)

    # 取最终前10
    final_top = validated[:10]

    result = {
        "total_before_filter": total_before,
        "total_after_basic_filter": len(candidates),
        "scale_excluded_count": len(excluded),
        "scale_excluded": excluded,
        "final_candidates": len(final_top),
        "top10": final_top,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    # P3修复：写入 pipeline
    try:
        pipeline_path = PROJECT_ROOT / "fund-reports" / "_pipeline_data.json"
        pipeline = {}
        if pipeline_path.exists():
            with open(pipeline_path, "r", encoding="utf-8") as f:
                pipeline = json.load(f)
        pipeline["candidates"] = final_top
        with open(pipeline_path, "w", encoding="utf-8") as f:
            json.dump(pipeline, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 已写入 pipeline['candidates'] ({len(final_top)} 只)", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] 写入 pipeline 失败: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
