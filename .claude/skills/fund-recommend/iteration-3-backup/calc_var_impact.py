#!/usr/bin/env python3
"""
calc_var_impact.py — 计算加入新基金后的组合 VaR 变化
━━━━━━━━━━━━━━━━━━━━
读取 _pipeline_data.json 中的 constraints 和 candidates，
计算每只候选基金的边际 VaR，
写入 _pipeline_data.json["var_impacts"]。
"""
import json
import math
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


def read_constraints():
    """从 step0 文件读取约束"""
    try:
        script_dir = Path(__file__).parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from pipeline import read_step
        return read_step("step0")
    except Exception:
        return {}


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


def write_var_impacts(data):
    """写入 step4 文件"""
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from pipeline import write_step
    write_step("step4", {"var_impacts": data})


def calc_marginal_var(
    new_fund_value: float,
    existing_value: float,
    existing_var: float,
    new_fund_vol: float = 0.15,
    correlation: float = 0.5,
) -> dict:
    """计算加入新基金后的边际 VaR"""
    new_fund_var = new_fund_value * new_fund_vol / math.sqrt(12)
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
    pipeline = read_constraints()

    # 获取现有组合 VaR
    existing_var = pipeline.get("monthly_var_estimate", 1000)
    existing_value = pipeline.get("total_value", 50000)

    # 获取候选基金
    candidates = read_candidates()
    if not candidates:
        print(json.dumps({"error": "step2 中无 candidates，请先运行 screen_candidates.py"}))
        sys.exit(1)

    # 模拟加入 5% 仓位（按总市值的 5%）
    new_fund_value = existing_value * 0.05

    print(f"[INFO] 计算 VaR 影响: 现有VaR={existing_var}, 新增仓位={new_fund_value:.0f}元", file=sys.stderr)

    var_results = {}
    for c in candidates:
        code = c.get("code", "")
        name = c.get("name", "")
        result = calc_marginal_var(new_fund_value, existing_value, existing_var)
        var_results[code] = {
            "code": code,
            "name": name,
            **result,
        }
        status = "⚠️ 超出预算" if result["exceeds_budget"] else "✅ 可接受"
        print(f"[VaR] {code} {name}: 边际VaR={result['marginal_var']}元 {status}", file=sys.stderr)

    # 写入 step4
    write_var_impacts(var_results)
    print(json.dumps(var_results, ensure_ascii=False, indent=2))
    print(f"\n[INFO] 已写入 pipeline['var_impacts'] ({len(var_results)} 只基金)", file=sys.stderr)


if __name__ == "__main__":
    main()
