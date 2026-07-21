#!/usr/bin/env python3
"""
validate_funds.py — 读取 Claude MCP 数据，补充 AKShare 验证
━━━━━━━━━━━━━━━━━━━━
P5修复：降级为纯补充工具。
实际 MCP 调用（get_fund_info, get_fund_nav_history 等）由 Claude 执行。
此脚本读取 _pipeline_step3_funds.json，可选补充 AKShare 规模数据，
写入 _pipeline_step3_akshare.json。
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

FUNDS_FILE = REPORTS_DIR / "_pipeline_step3_funds.json"
OUTPUT_FILE = REPORTS_DIR / "_pipeline_step3_akshare.json"


def read_funds_data():
    """从 step3 文件读取 Claude MCP 写入的基金数据"""
    if not FUNDS_FILE.exists():
        print("[WARN] 基金数据文件不存在: {}".format(FUNDS_FILE), file=sys.stderr)
        print("[提示] 请先由 Claude 调用 MCP 工具并写入 _pipeline_step3_funds.json", file=sys.stderr)
        return None
    with open(FUNDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_fund_scale_wan(fund_code):
    """通过 AKShare 获取基金规模（万元），失败返回 None"""
    try:
        import akshare as ak
        df = ak.fund_individual_basic_info_xq(symbol=fund_code)
        if df is not None and not df.empty:
            scale_row = df[df["item"] == "最新规模"]
            if not scale_row.empty:
                scale_str = str(scale_row["value"].values[0])
                if "万" in scale_str:
                    return float(scale_str.replace("万", "").replace("亿", ""))
                elif "亿" in scale_str:
                    return float(scale_str.replace("亿", "")) * 10000
    except Exception as e:
        print("[WARN] AKShare获取{fund_code}规模失败: {e}".format(
            fund_code=fund_code, e=e
        ), file=sys.stderr)
    return None


def get_return_label(inception_date_str, return_value, period_years):
    """
    根据基金成立时间决定收益标签。
    不满3年标注"成立以来（Y年X月）"。
    """
    if not inception_date_str:
        return "近{}年".format(period_years), return_value

    try:
        from datetime import datetime, date
        inception = datetime.strptime(inception_date_str[:10], "%Y-%m-%d").date()
        today = date.today()
        months = (today.year - inception.year) * 12 + (today.month - inception.month)
        years = months // 12
        remaining = months % 12

        if years < period_years:
            return "成立以来（{}年{}月）".format(years, remaining), return_value
        return "近{}年".format(period_years), return_value
    except Exception:
        return "近{}年".format(period_years), return_value


def main():
    data = read_funds_data()
    if data is None:
        print(json.dumps({"error": "step3 文件不存在，请先运行 Claude MCP 调用"}))
        sys.exit(1)

    verified = data.get("verified", [])
    print("[INFO] 读取到 {} 只基金的 MCP 数据".format(len(verified)), file=sys.stderr)

    # 补充/验证字段
    for fund in verified:
        code = fund.get("code", "")

        # 如果 Claude 未获取规模，用 AKShare 补充
        if fund.get("scale_wan") is None:
            scale = get_fund_scale_wan(code)
            if scale is not None:
                fund["scale_wan"] = scale
                print("[AKSHARE] {} 补充规模={}万".format(code, scale), file=sys.stderr)

        # 生成收益标签（基于成立日期）
        est_date = fund.get("establishment_date")
        if est_date:
            fund["return_1y_label"], _ = get_return_label(est_date, None, 1)
            fund["return_3y_label"], _ = get_return_label(est_date, None, 3)

            # 计算年龄
            try:
                from datetime import datetime, date
                inception = datetime.strptime(est_date[:10], "%Y-%m-%d").date()
                today = date.today()
                total_months = (today.year - inception.year) * 12 + (today.month - inception.month)
                fund["age_years"] = total_months // 12
                fund["age_months"] = total_months % 12
            except Exception:
                pass

    # 输出结果
    result = {
        "candidates": data.get("candidates", []),
        "verified": verified,
        "failed": data.get("failed", []),
        "total": len(verified),
        "source": "claude_mcp_akshare_supplement",
    }

    # 写入 step3_akshare
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n[INFO] 已写入 _pipeline_step3_akshare.json ({} 只基金)".format(len(verified)), file=sys.stderr)


if __name__ == "__main__":
    main()
