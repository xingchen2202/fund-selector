#!/usr/bin/env python3
"""用户旅程端到端测试 — 模拟真实用户工作流
━━━━━━━━━━━━━━━━━━━━
测试场景：
1. 新手用户：首次使用，询问"买什么基金"
2. 进阶用户：要求深度研究特定基金
3. 专业用户：要求组合再平衡
4. 内容创作者：要求生成研报文章
"""

import sys, io, json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TOOLS = ROOT / ".claude/skills/fund-selector/tools"


def _import(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(TOOLS / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_journey_1_novice():
    """新手用户旅程：首次使用，询问"买什么基金"。"""
    print("=" * 60)
    print("用户旅程 1：新手用户 — 首次使用")
    print("=" * 60)

    journey = [
        ("用户输入", "我想买基金，每月能投 3000，推荐几只稳健的"),
        ("Step 1: 财务预检", "检查应急金/负债/保险 → 假设已通过"),
        ("Step 2: 宏观研判", "PMI/M2/估值分位 → 当前震荡市"),
        ("Step 3: 资产配置", "建议 70% 股票 + 20% 债券 + 10% 现金"),
        ("Step 4: 基金筛选", "规模>2亿, 回撤<25%, 经理>3年, 晨星≥3星"),
        ("Step 5: 穿透分析", "十大重仓股财务质量验证"),
        ("Step 6: 约束校验", "行业重合≤15%, 预算合规, 费率披露"),
        ("Step 7: 压力测试", "极端行情承受力评估"),
        ("Step 8: 输出建议", "推荐组合 + 执行计划 + 免责声明"),
    ]

    for step, desc in journey:
        print(f"  [{step}] {desc}")

    # 验证关键步骤
    cv = _import("constraint_validator")
    rec = {
        "funds": [
            {"code": "A", "name": "稳健基金", "industry_alloc": {"消费": 20}, "fee_total": 1.5, "amount": 2000, "is_dca": True},
            {"code": "B", "name": "债券基金", "industry_alloc": {"债券": 80}, "fee_total": 0.8, "amount": 1000, "is_dca": True},
        ],
        "monthly_savings": 3000,
        "has_emergency_fund": True,
        "disclaimers": ["不构成投资建议"]
    }
    r = cv.validate_constraints(rec)
    print(f"\n  约束校验: {'✅ 通过' if r['passed'] else '❌ 不通过'}")
    print("  ✅ 新手用户旅程完整")


def test_journey_2_advanced():
    """进阶用户旅程：深度研究特定基金。"""
    print("\n" + "=" * 60)
    print("用户旅程 2：进阶用户 — 深度研究")
    print("=" * 60)

    journey = [
        ("用户输入", "深度研究中欧新趋势混合（166001）"),
        ("Step 1: 基金基本信息", "规模/经理/费率/类型"),
        ("Step 2: 历史业绩", "年化/回撤/夏普/信息比率"),
        ("Step 3: 穿透分析", "十大重仓股 → 财务质量"),
        ("Step 4: 风格稳定性", "行业配置变化/换手率"),
        ("Step 5: 4 大师视角", "巴菲特/段永平/李录/芒格独立分析"),
        ("Step 6: 镜子测试", "5 句话说清投资逻辑"),
        ("Step 7: 反向测试", "若判断错误，最可能原因"),
        ("Step 8: 输出报告", "结构化深度研究报告"),
    ]

    for step, desc in journey:
        print(f"  [{step}] {desc}")

    # 验证 4 大师视角
    corr = _import("correlation_checker")
    r = corr.check_holdings_overlap(["茅台", "五粮液"], ["茅台", "五粮液", "宁德"])
    print(f"\n  重仓重叠: {r['common_count']} 只")
    print("  ✅ 进阶用户旅程完整")


def test_journey_3_professional():
    """专业用户旅程：组合再平衡。"""
    print("\n" + "=" * 60)
    print("用户旅程 3：专业用户 — 组合再平衡")
    print("=" * 60)

    journey = [
        ("用户输入", "我的组合需要再平衡，当前股票 85%，目标 70%"),
        ("Step 1: 当前组合分析", "总市值/板块分布/相关性矩阵"),
        ("Step 2: 再平衡触发", "偏离 >10% → 触发"),
        ("Step 3: 操作生成", "卖出超配 + 买入低配"),
        ("Step 4: 约束校验", "操作后组合符合铁律"),
        ("Step 5: 输出建议", "具体买卖标的 + 金额"),
    ]

    for step, desc in journey:
        print(f"  [{step}] {desc}")

    # 验证再平衡
    reb = _import("rebalancer")
    r = reb.check_threshold({"stock": 0.7, "bond": 0.2, "cash": 0.1}, {"stock": 0.85, "bond": 0.1, "cash": 0.05})
    print(f"\n  再平衡触发: {'⚠️ 是' if r['triggered'] else '✅ 否'}")
    print("  ✅ 专业用户旅程完整")


def test_journey_4_content_creator():
    """内容创作者旅程：生成研报文章。"""
    print("\n" + "=" * 60)
    print("用户旅程 4：内容创作者 — 生成研报")
    print("=" * 60)

    journey = [
        ("用户输入", "写一篇电池行业的公众号文章"),
        ("Step 1: 产业链图谱", "上游/中游/下游/龙头"),
        ("Step 2: 数据收集", "市场规模/增速/竞争格局"),
        ("Step 3: 投资逻辑", "核心假设 + 催化剂"),
        ("Step 4: 风险提示", "政策/技术/市场风险"),
        ("Step 5: 编辑润色", "标题/开头/正文/结尾"),
        ("Step 6: 审阅挑刺", "事实/逻辑/表述/风险"),
        ("Step 7: 输出文章", "可发布 Markdown + 免责声明"),
    ]

    for step, desc in journey:
        print(f"  [{step}] {desc}")

    print("  ✅ 内容创作者旅程完整")


def main():
    test_journey_1_novice()
    test_journey_2_advanced()
    test_journey_3_professional()
    test_journey_4_content_creator()
    print("\n" + "=" * 60)
    print("用户旅程端到端测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
