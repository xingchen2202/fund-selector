#!/usr/bin/env python3
"""约束校验器（Constraint Validator）— 8 条铁律程序化执行
━━━━━━━━━━━━━━━━━━━━
移植自 CLAUDE.md 的 8 条铁律，从"文档指令"升级为"程序化强制"。

用法：
    from tools.constraint_validator import validate_constraints
    result = validate_constraints(recommendation)
    if not result["passed"]:
        print("约束不通过:", result["failures"])

输入 recommendation 字典结构：
{
  "funds": [{"code": "110011", "name": "...", "industry_alloc": {"制造业": 30, "金融": 15}, "fee_total": 1.5, "amount": 10000}],
  "monthly_savings": 3000,          # 月净储蓄额
  "total_investment": 50000,        # 总资金
  "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},  # 第二步设定
  "actual_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},   # 第四步实际
  "valuation_percentile": 0.25,     # 当前估值分位
  "has_emergency_fund": True,       # 应急金
  "has_high_interest_debt": False,  # 高息负债
  "has_insurance": True,            # 保险
  "rebalancing_rule": "季度回顾，偏离>10%触发",
  "disclaimers": ["不构成投资建议"]
}

返回：
{"passed": bool, "failures": [...], "warnings": [...]}
"""

from __future__ import annotations

import io
import sys
from typing import Any

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# 常识校验区间（移植自 CLAUDE.md 约束四）
COMMONSENSE_RANGES = {
    "hs300_pe": (8, 25, "沪深300 PE 历史区间 8-25x"),
    "sh_pe": (8, 50, "上证 PE 历史区间 8-50x"),
    "pb": (0.8, 3.0, "PB 历史区间 0.8-3.0x"),
}

# 行业穿透阈值
INDUSTRY_OVERLAP_THRESHOLD = 0.15  # 15%


def validate_constraints(rec: dict) -> dict:
    """对推荐组合执行 8 条铁律校验。

    Returns:
        {"passed": bool, "failures": [str], "warnings": [str]}
    """
    failures = []
    warnings = []

    # 约束一：穿透防重叠（行业≤15%）
    _check_industry_overlap(rec, failures)

    # 约束二：预算硬平衡
    _check_budget_balance(rec, failures)

    # 约束三：配置比例闭环
    _check_allocation_closed_loop(rec, failures)

    # 约束四：常识校验
    _check_commonsense(rec, warnings)

    # 约束五：财务预检
    _check_financial_health(rec, warnings)

    # 约束六：费率穿透
    _check_fee_transparency(rec, failures)

    # 约束七：再平衡机制
    _check_rebalancing(rec, warnings)

    # 约束八：免责声明（历史筛选交叉验证为可选，归入警告）
    _check_disclaimer(rec, warnings)

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "warnings": warnings,
    }


def _check_industry_overlap(rec: dict, failures: list):
    """约束一：任意两只基金在同一行业仓位重合度 ≤15%。"""
    funds = rec.get("funds", [])
    if len(funds) < 2:
        return

    for i in range(len(funds)):
        for j in range(i + 1, len(funds)):
            f1, f2 = funds[i], funds[j]
            ind1 = f1.get("industry_alloc", {})
            ind2 = f2.get("industry_alloc", {})
            for industry in set(ind1) | set(ind2):
                overlap = min(ind1.get(industry, 0), ind2.get(industry, 0))
                if overlap > INDUSTRY_OVERLAP_THRESHOLD * 100:
                    failures.append(
                        f"[穿透防重叠] {f1.get('name','?')} 与 {f2.get('name','?')} "
                        f"在 {industry} 行业重合度 {overlap:.1f}% > 15%，须替换其一"
                    )


def _check_budget_balance(rec: dict, failures: list):
    """约束二：定投金额 ≤ 月净储蓄额。"""
    monthly = rec.get("monthly_savings", 0)
    if monthly <= 0:
        warnings = []  # noqa: F841
        return

    for f in rec.get("funds", []):
        amount = f.get("amount", 0)
        # 定投金额通常按月计算
        if f.get("is_dca", True) and amount > monthly:
            # 检查是否触发加倍定投
            vp = rec.get("valuation_percentile", 0.5)
            if vp < 0.1:
                excess = amount - monthly
                idle_cash = rec.get("idle_cash_flow", 0)
                months = int(idle_cash / excess) if excess > 0 else 0
                if months < 1:
                    failures.append(
                        f"[预算硬平衡] {f.get('name','?')} 定投 ¥{amount}/月 "
                        f"> 月净储蓄 ¥{monthly}，且存量现金流不足以支撑加倍定投"
                    )
                # 否则为警告（有超额来源但需标注）
            else:
                failures.append(
                    f"[预算硬平衡] {f.get('name','?')} 定投 ¥{amount}/月 "
                    f"> 月净储蓄 ¥{monthly}，超出预算"
                )


def _check_allocation_closed_loop(rec: dict, failures: list):
    """约束三：第四步实际比例必须匹配第二步目标比例（误差≤5%）。"""
    target = rec.get("target_allocation", {})
    actual = rec.get("actual_allocation", {})
    if not target or not actual:
        return  # 无数据时不强制

    for asset in ("stock", "bond", "cash"):
        t = target.get(asset, 0)
        a = actual.get(asset, 0)
        if abs(t - a) > 0.05:
            label = {"stock": "股票", "bond": "债券", "cash": "现金"}[asset]
            failures.append(
                f"[配置闭环] {label}比例目标 {t:.0%} vs 实际 {a:.0%}，偏差 >5%"
            )


def _check_commonsense(rec: dict, warnings: list):
    """约束四：PE/PB 常识校验。"""
    for metric, (lo, hi, desc) in COMMONSENSE_RANGES.items():
        val = rec.get(metric)
        if val is not None and (val < lo or val > hi):
            warnings.append(
                f"[常识校验] {desc}，当前值={val}，显著偏离历史区间"
            )


def _check_financial_health(rec: dict, warnings: list):
    """约束五：财务健康预检。"""
    if not rec.get("has_emergency_fund", True):
        warnings.append("[财务预检] 未确认应急金，建议先存满3个月生活费")
    if rec.get("has_high_interest_debt", False):
        warnings.append("[财务预检] 存在高息负债，建议优先偿还利率>8%债务")
    if not rec.get("has_insurance", True):
        warnings.append("[财务预检] 未确认基础保险，建议先配置医疗/重疾/意外")


def _check_fee_transparency(rec: dict, failures: list):
    """约束六：费率穿透。"""
    for f in rec.get("funds", []):
        if f.get("fee_total") is None:
            failures.append(
                f"[费率穿透] {f.get('name','?')} 未披露总费率，禁止推荐收费模糊产品"
            )


def _check_rebalancing(rec: dict, warnings: list):
    """约束七：再平衡机制。"""
    if not rec.get("rebalancing_rule"):
        warnings.append("[再平衡] 未设定再平衡触发条件与回顾频率")


def _check_disclaimer(rec: dict, warnings: list):
    """约束八（部分）：免责声明 + 历史交叉验证提示。"""
    if not rec.get("disclaimers"):
        warnings.append("[合规] 输出缺少免责声明")


def main():
    """CLI 演示：对示例推荐执行校验。"""
    sample = {
        "funds": [
            {"code": "110011", "name": "易方达中小盘", "industry_alloc": {"制造业": 30, "金融": 15}, "fee_total": 1.5, "amount": 2000, "is_dca": True},
            {"code": "000001", "name": "华夏成长", "industry_alloc": {"制造业": 25, "科技": 20}, "fee_total": 1.2, "amount": 1500, "is_dca": True},
        ],
        "monthly_savings": 3000,
        "total_investment": 50000,
        "target_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "actual_allocation": {"stock": 0.7, "bond": 0.2, "cash": 0.1},
        "valuation_percentile": 0.25,
        "has_emergency_fund": True,
        "has_high_interest_debt": False,
        "has_insurance": True,
        "rebalancing_rule": "季度回顾，偏离>10%触发",
        "disclaimers": ["不构成投资建议"],
    }
    result = validate_constraints(sample)
    print(f"校验结果: {'通过' if result['passed'] else '不通过'}")
    for f in result["failures"]:
        print(f"  ❌ {f}")
    for w in result["warnings"]:
        print(f"  ⚠️ {w}")


if __name__ == "__main__":
    main()
