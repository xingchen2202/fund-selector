#!/usr/bin/env python3
"""
validate_funds.py — 验证候选基金基本面，写入 pipeline
━━━━━━━━━━━━━━━━━━━━
读取 _pipeline_data.json 中的 candidates，
调用 AKShare 获取规模/基本信息，
写入 _pipeline_data.json["validated_funds"]。

注意：净值历史、经理等数据由 Claude 通过 cn-mutual-fund MCP 获取，
本脚本只负责 AKShare 可可靠获取的规模数据。
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
PIPELINE_FILE = PROJECT_ROOT / "fund-reports" / "_pipeline_data.json"


def read_pipeline():
    if PIPELINE_FILE.exists():
        with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def write_pipeline(key, data):
    pipeline = read_pipeline()
    pipeline[key] = data
    PIPELINE_FILE.parent.mkdir(exist_ok=True)
    with open(PIPELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(pipeline, f, ensure_ascii=False, indent=2)


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
                    num = float(scale_str.replace("万", "").replace("亿", ""))
                    return num
                elif "亿" in scale_str:
                    num = float(scale_str.replace("亿", ""))
                    return num * 10000
    except Exception as e:
        print(f"[WARN] AKShare获取{fund_code}规模失败: {e}", file=sys.stderr)
    return None


def fetch_fund_basic(fund_code, candidate_name, candidate_sector, candidate_score):
    """
    通过 AKShare 获取基金基本信息。
    返回 dict 包含规模和名称（如果 Excel 中名称缺失）。
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
        "return_3y": None,
        "max_drawdown": None,
        "sharpe": None,
        "top_holdings": [],
    }

    scale_wan = get_fund_scale_wan(fund_code)
    if scale_wan is not None:
        result["scale_wan"] = scale_wan

    # 尝试获取名称（如果 Excel 中名称为 "未知" 或缺失）
    if not candidate_name or candidate_name == "未知":
        try:
            import akshare as ak
            df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if df is not None and not df.empty:
                name_row = df[df["item"] == "基金简称"]
                if not name_row.empty:
                    result["name"] = str(name_row["value"].values[0])
        except Exception:
            pass

    return result


def main():
    pipeline = read_pipeline()
    candidates = pipeline.get("candidates", [])

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
        print(f"[OK] {code} 规模={scale_str}", file=sys.stderr)

    result = {
        "candidates": [c.get("code") for c in candidates],
        "verified": validated,
        "failed": [],
        "total": len(validated),
    }

    # 写入 pipeline
    write_pipeline("validated_funds", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[INFO] 已写入 pipeline['validated_funds'] ({len(validated)} 只基金)", file=sys.stderr)


if __name__ == "__main__":
    main()
