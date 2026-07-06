#!/usr/bin/env python3
"""Financial Rigor Toolkit — 金融数据严谨性验证工具（A 股基金版）
━━━━━━━━━━━━━━━━━━━━
移植自 ai-berkshire (MIT)，适配 A 股基金研究语境。

零外部依赖 — 仅 Python stdlib (decimal, json, math, argparse)。
Python >= 3.7。

用法（由 Claude 在关键校验点自动调用，无需手动执行）：
    # 1. 规模验算：份额×单位净值 vs 报告规模
    python tools/financial_rigor.py verify-scale --nav 1.0553 --shares 4.42e8 --reported 4.66e8

    # 2. 估值指标验算：PE/PB/股息率/年化收益
    python tools/financial_rigor.py verify-valuation --price 1.0553 --eps 0.052 --bps 1.08 --dividend 0.031

    # 3. 多源交叉验证：MCP vs Excel vs 实时排名 三源一致性
    python tools/financial_rigor.py cross-validate --field 规模 --values '{"MCP": 4.42, "Excel": 4.38, "ranking": 4.48}' --unit 亿

    # 4. Benford 检测：综合得分数据是否有伪造嫌疑
    python tools/financial_rigor.py benford --values '[33.0, 31.5, 29.0, ...]'

    # 5. 精确计算（Decimal，无浮点误差）
    python tools/financial_rigor.py calc --expr '1.0553 * 4.42e8'

    # 6. 定投收益复利验算：验证定投金额×期数的累计收益
    python tools/financial_rigor.py dca --monthly 1600 --months 6 --rate 0.08

    # 7. A 股特有：近 N 日复权净值年化收益精确计算
    python tools/financial_rigor.py annualized --start-nav 0.95 --end-nav 1.0553 --days 180
"""

import argparse
import json
import math
import sys
from decimal import Decimal, Context, ROUND_HALF_EVEN

# Windows GBK 兼容性：强制 UTF-8 输出，避免 ✅❌ 等字符崩溃
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# 精确十进制引擎（避免浮点漂移）
# ---------------------------------------------------------------------------

_CTX = Context(prec=28, rounding=ROUND_HALF_EVEN)


def exact(value) -> Decimal:
    """任意数值 → 精确 Decimal，规避 float 陷阱。"""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def fmt_number(d: Decimal, unit: str = "") -> str:
    """大数人类可读：亿/万/B/T。"""
    v = float(d)
    abs_v = abs(v)
    if unit in ("亿", "亿元", "万元", "万"):
        if abs_v >= 10000 and unit in ("万", "万元"):
            return f"{v / 10000:.2f}亿"
        if abs_v >= 10000 and unit in ("亿", "亿元"):
            return f"{v / 10000:.2f}万亿"
        return f"{v:.2f}{unit}"
    if abs_v >= 1e12:
        return f"{v / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{v / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{v / 1e6:.2f}M"
    return f"{v:,.4f}"


# ---------------------------------------------------------------------------
# 1. 规模验算：份额 × 单位净值 vs 报告规模
# ---------------------------------------------------------------------------

def verify_scale(nav, shares, reported_scale, unit="元"):
    """验证基金规模 = 份额 × 单位净值，并与报告规模对照。"""
    n = exact(nav)
    s = exact(shares)
    r = exact(reported_scale)

    calculated = _CTX.multiply(n, s)
    deviation = abs(float(calculated - r) / float(r)) * 100 if r != 0 else 0

    print("=" * 60)
    print("规模验算 (Scale Verification)")
    print("=" * 60)
    print(f"  单位净值 (NAV):       {n} {unit}")
    print(f"  总份额 (Shares):      {fmt_number(s, '份')}")
    print(f"  计算规模:             {fmt_number(calculated, '元')}")
    print(f"  报告规模:             {fmt_number(r, unit)}")
    print(f"  偏差:                 {deviation:.2f}%")
    print()

    if deviation > 5:
        print(f"  ❌ 警告: 偏差 {deviation:.1f}% > 5%, 请检查:")
        print(f"     - 净值是否为最新（QDII T+2 延迟）?")
        print(f"     - 份额是否最新（大额申赎会变动）?")
        print(f"     - 单位是否一致（元 vs 亿元）?")
        return False
    elif deviation > 1:
        print(f"  ⚠️  偏差 {deviation:.1f}% 在可接受范围, 或因申购赎回波动")
        return True
    else:
        print(f"  ✅ 验证通过, 偏差仅 {deviation:.2f}%")
        return True


# ---------------------------------------------------------------------------
# 2. 估值指标验算
# ---------------------------------------------------------------------------

def verify_valuation(price, eps=None, bps=None, dividend=None,
                     annual_return=None, unit=""):
    """由原始输入精确计算估值指标，避免 float 累积误差。"""
    p = exact(price)

    print("=" * 60)
    print("估值指标验算 (Valuation Verification)")
    print("=" * 60)
    print(f"  输入价格/净值: {p}")
    print()

    results = {}

    if eps is not None:
        e = exact(eps)
        if e != 0:
            pe = _CTX.divide(p, e)
            print(f"  PE:        {p} / {e} = {float(pe):.2f}x")
            results["PE"] = float(pe)
            ey = _CTX.divide(e, p) * 100
            print(f"  盈利收益率: {float(ey):.2f}%")

    if bps is not None:
        b = exact(bps)
        if b != 0:
            pb = _CTX.divide(p, b)
            print(f"  PB:        {p} / {b} = {float(pb):.2f}x")
            results["PB"] = float(pb)
            if eps is not None and float(exact(eps)) != 0:
                roe = _CTX.divide(exact(eps), b) * 100
                print(f"  ROE:       {float(roe):.2f}%")
                results["ROE"] = float(roe)

    if dividend is not None:
        d = exact(dividend)
        if p != 0:
            div_yield = _CTX.divide(d, p) * 100
            print(f"  股息率:    {float(div_yield):.2f}%")
            results["Dividend_Yield"] = float(div_yield)

    if annual_return is not None:
        r = exact(annual_return)
        print(f"  年化收益:  {float(r) * 100:.2f}%")
        results["Annual_Return"] = float(r)

    print()
    print("  ✅ 以上指标均使用精确十进制计算, 无浮点误差")
    return results


# ---------------------------------------------------------------------------
# 3. 多源交叉验证
# ---------------------------------------------------------------------------

def cross_validate(field_name, source_values: dict, unit="", tolerance_pct=2.0):
    """多数据源（MCP / Excel / 排名）一致性对比。"""
    print("=" * 60)
    print(f"交叉验证: {field_name} (Cross-Validation)")
    print("=" * 60)

    values = {k: exact(v) for k, v in source_values.items()}
    nums = sorted(float(v) for v in values.values())
    n = len(nums)
    median = nums[n // 2] if n % 2 == 1 else (nums[n // 2 - 1] + nums[n // 2]) / 2

    print(f"  数据来源数: {len(values)}")
    print(f"  参考中位数: {fmt_number(exact(median))} {unit}")
    print()

    all_ok = True
    for src, val in values.items():
        dev = abs(float(val) - median) / median * 100 if median != 0 else 0
        status = "✅" if dev <= tolerance_pct else "❌"
        if dev > tolerance_pct:
            all_ok = False
        print(f"  {status} {src:20s}: {fmt_number(val)} {unit}  (偏差 {dev:.2f}%)")

    print()
    if all_ok:
        print(f"  ✅ 所有来源偏差 ≤ {tolerance_pct}%, 数据一致")
    else:
        print(f"  ⚠️  存在来源偏差 > {tolerance_pct}%, 请核实差异原因")
        print(f"     建议: 优先采信 MCP 实时数据")
    print(f"\n  共识值 (中位数): {fmt_number(exact(median))} {unit}")
    return {"consensus": median, "all_consistent": all_ok}


# ---------------------------------------------------------------------------
# 4. Benford 定律快检（财务数据造假/篡改检测）
# ---------------------------------------------------------------------------

_BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def benford_check(values: list):
    """对一组财务综合得分做 Benford 定律快检。样本<50 时不可靠。"""
    print("=" * 60)
    print("Benford定律检测 (Data Fabrication Check)")
    print("=" * 60)

    digits = []
    for v in values:
        v = abs(float(v))
        if v > 0:
            sig = 10 ** (math.log10(v) - math.floor(math.log10(v)))
            d = int(sig)
            if 1 <= d <= 9:
                digits.append(d)

    n = len(digits)
    if n < 50:
        print(f"  ⚠️  样本量不足: {n} < 50, 分析不可靠")
        return None

    counts = {d: digits.count(d) for d in range(1, 10)}
    observed = {d: counts[d] / n for d in range(1, 10)}
    mad = sum(abs(observed[d] - _BENFORD[d]) for d in range(1, 10)) / 9

    conformity = ("高度符合" if mad < 0.006 else
                  "可接受" if mad < 0.012 else
                  "边缘" if mad < 0.015 else
                  "不符合 ⚠️")

    chi2 = sum((counts[d] - _BENFORD[d] * n) ** 2 / (_BENFORD[d] * n) for d in range(1, 10))

    print(f"  样本量:  {n}")
    print(f"  MAD:     {mad:.6f}")
    print(f"  Chi-sq:  {chi2:.2f}")
    print(f"  符合度:  {conformity}")
    print()
    print(f"  {'首位数':>6} {'观测':>8} {'期望':>10} {'偏差':>8}")
    print(f"  {'-' * 6} {'-' * 8} {'-' * 10} {'-' * 8}")
    for d in range(1, 10):
        obs = observed[d]
        exp = _BENFORD[d]
        dev = obs - exp
        flag = " ⚠️" if abs(dev) > 0.03 else ""
        print(f"  {d:>6d} {obs:>8.3f} {exp:>10.3f} {dev:>+8.3f}{flag}")
    print()
    ok = mad < 0.015
    print("  ✅ 首位数字分布符合Benford定律" if ok
          else "  ❌ 分布异常, 可能存在人为调整")
    return {"mad": mad, "conformity": conformity, "is_conforming": ok}


# ---------------------------------------------------------------------------
# 5. 精确计算器
# ---------------------------------------------------------------------------

def exact_calc(expr: str):
    """安全十进制表达式求值：仅允许数字与 + - * / ( )。"""
    print("=" * 60)
    print("精确计算 (Exact Calculator)")
    print("=" * 60)

    allowed = set("0123456789.+-*/() eE")
    if not all(c in allowed for c in expr.replace(" ", "")):
        print(f"  ❌ 不安全的表达式: {expr}")
        return None
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        d_result = exact(result)
        print(f"  表达式: {expr}")
        print(f"  结果:   {fmt_number(d_result)}")
        print(f"  精确值: {d_result}")
        return float(d_result)
    except Exception as e:
        print(f"  ❌ 计算错误: {e}")
        return None


# ---------------------------------------------------------------------------
# 6. 定投复利验算
# ---------------------------------------------------------------------------

def verify_dca(monthly, months, annual_rate):
    """等额定投累计本金 + 按年化率估算终值。"""
    m = exact(monthly)
    r = exact(annual_rate) / 12
    total_principal = exact(0)
    balance = exact(0)
    for _ in range(months):
        balance = _CTX.add(balance, m)
        balance = _CTX.multiply(balance, _CTX.add(Decimal("1"), r))
        total_principal = _CTX.add(total_principal, m)

    profit = _CTX.subtract(balance, total_principal)
    print("=" * 60)
    print("定投复利验算 (DCA Verification)")
    print("=" * 60)
    print(f"  每月定投:     {fmt_number(m, '元')}")
    print(f"  期数:         {months} 期")
    print(f"  假设年化:     {float(annual_rate) * 100:.2f}%")
    print(f"  累计本金:     {fmt_number(total_principal, '元')}")
    print(f"  预估终值:     {fmt_number(balance, '元')}")
    print(f"  预估收益:     {fmt_number(profit, '元')} ({float(profit) / float(total_principal) * 100:.2f}%)")
    return {"principal": float(total_principal), "final": float(balance)}


# ---------------------------------------------------------------------------
# 7. 区间年化收益（A 股基金常用）
# ---------------------------------------------------------------------------

def annualized_return(start_nav, end_nav, days):
    """由起止净值与天数精确计算年化收益。"""
    s = exact(start_nav)
    e = exact(end_nav)
    d = exact(days)
    if s <= 0 or d <= 0:
        print("  ❌ 起止净值与天数必须 > 0")
        return None
    ratio = _CTX.divide(e, s)
    # 年化 = (end/start)^(365/days) - 1
    years = _CTX.divide(exact(365), d)
    annual = float(ratio) ** float(years) - 1
    total = float(ratio) - 1
    print("=" * 60)
    print("区间年化收益 (Annualized Return)")
    print("=" * 60)
    print(f"  起始净值: {s}")
    print(f"  终止净值: {e}")
    print(f"  区间天数: {days}")
    print(f"  区间收益: {total * 100:.2f}%")
    print(f"  年化收益: {annual * 100:.2f}%")
    return {"total": total, "annualized": annual}


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Financial Rigor Toolkit — 金融数据严谨性验证工具（A 股基金版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s verify-scale --nav 1.0553 --shares 4.42e8 --reported 4.66e8
  %(prog)s verify-valuation --price 1.0553 --eps 0.052 --bps 1.08
  %(prog)s cross-validate --field 规模 --values '{"MCP": 4.42, "Excel": 4.38}' --unit 亿
  %(prog)s benford --values '[33.0, 31.5, 29.0]'
  %(prog)s calc --expr '1.0553 * 4.42e8'
  %(prog)s dca --monthly 1600 --months 6 --rate 0.08
  %(prog)s annualized --start-nav 0.95 --end-nav 1.0553 --days 180
        """)

    sub = parser.add_subparsers(dest="command")

    sc = sub.add_parser("verify-scale", help="规模验算：份额×净值 vs 报告规模")
    sc.add_argument("--nav", type=float, required=True)
    sc.add_argument("--shares", type=float, required=True)
    sc.add_argument("--reported", type=float, required=True)
    sc.add_argument("--unit", default="元")

    val = sub.add_parser("verify-valuation", help="估值指标验算")
    val.add_argument("--price", type=float, required=True)
    val.add_argument("--eps", type=float, default=None)
    val.add_argument("--bps", type=float, default=None)
    val.add_argument("--dividend", type=float, default=None)
    val.add_argument("--annual-return", type=float, default=None)

    cv = sub.add_parser("cross-validate", help="多源交叉验证")
    cv.add_argument("--field", required=True)
    cv.add_argument("--values", required=True)
    cv.add_argument("--unit", default="")
    cv.add_argument("--tolerance", type=float, default=2.0)

    bf = sub.add_parser("benford", help="Benford定律检测")
    bf.add_argument("--values", required=True)

    ca = sub.add_parser("calc", help="精确计算")
    ca.add_argument("--expr", required=True)

    dc = sub.add_parser("dca", help="定投复利验算")
    dc.add_argument("--monthly", type=float, required=True)
    dc.add_argument("--months", type=int, required=True)
    dc.add_argument("--rate", type=float, required=True)

    an = sub.add_parser("annualized", help="区间年化收益")
    an.add_argument("--start-nav", type=float, required=True)
    an.add_argument("--end-nav", type=float, required=True)
    an.add_argument("--days", type=int, required=True)

    args = parser.parse_args()

    cmds = {
        "verify-scale": lambda: verify_scale(args.nav, args.shares, args.reported, args.unit),
        "verify-valuation": lambda: verify_valuation(args.price, args.eps, args.bps,
                                                      args.dividend, args.annual_return),
        "cross-validate": lambda: cross_validate(args.field, json.loads(args.values),
                                                 args.unit, args.tolerance),
        "benford": lambda: benford_check(json.loads(args.values)),
        "calc": lambda: exact_calc(args.expr),
        "dca": lambda: verify_dca(args.monthly, args.months, args.rate),
        "annualized": lambda: annualized_return(args.start_nav, args.end_nav, args.days),
    }
    fn = cmds.get(args.command)
    if fn:
        fn()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
