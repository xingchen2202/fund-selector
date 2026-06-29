#!/usr/bin/env python3
"""
generate_recommend.py — 整合所有数据，生成推荐报告
━━━━━━━━━━━━━━━━━━━━
支持两种模式：
  1. --pipeline: 从 _pipeline_data.json 读取完整数据（默认）
  2. <data_json_file>: 从指定 JSON 文件读取（向后兼容）
"""
import json
import sys
import io
from datetime import datetime
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
REPORTS_DIR = SKILL_DIR.parent.parent.parent / "fund-reports"
PIPELINE_FILE = REPORTS_DIR / "_pipeline_data.json"


def read_pipeline():
    """读取 pipeline 数据总线"""
    if PIPELINE_FILE.exists():
        with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


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

    # 最终候选基金（合并 validated_funds + var_impacts + news）
    candidates = data.get("candidates", [])
    validated_funds = data.get("validated_funds", {})
    var_impacts = data.get("var_impacts", {})
    news_data = data.get("news", {})

    lines.append(f"【最终候选基金】（{len(candidates)} 只）")
    lines.append("━" * 40)

    for c in candidates:
        code = c.get("code", "N/A")
        name = c.get("name", "未知")

        # 从 validated_funds 获取详细数据
        fund_detail = {}
        if isinstance(validated_funds, dict):
            # 支持两种结构：{"verified": [{...}, ...]} 或 {code: {...}}
            verified_list = validated_funds.get("verified", [])
            if isinstance(verified_list, list):
                for f in verified_list:
                    if f.get("code") == code:
                        fund_detail = f
                        break
            elif isinstance(verified_list, dict):
                fund_detail = verified_list.get(code, {})

        # 从 var_impacts 获取 VaR 数据
        var_info = var_impacts.get(code, {}) if isinstance(var_impacts, dict) else {}

        # 从 news 获取新闻数据
        news_info = news_data.get(code, {}) if isinstance(news_data, dict) else {}

        lines.append(f"▌ {name}（{code}）")
        lines.append(f"[数据层]")
        scale = fund_detail.get("scale_wan")
        scale_str = f"{scale / 10000:.2f} 亿" if scale else "N/A"
        lines.append(f"  规模：{scale_str} 经理：{fund_detail.get('manager') or '待补充'} | 总费率：{fund_detail.get('fee') or '待补充'}")

        # P4修复：收益标注使用正确的标签
        return_1y = fund_detail.get("return_1y")
        return_1y_label = fund_detail.get("return_1y_label", "近1年")
        if return_1y is None:
            return_1y_str = "待补充"
        elif isinstance(return_1y, str):
            return_1y_str = return_1y
        else:
            return_1y_str = f"{return_1y:+.2f}%"

        return_3y = fund_detail.get("return_3y")
        return_3y_label = fund_detail.get("return_3y_label", "近3年")
        if return_3y is None:
            return_3y_str = "待补充"
        elif isinstance(return_3y, str):
            return_3y_str = return_3y
        else:
            return_3y_str = f"{return_3y:+.2f}%"

        lines.append(f"  {return_1y_label}：{return_1y_str} | {return_3y_label}：{return_3y_str} | 最大回撤：{fund_detail.get('max_drawdown') or '待补充'}")

        # P4修复：如果有成立日期，显示在分析层
        est_date = fund_detail.get("establishment_date")
        age_years = fund_detail.get("age_years")
        age_months = fund_detail.get("age_months")
        lines.append(f"[分析层]")
        base_info = f"  板块：{c.get('sector', '未知')} | 综合评分：{c.get('score', 'N/A')}"
        if est_date and age_years is not None:
            base_info += f" | 成立于{est_date}（{age_years}年{age_months}月）"
        lines.append(base_info)
        lines.append(f"[VaR 影响]")
        marginal_var = var_info.get("marginal_var", "N/A")
        lines.append(f"  加入 5% 仓位预计增加 VaR：{marginal_var} 元")
        lines.append(f"[新闻背景]")
        bullish = news_info.get("bullish", "无")
        bearish = news_info.get("bearish", "无")
        lines.append(f"  利多：{bullish}")
        lines.append(f"  利空：{bearish}")

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
    use_pipeline = False
    data_file = None

    # 解析命令行参数
    if "--pipeline" in sys.argv:
        use_pipeline = True
    elif len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
        data_file = Path(sys.argv[1])

    if use_pipeline:
        # 从数据总线读取
        if not PIPELINE_FILE.exists():
            print(json.dumps({"error": f"pipeline 文件不存在: {PIPELINE_FILE}"}))
            print("[提示] 请先运行 screen_candidates.py 和 validate_funds.py", file=sys.stderr)
            sys.exit(1)
        with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[INFO] 从 pipeline 读取数据，keys: {list(data.keys())}", file=sys.stderr)
    elif data_file:
        # 从指定文件读取（向后兼容）
        if not data_file.exists():
            print(json.dumps({"error": f"数据文件不存在: {data_file}"}))
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
    output_path = REPORTS_DIR / f"recommend_{date_str}.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    # 输出到 stdout
    print(report)
    print(f"\n[报告已保存: {output_path}]")


if __name__ == "__main__":
    main()
