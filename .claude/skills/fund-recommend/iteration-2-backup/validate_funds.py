#!/usr/bin/env python3
"""
validate_funds.py — 验证候选基金基本面，写入 pipeline
━━━━━━━━━━━━━━━━━━━━
读取 _pipeline_data.json 中的 candidates，
调用 AKShare 获取规模/基本信息/成立日期，
计算成立年限，不满3年标注"成立以来（X年X月）"，
写入 _pipeline_data.json["validated_funds"]。

注意：净值历史、经理等数据由 Claude 通过 cn-mutual-fund MCP 获取，
本脚本只负责 AKShare 可可靠获取的规模和成立日期数据。
"""
import json
import sys
import io
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
REPORTS_DIR = PROJECT_ROOT / "fund-reports"


def read_candidates():
    """从 step2 文件读取候选列表"""
    try:
        script_dir = Path(__file__).parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from pipeline import read_step
        data = read_step("step2")
        return data.get("top10", [])
    except Exception:
        return []


def write_validated_funds(data):
    """写入 step3 文件"""
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from pipeline import write_step
    write_step("step3", {"validated_funds": data})


def get_fund_info_basic(fund_code):
    """
    通过 AKShare 获取基金基本信息。
    返回 dict：{name, scale_wan, establishment_date}
    """
    try:
        import akshare as ak
        df = ak.fund_individual_basic_info_xq(symbol=fund_code)
        if df is not None and not df.empty:
            result = {"name": None, "scale_wan": None, "establishment_date": None}
            # 名称
            name_row = df[df["item"] == "基金简称"]
            if not name_row.empty:
                result["name"] = str(name_row["value"].values[0]).strip()
            # 规模
            scale_row = df[df["item"] == "最新规模"]
            if not scale_row.empty:
                scale_str = str(scale_row["value"].values[0])
                if "万" in scale_str:
                    result["scale_wan"] = float(scale_str.replace("万", "").replace("亿", ""))
                elif "亿" in scale_str:
                    result["scale_wan"] = float(scale_str.replace("亿", "")) * 10000
            # 成立时间
            date_row = df[df["item"] == "成立时间"]
            if not date_row.empty:
                result["establishment_date"] = str(date_row["value"].values[0]).strip()[:10]
            return result
    except Exception as e:
        print(f"[WARN] AKShare获取{fund_code}基本信息失败: {e}", file=sys.stderr)
    return {"name": None, "scale_wan": None, "establishment_date": None}


def get_return_label(inception_date_str, return_value, period_years):
    """
    根据基金成立时间决定收益标签。

    Args:
        inception_date_str: 成立日期字符串 (ISO格式 "2024-01-12")
        return_value: 收益数值或None
        period_years: 想标注的期限（如3表示"近3年"）

    Returns:
        (label, value) 标签和数值元组
        不满3年时 label = "成立以来（Y年M月）"
        满3年时 label = "近N年"
    """
    if not inception_date_str:
        return f"近{period_years}年", return_value

    try:
        from datetime import datetime, date

        inception_date = datetime.strptime(inception_date_str[:10], "%Y-%m-%d").date()
        today = date.today()
        months = (today.year - inception_date.year) * 12 + (today.month - inception_date.month)
        years = months // 12
        remaining_months = months % 12

        if years < period_years:
            label = f"成立以来（{years}年{remaining_months}月）"
        else:
            label = f"近{period_years}年"
        return label, return_value
    except Exception:
        return f"近{period_years}年", return_value


def fetch_fund_basic(fund_code, candidate_name, candidate_sector, candidate_score):
    """
    通过 AKShare 获取基金基本信息，并生成正确的收益标签。
    返回 dict 包含规模、名称、成立日期、收益标签。
    """
    result = {
        "code": fund_code,
        "name": candidate_name,
        "scale_wan": None,
        "sector": candidate_sector,
        "score": candidate_score,
        # 以下字段由 Claude 通过 MCP 填充
        "manager": None,
        "fee": None,
        "return_1y": None,
        "return_1y_label": "近1年",
        "return_3y": None,
        "return_3y_label": "近3年",
        "max_drawdown": None,
        "sharpe": None,
        "top_holdings": [],
        # P4修复：成立日期和年龄
        "establishment_date": None,
        "age_years": None,
        "age_months": None,
    }

    # 获取 AKShare 基本信息
    info = get_fund_info_basic(fund_code)

    # 填充名称
    if info.get("name"):
        result["name"] = info["name"]

    # 填充规模
    if info.get("scale_wan") is not None:
        result["scale_wan"] = info["scale_wan"]

    # P4修复：填充成立日期，计算年龄，生成收益标签
    est_date_str = info.get("establishment_date")
    if est_date_str:
        result["establishment_date"] = est_date_str
        try:
            from datetime import datetime, date

            est_date = datetime.strptime(est_date_str[:10], "%Y-%m-%d").date()
            today = date.today()
            total_months = (today.year - est_date.year) * 12 + (today.month - est_date.month)
            years = total_months // 12
            remaining_months = total_months % 12
            result["age_years"] = years
            result["age_months"] = remaining_months

            # 生成收益标签
            result["return_1y_label"], _ = get_return_label(est_date_str, None, 1)
            result["return_3y_label"], _ = get_return_label(est_date_str, None, 3)
        except Exception as e:
            print(f"[WARN] 解析成立日期失败 {fund_code}: {e}", file=sys.stderr)

    return result


def main():
    # 从 step2 读取 candidates
    candidates = read_candidates()

    if not candidates:
        print(json.dumps({"error": "pipeline 中无 candidates 字段"}))
        print("[提示] 请先运行 screen_candidates.py 生成候选列表", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] 开始验证 {len(candidates)} 只候选基金...", file=sys.stderr)

    validated = []
    for c in candidates:
        code = c.get("code", "")
        name = c.get("name", "")
        sector = c.get("sector", "未知")
        score = c.get("score")

        print(f"[INFO] 验证 {code} {name}...", file=sys.stderr)
        detail = fetch_fund_basic(code, name, sector, score)
        validated.append(detail)

        scale_str = f"{detail['scale_wan']}万" if detail['scale_wan'] else "未知"
        age_str = f"成立{detail['age_years']}年{detail['age_months']}月" if detail['age_years'] is not None else ""
        print(f"[OK] {code} 规模={scale_str} {age_str}", file=sys.stderr)

    result = {
        "candidates": [c.get("code") for c in candidates],
        "verified": validated,
        "failed": [],
        "total": len(validated),
    }

    # 写入 step3
    write_validated_funds(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[INFO] 已写入 pipeline['validated_funds'] ({len(validated)} 只基金)", file=sys.stderr)


if __name__ == "__main__":
    main()
