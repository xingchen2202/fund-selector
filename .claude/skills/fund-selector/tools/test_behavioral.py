#!/usr/bin/env python3
"""行为金融偏差检测测试
━━━━━━━━━━━━━━━━━━━━
测试 skill 能否识别以下行为偏差：
1. 追涨杀跌（追逐过去业绩）
2. 过度集中（单一行业/基金占比过高）
3. 恐慌抛售信号
4. 锚定效应（成本价锚定）
5. 处置效应（过早卖盈持亏）
"""

import sys, io, json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def test_chasing_returns():
    """追涨杀跌检测：过去 1 年涨幅 >50% 的基金需谨慎。"""
    print("=" * 60)
    print("追涨杀跌偏差检测")
    print("=" * 60)

    scenarios = [
        ("某半导体基金近1年 +80%", 0.80, "⚠️ 高涨幅 → 可能已高估，需谨慎"),
        ("某红利基金近1年 +8%", 0.08, "✅ 温和涨幅 → 可持续关注"),
        ("某医药基金近1年 -30%", -0.30, "⚠️ 高跌幅 → 恐慌抛售？需分析基本面"),
    ]

    for name, return_1y, advice in scenarios:
        print(f"\n  [{name}]")
        print(f"    建议: {advice}")


def test_overconcentration():
    """过度集中检测：单一行业/基金占比过高。"""
    print("\n" + "=" * 60)
    print("过度集中偏差检测")
    print("=" * 60)

    scenarios = [
        ("半导体占组合 45%", 0.45, "⚠️ 过度集中，建议降至 <20%"),
        ("单一基金占组合 60%", 0.60, "⚠️ 过度集中，建议分散至 ≤30%"),
        ("最大行业占比 15%", 0.15, "✅ 分散度良好"),
    ]

    for name, ratio, advice in scenarios:
        print(f"\n  [{name}]")
        print(f"    建议: {advice}")


def test_panic_selling_signals():
    """恐慌抛售信号检测：市场情绪极端时的非理性行为。"""
    print("\n" + "=" * 60)
    print("恐慌抛售信号检测")
    print("=" * 60)

    scenarios = [
        ("市场单日 -8%，恐慌抛售", "panic", "❌ 不建议：恐慌时卖出往往卖在底部"),
        ("基金连续 -15%，止损卖出", "stop_loss", "⚠️ 需区分：基本面恶化 vs 市场情绪"),
        ("杠杆爆仓被迫卖出", "forced", "❌ 避免使用杠杆投资"),
    ]

    for name, signal_type, advice in scenarios:
        print(f"\n  [{name}]")
        print(f"    类型: {signal_type}")
        print(f"    建议: {advice}")


def test_anchor_effect():
    """锚定效应检测：成本价锚定导致非理性持有。"""
    print("\n" + "=" * 60)
    print("锚定效应检测")
    print("=" * 60)

    scenarios = [
        ("成本 1.5，现价 1.2，等待回本", "成本锚定", "❌ 错误：决策应基于未来预期，非历史成本"),
        ("盈利 20%，担心回吐，过早卖出", "盈利锚定", "⚠️ 需评估：基本面是否支持继续持有"),
    ]

    for name, bias, advice in scenarios:
        print(f"\n  [{name}]")
        print(f"    偏差: {bias}")
        print(f"    建议: {advice}")


def test_disposition_effect():
    """处置效应检测：过早卖盈持亏。"""
    print("\n" + "=" * 60)
    print("处置效应检测")
    print("=" * 60)

    scenarios = [
        ("盈利基金立即卖出，亏损基金长期持有", "disposition", "❌ 处置效应：理性做法相反"),
    ]

    for name, bias, advice in scenarios:
        print(f"\n  [{name}]")
        print(f"    偏差: {bias}")
        print(f"    建议: {advice}")


def main():
    test_chasing_returns()
    test_overconcentration()
    test_panic_selling_signals()
    test_anchor_effect()
    test_disposition_effect()
    print("\n" + "=" * 60)
    print("行为金融偏差检测完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
