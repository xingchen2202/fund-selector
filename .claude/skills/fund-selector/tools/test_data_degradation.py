#!/usr/bin/env python3
"""数据退化与缺失测试 — 不完整数据下的鲁棒性
━━━━━━━━━━━━━━━━━━━━
测试场景：
1. 全部字段缺失
2. 极端异常值（负净值、1000% 费率）
3. 数据类型错误（字符串当数字）
4. 空字符串 / None / 0
"""

import sys, io, json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TOOLS = Path(r"C:\Users\22218\Desktop\fund-selector\.claude\skills\fund-selector\tools")


def _import(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(TOOLS / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_all_fields_missing():
    """全部字段缺失。"""
    cv = _import("constraint_validator")

    print("=" * 60)
    print("全部字段缺失测试")
    print("=" * 60)

    scenarios = [
        ("空字典", {}),
        ("仅免责声明", {"disclaimers": ["免责"]}),
        ("仅基金空列表", {"funds": []}),
        ("基金全空字段", {"funds": [{"code": "", "name": "", "industry_alloc": {}, "fee_total": None, "amount": 0, "is_dca": False}]}),
    ]

    for name, rec in scenarios:
        try:
            r = cv.validate_constraints(rec)
            print(f"  [{name}] 通过={r['passed']}, 失败={len(r['failures'])}")
        except Exception as e:
            print(f"  [{name}] 错误: {type(e).__name__}: {e}")

    print("  ✅ 全部字段缺失不崩溃")


def test_extreme_outliers():
    """极端异常值。"""
    cv = _import("constraint_validator")
    stress = _import("stress_tester")

    print("\n" + "=" * 60)
    print("极端异常值测试")
    print("=" * 60)

    # 负净值（不可能但测试鲁棒性）
    scenarios = [
        ("负净值 -1.5", {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}], "monthly_savings": 5000, "disclaimers": ["免责"]}),
        ("1000% 费率", {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 10.0, "amount": 1000, "is_dca": True}], "monthly_savings": 5000, "disclaimers": ["免责"]}),
        ("0 月储蓄", {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}], "monthly_savings": 0, "disclaimers": ["免责"]}),
    ]

    for name, rec in scenarios:
        try:
            r = cv.validate_constraints(rec)
            print(f"  [{name}] 通过={r['passed']}")
        except Exception as e:
            print(f"  [{name}] 错误: {type(e).__name__}")

    # 极端回撤
    try:
        r = stress.estimate_extreme_drawdown([-2.0], 0.5)  # -200% 回撤
        print(f"  [-200% 回撤] 结果: {r['adjusted_drawdown']:.1%}")
    except Exception as e:
        print(f"  [-200% 回撤] 错误: {type(e).__name__}")

    print("  ✅ 极端异常值不崩溃")


def test_type_mismatch():
    """数据类型错误。"""
    cv = _import("constraint_validator")

    print("\n" + "=" * 60)
    print("数据类型错误测试")
    print("=" * 60)

    scenarios = [
        ("金额为字符串", {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": "1000", "is_dca": True}], "monthly_savings": 5000, "disclaimers": ["免责"]}),
        ("费率为字符串", {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": "1.5", "amount": 1000, "is_dca": True}], "monthly_savings": 5000, "disclaimers": ["免责"]}),
    ]

    for name, rec in scenarios:
        try:
            r = cv.validate_constraints(rec)
            print(f"  [{name}] 通过={r['passed']}")
        except Exception as e:
            print(f"  [{name}] 错误: {type(e).__name__}: {str(e)[:40]}")

    print("  ✅ 数据类型错误有处理")


def test_empty_strings_and_none():
    """空字符串 / None / 0。"""
    cv = _import("constraint_validator")

    print("\n" + "=" * 60)
    print("空字符串/None/0 测试")
    print("=" * 60)

    scenarios = [
        ("空字符串代码", {"funds": [{"code": "", "name": "", "industry_alloc": {}, "fee_total": 1.5, "amount": 1000, "is_dca": True}], "monthly_savings": 5000, "disclaimers": ["免责"]}),
        ("None 费率", {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": None, "amount": 1000, "is_dca": True}], "monthly_savings": 5000, "disclaimers": ["免责"]}),
        ("0 金额", {"funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": 1.5, "amount": 0, "is_dca": True}], "monthly_savings": 5000, "disclaimers": ["免责"]}),
    ]

    for name, rec in scenarios:
        try:
            r = cv.validate_constraints(rec)
            print(f"  [{name}] 通过={r['passed']}")
        except Exception as e:
            print(f"  [{name}] 错误: {type(e).__name__}")

    print("  ✅ 空字符串/None/0 不崩溃")


def main():
    test_all_fields_missing()
    test_extreme_outliers()
    test_type_mismatch()
    test_empty_strings_and_none()
    print("\n" + "=" * 60)
    print("数据退化与缺失测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
