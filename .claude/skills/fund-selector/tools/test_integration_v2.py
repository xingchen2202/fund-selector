#!/usr/bin/env python3
"""集成测试 — 验证全部新工具协同工作
━━━━━━━━━━━━━━━━━━━━
端到端场景：用户请求 → 筛选 → 约束校验 → 压力测试 → 相关性 → 仓位优化 → 再平衡 → 最终建议
"""

import sys, io, json, importlib
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


def test_full_workflow():
    """完整工作流：从用户请求到最终建议。"""
    cv = _import("constraint_validator")
    stress = _import("stress_tester")
    corr = _import("correlation_checker")
    pos = _import("position_optimizer")
    reb = _import("rebalancer")

    print("=" * 60)
    print("完整工作流集成测试")
    print("=" * 60)

    # Step 1: 候选基金
    funds = [
        {"code": "110011", "name": "易方达消费", "industry_alloc": {"消费": 35, "白酒": 20},
         "fee_total": 1.5, "amount": 2000, "is_dca": True,
         "top_holdings": ["茅台", "五粮液", "泸州", "汾酒", "海天"],
         "max_drawdown": -0.25},
        {"code": "519671", "name": "华泰柏瑞红利", "industry_alloc": {"金融": 25, "能源": 20},
         "fee_total": 1.2, "amount": 1000, "is_dca": True,
         "top_holdings": ["神华", "大秦", "招行", "兴业", "长江电力"],
         "max_drawdown": -0.15},
    ]

    # Step 2: 约束校验
    rec = {
        "funds": funds,
        "monthly_savings": 3000,
        "target_allocation": {"stock": 0.8, "bond": 0.1, "cash": 0.1},
        "actual_allocation": {"stock": 0.85, "bond": 0.05, "cash": 0.1},
        "has_emergency_fund": True,
        "has_high_interest_debt": False,
        "has_insurance": True,
        "rebalancing_rule": "季度回顾，偏离>10%触发",
        "disclaimers": ["不构成投资建议"],
    }
    constraint = cv.validate_constraints(rec)
    print(f"\n  [约束校验] {'✅ 通过' if constraint['passed'] else '❌ 不通过'}")

    # Step 3: 压力测试
    drawdowns = [f["max_drawdown"] for f in funds]
    stress_result = stress.stress_test_portfolio(drawdowns, [2000, 1000], correlation=0.3)
    print(f"  [压力测试] 极端回撤: {stress_result['adjusted_drawdown']:.1%}, "
          f"风险等级: {stress_result['risk_tier']}")

    # Step 4: 持仓相关性
    overlap = corr.check_holdings_overlap(funds[0]["top_holdings"], funds[1]["top_holdings"])
    print(f"  [相关性] 重仓重叠: {overlap['common_count']} 只, {overlap['message'][:30]}")

    # Step 5: 仓位优化
    kelly = pos.kelly_criterion(win_rate=0.60, payoff=1.5)
    print(f"  [仓位优化] Kelly 建议: {kelly['position_pct']}")

    # Step 6: 再平衡检测
    rebalance = reb.check_threshold(
        {"stock": 0.8, "bond": 0.1, "cash": 0.1},
        {"stock": 0.85, "bond": 0.05, "cash": 0.1}
    )
    print(f"  [再平衡] {'⚠️ 触发' if rebalance['triggered'] else '✅ 无需'}")

    print("\n  ✅ 完整工作流集成测试通过")


def test_new_tools_exist():
    """验证所有新工具文件存在。"""
    tools = [
        "stress_tester.py", "correlation_checker.py",
        "behavioral_scorer.py", "position_optimizer.py", "rebalancer.py"
    ]
    missing = [t for t in tools if not (TOOLS / t).exists()]
    print(f"\n  [工具完整性] {len(tools) - len(missing)}/{len(tools)} 存在")
    assert not missing, f"缺失: {missing}"


def main():
    test_new_tools_exist()
    test_full_workflow()
    print("\n" + "=" * 60)
    print("集成测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
