#!/usr/bin/env python3
"""
generate_recommend.py — 整合所有数据，生成推荐报告
━━━━━━━━━━━━━━━━━━━━
将 Step 0-6 的输出整合为结构化报告并保存。
"""
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
REPORTS_DIR = SKILL_DIR.parent.parent / "fund-reports"


def generate_report(data: dict) -> str:
    """生成报告文本"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    lines = []

    lines.append(f"=== 基金筛选参考报告 {date_str} ===")
    lines.append("")

    # 当前组合约束
    constraints = data.get("constraints", {})
    lines.append("【当前组合约束】")
    lines.append(f"总市值：{constraints.get('total_value', 'N/A')} 元")
    lines.append(f"VaR 预算剩余：{constraints.get('var_budget', 'N/A')} 元")
    overloaded = constraints.get("overloaded_sectors", {})
    if overloaded:
        over_str = ", ".join(f"{k}（{v}%）" for k, v in overloaded.items())
        lines.append(f"已超配（本次不推荐新增）：{over_str}")
    lines.append("")

    # 宏观环境
    macro = data.get("macro", {})
    lines.append("【宏观环境】")
    cycle = macro.get("cycle_judgment", {})
    lines.append(f"周期判断：{cycle.get('phase', '未知')}（置信度：{cycle.get('confidence', 'N/A')}）")
    available = macro.get("available_indicators", [])
    unavailable = macro.get("unavailable_indicators", [])
    if available:
        lines.append(f"可用指标：{', '.join(available)}")
    if unavailable:
        lines.append(f"不可用指标：{', '.join(unavailable)}")
    lines.append("")

    # 最终候选基金
    candidates = data.get("candidates", [])
    lines.append(f"【最终候选基金】（{len(candidates)} 只）")
    lines.append("━" * 40)

    for c in candidates:
        lines.append(f"▌ {c.get('name', '未知')}（{c.get('code', 'N/A')}）")
        lines.append(f"[数据层]")
        lines.append(f"  规模：{c.get('scale', 'N/A')} 亿 | 经理：{c.get('manager', 'N/A')} | 总费率：{c.get('fee', 'N/A')}")
        lines.append(f"  近 1 年：{c.get('return_1y', 'N/A')} | 近 3 年：{c.get('return_3y', 'N/A')} | 最大回撤：{c.get('max_drawdown', 'N/A')}")
        lines.append(f"[分析层]")
        lines.append(f"  {c.get('analysis', '无分析数据')}")
        lines.append(f"[VaR 影响]")
        lines.append(f"  加入 5% 仓位预计增加 VaR：{c.get('marginal_var', 'N/A')} 元")
        lines.append(f"[新闻背景]")
        lines.append(f"  利多：{c.get('bullish_news', '无')}")
        lines.append(f"  利空：{c.get('bearish_news', '无')}")

        if c.get("perilla"):
            lines.append(f"[紫苏叶视角]")
            lines.append(f"  {c['perilla']}")

        lines.append("")

    # 需要自己判断的
    lines.append("【你需要自己判断的】")
    lines.append("- 现在买还是等：AI 无法判断，这是你的决定")
    lines.append("- 买入金额：建议不超过单次定投的 2 倍")
    lines.append("- 是否先止盈现有持仓再买入")
    lines.append("")

    # 数据说明
    lines.append("【数据说明】")
    lines.append("- 基金数据来源：cn-mutual-fund MCP（AKShare）")
    lines.append("- 新闻来源：Tavily（如可用）")
    lines.append("- 持仓数据滞后：一个季度")
    lines.append("- 本报告不构成投资建议")
    lines.append("")
    lines.append("=== 报告结束 ===")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "用法: generate_recommend.py <data_json_file>"}))
        sys.exit(1)

    data_file = Path(sys.argv[1])
    if not data_file.exists():
        print(json.dumps({"error": f"数据文件不存在: {data_file}"}))
        sys.exit(1)

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    report = generate_report(data)

    # 保存文件
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    output_path = REPORTS_DIR / f"recommend_{date_str}.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    # 输出到 stdout
    print(report)
    print(f"\n[报告已保存: {output_path}]")


if __name__ == "__main__":
    main()
