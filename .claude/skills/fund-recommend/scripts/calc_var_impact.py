#!/usr/bin/env python3
"""
calc_var_impact.py — 基于净值时间序列计算真实 VaR 影响
━━━━━━━━━━━━━━━━━━━━
读取 step3 的 nav_series，计算每只基金的实际年化波动率，
再计算边际 VaR。无净值序列时标注"数据不足"。

P8修复：不再使用固定波动率 0.15，改为基于净值序列的真实计算。
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


def read_step(step_key):
    """从对应步骤文件读取数据"""
    try:
        script_dir = Path(__file__).parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from pipeline import read_step
        return read_step(step_key)
    except Exception:
        return {}


def write_var_impacts(data):
    """写入 step4 文件"""
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from pipeline import write_step
    write_step("step4", {"var_impacts": data})


def compute_annual_volatility(nav_series):
    """
    从净值序列计算年化波动率。

    Args:
        nav_series: list of float（按时间顺序的净值列表）
                    或 list of dict（{"date": ..., "nav": ...}）

    Returns:
        float: 年化波动率（如 0.25 表示 25%）
        None: 数据不足（少于20个数据点）
    """
    if not nav_series or len(nav_series) < 20:
        return None

    # 统一提取净值
    navs = []
    for item in nav_series:
        if isinstance(item, dict):
            nav = item.get("nav") or item.get("单位净值")
            if nav is not None:
                try:
                    navs.append(float(nav))
                except (ValueError, TypeError):
                    pass
        else:
            try:
                navs.append(float(item))
            except (ValueError, TypeError):
                pass

    if len(navs) < 20:
        return None

    # 日收益率
    returns = []
    for i in range(1, len(navs)):
        if navs[i - 1] > 0:
            r = (navs[i] - navs[i - 1]) / navs[i - 1]
            returns.append(r)

    if len(returns) < 19:
        return None

    # 日收益率标准差
    n = len(returns)
    mean_r = sum(returns) / n
    variance = sum((r - mean_r) ** 2 for r in returns) / (n - 1)
    daily_vol = math.sqrt(variance)

    # 年化波动率 = 日波动率 × √252
    annual_vol = daily_vol * math.sqrt(252)

    return annual_vol


def compute_var_from_nav(nav_series, investment_amount, confidence=0.95):
    """
    基于净值时间序列计算真实 VaR。

    Args:
        nav_series: 净值列表（按时间顺序）
        investment_amount: 买入金额（元）
        confidence: 置信度（默认95%）

    Returns:
        (var_amount, annual_vol, error_msg)
        - var_amount: 月度 VaR（元），失败时为 None
        - annual_vol: 年化波动率，失败时为 None
        - error_msg: 错误信息，成功时为 None
    """
    if not nav_series or len(nav_series) < 20:
        return None, None, "净值序列不足20个数据点，无法计算"

    try:
        annual_vol = compute_annual_volatility(nav_series)
        if annual_vol is None or annual_vol <= 0:
            return None, None, "有效净值数据不足"

        # 月度 VaR（持有21个交易日，95%置信度）
        z_score = 1.645 if confidence == 0.95 else 2.326
        monthly_vol = annual_vol * math.sqrt(21 / 252)
        var_amount = investment_amount * monthly_vol * z_score

        return round(var_amount, 2), round(annual_vol, 4), None

    except Exception as e:
        return None, None, f"计算失败: {e}"


def main():
    # 读取约束
    step0 = read_step("step0")
    step2 = read_step("step2")
    step3 = read_step("step3")

    # 获取现有组合 VaR 和市值
    existing_var = step0.get("monthly_var_estimate", 1000)
    existing_value = step0.get("total_value", 40000)
    var_budget = step0.get("var_budget", 2000)

    # 获取候选基金
    candidates = step2.get("top10", step2.get("candidates", []))
    if not candidates:
        print(json.dumps({"error": "step2 中无 candidates，请先运行 screen_candidates.py"}))
        sys.exit(1)

    # 从 step3 获取净值序列
    verified_funds = step3.get("verified", [])
    if isinstance(verified_funds, dict):
        verified_funds = verified_funds.get("verified", [])

    # 构建 code → nav_series 映射
    nav_map = {}
    for f in verified_funds:
        code = f.get("code", "")
        nav_series = f.get("nav_series")
        if code and nav_series:
            nav_map[code] = nav_series

    # 模拟加入 5% 仓位
    investment_per_fund = existing_value * 0.05

    print(f"[INFO] 计算 VaR: 现有VaR={existing_var}, 新增仓位={investment_per_fund:.0f}元, 预算={var_budget}元",
          file=sys.stderr)

    var_results = {}
    excluded_by_var = []

    for c in candidates:
        code = c.get("code", "")
        name = c.get("name", "")

        nav_series = nav_map.get(code)
        var_amount, annual_vol, error = compute_var_from_nav(nav_series, investment_per_fund)

        if error:
            # 数据不足时不排除，标注
            var_results[code] = {
                "code": code,
                "name": name,
                "marginal_var": None,
                "annual_vol": None,
                "var_display": f"数据不足，无法计算（{error}）",
                "exceeds_budget": False,
                "data_insufficient": True,
            }
            print(f"[VaR] {code} {name}: {error}", file=sys.stderr)
        else:
            # 检查是否超出预算
            exceeds = var_amount > var_budget
            var_results[code] = {
                "code": code,
                "name": name,
                "marginal_var": var_amount,
                "annual_vol": annual_vol,
                "var_display": f"{var_amount} 元（95%置信度，月度，年化波动率{annual_vol:.1%}）",
                "exceeds_budget": exceeds,
                "data_insufficient": False,
            }
            status = "⚠️ 超出预算" if exceeds else "✅ 可接受"
            print(f"[VaR] {code} {name}: 年化波动率={annual_vol:.2%}, 边际VaR={var_amount}元 {status}",
                  file=sys.stderr)

            if exceeds:
                excluded_by_var.append({
                    "code": code,
                    "name": name,
                    "var": var_amount,
                    "reason": f"VaR{var_amount}元超预算{var_budget}元"
                })

    # 写入 step4
    output = {
        "var_impacts": var_results,
        "excluded_by_var": excluded_by_var,
        "investment_per_fund": investment_per_fund,
        "var_budget": var_budget,
    }
    write_var_impacts(output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n[INFO] 已写入 step4 ({len(var_results)} 只基金, 排除{len(excluded_by_var)}只)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
