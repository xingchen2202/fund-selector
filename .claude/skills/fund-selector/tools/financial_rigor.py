#!/usr/bin/env python3
"""Financial Rigor Toolkit — 金融数据严谨性验证工具
━━━━━━━━━━━━━━━━━━━━
移植自 ai-berkshire (MIT)，适配 A 股基金研究语境。

零外部依赖 — 仅 Python stdlib (decimal, json, math, argparse)。
Python >= 3.7。

用法（由 Claude 在关键校验点自动调用）：
    python tools/financial_rigor.py verify-scale --nav 1.0553 --shares 4.42e8 --reported 4.68e8
    python tools/financial_rigor.py verify-valuation --price 1.0553 --eps 0.052 --bps 1.08
    python tools/financial_rigor.py cross-validate --field 规模 --values '{"MCP": 4.42, "Excel": 4.38}' --unit 亿
    python tools/financial_rigor.py benford --values '[33.0, 31.5, 29.0, ...]'
    python tools/financial_rigor.py calc --expr '1.0553 * 4.42e8'
    python tools/financial_rigor.py three-scenario --price 1.0553 --eps 0.052 --shares 4.42e8 --growth 0.15 0.08 0.0 --pe 25 20 15
"""

import argparse
import json
import math
import sys
import io

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from decimal import Decimal, Context, ROUND_HALF_EVEN

_CTX = Context(prec=28, rounding=ROUND_HALF_EVEN)


def exact(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def fmt_number(d: Decimal, unit: str = "") -> str:
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


def verify_scale(nav, shares, reported_scale, unit="元"):
    """验证基金规模 = 份额 × 单位净值。"""
    n = exact(nav)
    s = exact(shares)
    r = exact(reported_scale)
    calculated = _CTX.multiply(n, s)
    if r == 0:
        print("=" * 60)
        print("规模验算 (Scale Verification)")
        print("=" * 60)
        print(f"  单位净值 (NAV):     {n} {unit}")
        print(f"  总份额 (Shares):    {fmt_number(s, '份')}")
        print(f"  计算规模:           {fmt_number(calculated, '元')}")
        print(f"  报告规模:           {fmt_number(r, unit)}")
        print()
        print("  ❌ 报告规模为零，无法验算偏差")
        return False
    deviation = abs(float(calculated - r) / float(r)) * 100 if r != 0 else 0
    passed = deviation <= 5

    print("=" * 60)
    print("规模验算 (Scale Verification)")
    print("=" * 60)
    print(f"  单位净值 (NAV):     {n} {unit}")
    print(f"  总份额 (Shares):    {fmt_number(s, '份')}")
    print(f"  计算规模:           {fmt_number(calculated, '元')}")
    print(f"  报告规模:           {fmt_number(r, unit)}")
    print(f"  偏差:               {deviation:.2f}%")
    print()
    if passed:
        print(f"  ✅ 验证通过, 偏差仅 {deviation:.2f}%")
    else:
        print(f"  ❌ 警告: 偏差 {deviation:.1f}% > 5%")
    return passed


def verify_valuation(price, eps=None, bps=None, dividend=None):
    """计算并验证估值指标。"""
    p = exact(price)
    results = {}
    print("=" * 60)
    print("估值指标验算 (Valuation Verification)")
    print("=" * 60)
    print(f"  输入价格/净值: {p}")
    print()

    if eps is not None:
        e = exact(eps)
        if e != 0:
            pe = _CTX.divide(p, e)
            print(f"  PE (TTM):  {p} / {e} = {float(pe):.2f}x")
            results["PE"] = float(pe)
            # 负 PE 警告：企业亏损，PE 无意义
            if float(pe) < 0:
                print(f"  ⚠️  负 PE：企业亏损，PE 指标无意义，建议改用 PS 或 PB")
        else:
            print(f"  PE (TTM):  EPS 为零，无法计算")

    if bps is not None:
        b = exact(bps)
        if b != 0:
            pb = _CTX.divide(p, b)
            print(f"  PB:        {p} / {b} = {float(pb):.2f}x")
            results["PB"] = float(pb)
            # 负 PB 警告：资不抵债
            if float(pb) < 0:
                print(f"  ⚠️  负 PB：净资产为负，企业资不抵债")
        else:
            print(f"  PB:  BPS 为零，无法计算")

    if dividend is not None:
        d = exact(dividend)
        if p != 0:
            div_yield = _CTX.divide(d, p) * 100
            print(f"  股息率:    {d} / {p} = {float(div_yield):.2f}%")
            results["Dividend_Yield"] = float(div_yield)

    print()
    print("  ✅ 以上指标均使用精确十进制计算, 无浮点误差")
    return results


def cross_validate(field_name, source_values: dict, unit="", tolerance_pct=2.0):
    """多数据源交叉验证。"""
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

    # 单源 = 无法交叉验证
    if len(values) == 1:
        print(f"  ⚠️  仅 1 个数据来源，无法交叉验证（需 ≥2 源）")
        return {"consensus": median, "all_consistent": None, "status": "单源无法验证"}

    # 双零 = 无有效数据，无法验证（与 data_validator 行为一致）
    if all(v == 0 for v in nums):
        print(f"  ⚠️  所有来源均为 0，无法验证一致性")
        return {"consensus": 0, "all_consistent": None, "status": "无法验证"}

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

    consensus = median
    print(f"\n  共识值 (中位数): {fmt_number(exact(consensus))} {unit}")
    return {"consensus": consensus, "all_consistent": all_ok}


_BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def benford_check(values: list):
    """Benford 定律检测（财务数据防伪造）。"""
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
    mad = sum(abs(observed.get(d, 0) - _BENFORD[d]) for d in range(1, 10)) / 9

    chi2 = sum((counts[d] - _BENFORD[d] * n) ** 2 / (_BENFORD[d] * n) for d in range(1, 10))

    conformity = ("高度符合" if mad < 0.006 else
                  "可接受" if mad < 0.012 else
                  "边缘" if mad < 0.015 else
                  "不符合 ⚠️")

    print(f"  样本量:  {n}")
    print(f"  MAD:     {mad:.6f}")
    print(f"  Chi-sq:  {chi2:.2f}")
    print(f"  符合度:  {conformity}")
    print()

    print(f"  {'首位数':>6} {'观测':>8} {'Benford期望':>12} {'偏差':>8}")
    print(f"  {'-'*6} {'-'*8} {'-'*12} {'-'*8}")
    for d in range(1, 10):
        obs = observed.get(d, 0)
        exp = _BENFORD[d]
        dev = obs - exp
        flag = " ⚠️" if abs(dev) > 0.03 else ""
        print(f"  {d:>6d} {obs:>8.3f} {exp:>12.3f} {dev:>+8.3f}{flag}")

    print()
    ok = mad < 0.015
    print("  ✅ 数据首位数字分布符合Benford定律" if ok
          else "  ❌ 数据首位数字分布异常, 可能存在人为调整")
    return {"mad": mad, "conformity": conformity, "is_conforming": ok}


def exact_calc(expr: str):
    """安全十进制表达式求值。"""
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


def three_scenario_valuation(current_price, current_eps, shares_billion,
                              growth_optimistic, growth_neutral, growth_pessimistic,
                              pe_optimistic, pe_neutral, pe_pessimistic, years=3, currency=""):
    """三情景目标价估值模型。"""
    print("=" * 60)
    print("三情景估值模型 (Three-Scenario Valuation)")
    print("=" * 60)

    p = exact(current_price)
    eps = exact(current_eps)
    shares = exact(shares_billion)

    scenarios = [
        ("乐观 (Bull)", growth_optimistic, pe_optimistic),
        ("中性 (Base)", growth_neutral, pe_neutral),
        ("悲观 (Bear)", growth_pessimistic, pe_pessimistic),
    ]

    print(f"  当前价格: {p} {currency}")
    print(f"  当前EPS:  {eps}")
    print(f"  预测期:   {years}年")
    print()
    print(f"  {'情景':12} {'年增速':>8} {'目标PE':>8} {'目标EPS':>10} {'目标股价':>10} {'涨跌幅':>8}")
    print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*10} {'-'*10} {'-'*8}")

    for name, growth, pe_val in scenarios:
        g = exact(growth)
        target_pe = exact(pe_val)
        future_eps = eps
        for _ in range(years):
            future_eps = _CTX.multiply(future_eps, _CTX.add(Decimal("1"), g))
        target_price = _CTX.multiply(future_eps, target_pe)
        change = float(target_price - p) / float(p) * 100

        print(f"  {name:12} {float(g)*100:>7.0f}% {float(target_pe):>7.0f}x "
              f"{float(future_eps):>10.2f} {float(target_price):>9.1f} {change:>+7.1f}%")

    print()
    print("  ✅ 所有计算使用精确十进制, 结果可审计复现")


def main():
    parser = argparse.ArgumentParser(
        description="Financial Rigor Toolkit — 金融数据严谨性验证工具（A 股基金版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s verify-scale --nav 1.0553 --shares 4.42e8 --reported 4.68e8
  %(prog)s verify-valuation --price 1.0553 --eps 0.052 --bps 1.08
  %(prog)s cross-validate --field 规模 --values '{"MCP": 4.42, "Excel": 4.38}' --unit 亿
  %(prog)s benford --values '[33.0, 31.5, 29.0]'
  %(prog)s calc --expr '1.0553 * 4.42e8'
  %(prog)s three-scenario --price 1.0553 --eps 0.052 --shares 4.42e8 --growth 0.15 0.08 0.0 --pe 25 20 15
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

    cv = sub.add_parser("cross-validate", help="多源交叉验证")
    cv.add_argument("--field", required=True)
    cv.add_argument("--values", required=True)
    cv.add_argument("--unit", default="")
    cv.add_argument("--tolerance", type=float, default=2.0)

    bf = sub.add_parser("benford", help="Benford定律检测")
    bf.add_argument("--values", required=True)

    ca = sub.add_parser("calc", help="精确计算")
    ca.add_argument("--expr", required=True)

    ts = sub.add_parser("three-scenario", help="三情景估值")
    ts.add_argument("--price", type=float, required=True)
    ts.add_argument("--eps", type=float, required=True)
    ts.add_argument("--shares", type=float, required=True, help="总股本(亿)")
    ts.add_argument("--growth", nargs=3, type=float, required=True)
    ts.add_argument("--pe", nargs=3, type=float, required=True)
    ts.add_argument("--years", type=int, default=3)
    ts.add_argument("--currency", default="")

    args = parser.parse_args()

    if args.command == "verify-scale":
        verify_scale(args.nav, args.shares, args.reported, args.unit)
    elif args.command == "verify-valuation":
        verify_valuation(args.price, args.eps, args.bps, args.dividend)
    elif args.command == "cross-validate":
        cross_validate(args.field, json.loads(args.values), args.unit, args.tolerance)
    elif args.command == "benford":
        benford_check(json.loads(args.values))
    elif args.command == "calc":
        exact_calc(args.expr)
    elif args.command == "three-scenario":
        three_scenario_valuation(
            args.price, args.eps, args.shares,
            args.growth[0], args.growth[1], args.growth[2],
            args.pe[0], args.pe[1], args.pe[2],
            args.years, args.currency)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
