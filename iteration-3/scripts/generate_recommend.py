#!/usr/bin/env python3
"""
generate_recommend.py — 合并所有步骤数据，生成推荐报告
━━━━━━━━━━━━━━━━━━━━
从独立步骤文件读取数据，合并后：
  1. 限制最终推荐不超过3只
  2. 相同策略的A/C/E份额只保留评分最高的一只
  3. 生成结构化报告并保存
"""
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
REPORTS_DIR = SKILL_DIR.parent.parent.parent / "fund-reports"


def read_all_steps():
    """读取所有步骤文件并合并"""
    merged = {}
    step_files = [
        REPORTS_DIR / "_pipeline_step0_constraints.json",
        REPORTS_DIR / "_pipeline_step1_macro.json",
        REPORTS_DIR / "_pipeline_step2_candidates.json",
        REPORTS_DIR / "_pipeline_step3_funds.json",
        REPORTS_DIR / "_pipeline_step3_akshare.json",
        REPORTS_DIR / "_pipeline_step4_var.json",
        REPORTS_DIR / "_pipeline_step5_news.json",
    ]
    for path in step_files:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    merged.update(data)
            except Exception:
                pass
    return merged


def deduplicate_share_classes(candidates):
    """
    P6修复：相同策略的A/C/E份额只保留综合评分最高的一只。
    识别方法：基金名称去除份额后缀（A/C/E）后相同则视为同一策略。
    """
    from collections import OrderedDict

    groups = OrderedDict()
    for c in candidates:
        name = c.get("name", "")
        # 去除份额后缀得到策略名
        strategy = name.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        if strategy not in groups:
            groups[strategy] = []
        groups[strategy].append(c)

    deduped = []
    for strategy, funds in groups.items():
        # 按评分降序，取最高分的一只
        best = max(funds, key=lambda x: x.get("score") or 0)
        deduped.append(best)

    return deduped


def limit_candidates(candidates, max_count=3):
    """P6修复：限制最终推荐数量"""
    # 按综合评分降序排列
    sorted_candidates = sorted(
        candidates,
        key=lambda x: x.get("score") or 0,
        reverse=True
    )
    return sorted_candidates[:max_count]


def generate_report(data: dict) -> str:
    """生成报告文本"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    lines = []

    lines.append("=== 基金筛选参考报告 {} ===".format(date_str))
    lines.append("")

    # 当前组合约束
    constraints = data.get("constraints", {})
    lines.append("【当前组合约束】")
    total_value = constraints.get("total_value", "N/A")
    if total_value != "N/A" and total_value is not None:
        lines.append("总市值：{:,.2f} 元".format(total_value))
    else:
        lines.append("总市值：N/A 元")
    var_budget = constraints.get("var_budget_remaining", constraints.get("var_budget", "N/A"))
    lines.append("VaR 预算剩余：{} 元".format(var_budget))
    overloaded = constraints.get("overloaded_sectors", {})
    if overloaded:
        over_str = ", ".join("{}（{}%）".format(k, v) for k, v in overloaded.items())
        lines.append("已超配（本次不推荐新增）：{}".format(over_str))
    lines.append("")

    # 宏观环境
    macro = data.get("macro", {})
    lines.append("【宏观环境】")
    cycle = macro.get("cycle_judgment", {})
    phase = cycle.get("phase", "未知")
    confidence = cycle.get("confidence", "N/A")
    lines.append("周期判断：{}（置信度：{}）".format(phase, confidence))
    available = macro.get("available_indicators", [])
    unavailable = macro.get("unavailable_indicators", [])
    if available:
        lines.append("可用指标：{}".format(", ".join(available)))
    if unavailable:
        lines.append("不可用指标：{}".format(", ".join(unavailable)))
    lines.append("")

    # 最终候选基金（合并 validated_funds + var_impacts + news）
    candidates = data.get("candidates") or data.get("top10") or []
    validated_funds = data.get("validated_funds", {})
    var_impacts = data.get("var_impacts", {})
    news_data = data.get("news", {})

    # P6修复：去重 A/C/E 份额，限制3只
    candidates = deduplicate_share_classes(candidates)
    candidates = limit_candidates(candidates, max_count=3)

    lines.append("【最终候选基金】（{} 只）".format(len(candidates)))
    lines.append("━" * 40)

    for c in candidates:
        code = c.get("code", "N/A")
        name = c.get("name", "未知")

        # 从 validated_funds 获取详细数据
        fund_detail = {}
        if isinstance(validated_funds, dict):
            verified_list = validated_funds.get("verified", [])
            if isinstance(verified_list, list):
                for f in verified_list:
                    if f.get("code") == code:
                        fund_detail = f
                        break

        # 从 var_impacts 获取 VaR 数据
        var_info = var_impacts.get(code, {}) if isinstance(var_impacts, dict) else {}

        # 从 news 获取新闻数据
        news_info = news_data.get(code, {}) if isinstance(news_data, dict) else {}

        lines.append("▌ {}（{}）".format(name, code))
        lines.append("[数据层]")
        scale = fund_detail.get("scale_wan")
        if scale is not None:
            if scale >= 10000:
                scale_str = "{:.2f} 亿".format(scale / 10000)
            else:
                scale_str = "{:.2f} 万".format(scale)
        else:
            scale_str = "N/A"
        lines.append("  规模：{} 经理：{} | 总费率：{}".format(
            scale_str,
            fund_detail.get("manager") or "待补充",
            fund_detail.get("fee") or "待补充"
        ))

        # 收益标签
        return_1y = fund_detail.get("return_1y")
        return_1y_label = fund_detail.get("return_1y_label", "近1年")
        if return_1y is None:
            return_1y_str = "待补充"
        elif isinstance(return_1y, str):
            return_1y_str = return_1y
        else:
            return_1y_str = "{:+.2f}%".format(return_1y)

        return_3y = fund_detail.get("return_3y")
        return_3y_label = fund_detail.get("return_3y_label", "近3年")
        if return_3y is None:
            return_3y_str = "待补充"
        elif isinstance(return_3y, str):
            return_3y_str = return_3y
        else:
            return_3y_str = "{:+.2f}%".format(return_3y)

        lines.append("  {}：{} | {}：{} | 最大回撤：{}".format(
            return_1y_label, return_1y_str,
            return_3y_label, return_3y_str,
            fund_detail.get("max_drawdown") or "待补充"
        ))
        lines.append("[分析层]")
        est_date = fund_detail.get("establishment_date")
        age_years = fund_detail.get("age_years")
        age_months = fund_detail.get("age_months")
        base_info = "  板块：{} | 综合评分：{}".format(
            c.get("sector", "未知"),
            c.get("score", "N/A")
        )
        if est_date and age_years is not None:
            base_info += " | 成立于{}（{}年{}月）".format(est_date, age_years, age_months)
        lines.append(base_info)
        lines.append("[VaR 影响]")
        marginal_var = var_info.get("marginal_var", "N/A")
        lines.append("  加入 5% 仓位预计增加 VaR：{} 元".format(marginal_var))
        lines.append("[新闻背景]")
        bullish = news_info.get("bullish", "无")
        bearish = news_info.get("bearish", "无")
        lines.append("  利多：{}".format(bullish))
        lines.append("  利空：{}".format(bearish))

        if c.get("perilla"):
            lines.append("[紫苏叶视角]")
            lines.append("  {}".format(c["perilla"]))

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
    lines.append("- 新闻来源：AKShare（东方财富/新闻联播）+ Tavily（备用）")
    lines.append("- 持仓数据滞后：一个季度")
    lines.append("- 本报告不构成投资建议")
    lines.append("")

    lines.append("=== 报告结束 ===")

    return "\n".join(lines)


def main():
    use_pipeline = False
    data_file = None

    # 解析命令行参数
    if "--pipeline" in sys.argv:
        use_pipeline = True
    elif len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
        data_file = Path(sys.argv[1])

    if use_pipeline:
        # 从独立步骤文件读取并合并
        data = read_all_steps()
        if not data:
            print(json.dumps({"error": "无步骤数据文件，请先运行流水线脚本"}))
            sys.exit(1)
        print("[INFO] 从步骤文件合并数据，keys: {}".format(list(data.keys())), file=sys.stderr)
    elif data_file:
        if not data_file.exists():
            print(json.dumps({"error": "数据文件不存在: {}".format(data_file)}))
            sys.exit(1)
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        print(json.dumps({"error": "用法: generate_recommend.py --pipeline | generate_recommend.py <data_json_file>"}))
        sys.exit(1)

    report = generate_report(data)

    # 保存文件
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    output_path = REPORTS_DIR / "recommend_{}.txt".format(date_str)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    # 输出到 stdout
    print(report)
    print("\n[报告已保存: {}]".format(output_path))


if __name__ == "__main__":
    main()
