#!/usr/bin/env python3
"""
generate_recommend.py — 合并所有步骤数据，生成推荐报告
━━━━━━━━━━━━━━━━━━━━
从5个独立步骤文件读取数据，合并后：
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


def _load_rejection():
    """加载快否决清单结果文件（如果存在）。"""
    path = REPORTS_DIR / "_pipeline_rejection.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def read_all_steps():
    """读取所有步骤文件并合并"""
    merged = {}
    step_files = [
        REPORTS_DIR / "_pipeline_step0.json",
        REPORTS_DIR / "_pipeline_step1.json",   # P5: Claude MCP 宏观数据
        REPORTS_DIR / "_pipeline_step2.json",
        REPORTS_DIR / "_pipeline_step3.json",   # P5: Claude MCP 基金验证
        REPORTS_DIR / "_pipeline_step4.json",
        REPORTS_DIR / "_pipeline_step5.json",
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

    lines.append(f"=== 基金筛选参考报告 {date_str} ===")
    lines.append("")

    # 当前组合约束 — step0 数据在顶层
    lines.append("【当前组合约束】")
    total_value = data.get("total_value", "N/A")
    if total_value != "N/A" and total_value is not None:
        lines.append(f"总市值：{total_value:,.2f} 元")
    else:
        lines.append("总市值：N/A 元")
    var_budget = data.get("var_budget_remaining", data.get("var_budget", "N/A"))
    lines.append(f"VaR 预算剩余：{var_budget} 元")
    overloaded = data.get("overloaded_sectors", {})
    if overloaded:
        over_str = ", ".join(f"{k}（{v}%）" for k, v in overloaded.items())
        lines.append(f"已超配（本次不推荐新增）：{over_str}")
    lines.append("")

    # 宏观环境 — P5修复：支持新 step1 格式（数据在顶层）
    lines.append("【宏观环境】")
    # 新格式：cycle_judgment 和 cycle_confidence 在顶层（来自 step1）
    cycle_judgment = data.get("cycle_judgment")
    cycle_confidence = data.get("cycle_confidence")
    if cycle_judgment and cycle_confidence:
        lines.append(f"周期判断：{cycle_judgment}（置信度：{cycle_confidence}）")
    else:
        # 兼容旧格式（嵌套在 macro 中）
        macro = data.get("macro", {})
        cycle = macro.get("cycle_judgment", {})
        if isinstance(cycle, dict):
            lines.append(f"周期判断：{cycle.get('phase', '未知')}（置信度：{cycle.get('confidence', 'N/A')}）")
        else:
            lines.append(f"周期判断：未知（置信度：N/A）")
    # 可用/不可用指标
    available = data.get("available_indicators", [])
    unavailable = data.get("unavailable_indicators", [])
    if available:
        lines.append(f"可用指标：{', '.join(available)}")
    if unavailable:
        lines.append(f"不可用指标：{', '.join(unavailable)}")
    lines.append("")

    # 最终候选基金（合并 validated_funds + var_impacts + news）
    # step2 可能写入 "candidates" 或 "top10"
    candidates = data.get("candidates") or data.get("top10") or []
    validated_funds = data.get("validated_funds", {})
    var_impacts = data.get("var_impacts", {})
    news_data = data.get("news", {})

    # 【移植 ai-berkshire】消费快否决清单结果：被 R1-R6 否决的基金直接剔除
    rejection_data = data.get("rejection") or _load_rejection()
    rejected_codes = set()
    rejected_details = []
    if rejection_data:
        for r in rejection_data.get("rejected", []):
            rejected_codes.add(r.get("code"))
            triggered = ",".join(r.get("triggered", []))
            rejected_details.append(f"{r.get('code')} {r.get('name', '')} [R{triggered}]")
    if rejected_codes:
        before = len(candidates)
        candidates = [c for c in candidates if c.get("code") not in rejected_codes]
        print(f"[REJECTION] 快否决剔除 {before - len(candidates)} 只: {', '.join(rejected_details)}",
              file=sys.stderr)

    # P7修复：在限制数量前先按最大回撤过滤
    # 导入 validate_funds.py 的过滤函数（如果可用）
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from validate_funds import determine_fund_type, extract_drawdown, should_exclude_by_drawdown
        _drawdown_filter_available = True
    except ImportError:
        _drawdown_filter_available = False

    if _drawdown_filter_available:
        filtered_candidates = []
        for c in candidates:
            code = c.get("code", "")
            name = c.get("name", "")
            fund_detail = {}
            for f in validated_funds:
                if f.get("code") == code:
                    fund_detail = f
                    break

            fund_type = determine_fund_type(fund_detail)
            # 优先使用 drawdown_display（validate_funds.py 已计算），否则从原始数据提取
            nav_data = fund_detail.get("nav_series") or fund_detail.get("max_drawdown")
            drawdown_3y, drawdown_inception, label = extract_drawdown(nav_data, fund_type)

            should_exclude, reason = should_exclude_by_drawdown(drawdown_3y, label, fund_type)
            if should_exclude:
                print(f"[EXCLUDE] {code} {name} {reason}", file=sys.stderr)
                continue

            # 标注回撤展示字段
            c["_drawdown_display"] = f"{drawdown_3y:.1%}（{label}）" if drawdown_3y is not None else "数据缺失"
            c["_drawdown_inception"] = f"{drawdown_inception:.1%}（成立以来）" if drawdown_inception is not None else "数据缺失"
            filtered_candidates.append(c)
        candidates = filtered_candidates

    # P6修复：去重 A/C/E 份额，限制3只
    candidates = deduplicate_share_classes(candidates)
    candidates = limit_candidates(candidates, max_count=3)

    lines.append(f"【最终候选基金】（{len(candidates)} 只）")
    lines.append("━" * 40)

    for c in candidates:
        code = c.get("code", "N/A")
        name = c.get("name", "未知")

        # 从 validated_funds 获取详细数据
        # P5修复：支持新格式（直接列表）和旧格式（嵌套在 verification 中）
        fund_detail = {}
        if isinstance(validated_funds, list):
            # 新格式：validated_funds 直接是列表
            for f in validated_funds:
                if f.get("code") == code:
                    fund_detail = f
                    break
        elif isinstance(validated_funds, dict):
            # 旧格式：嵌套在 verified/verification 中
            verified_list = validated_funds.get("verified") or validated_funds.get("verified", [])
            if isinstance(verified_list, list):
                for f in verified_list:
                    if f.get("code") == code:
                        fund_detail = f
                        break

        # 从 var_impacts 获取 VaR 数据
        var_info = var_impacts.get(code, {}) if isinstance(var_impacts, dict) else {}

        # 从 news 获取新闻数据
        news_info = news_data.get(code, {}) if isinstance(news_data, dict) else {}

        lines.append(f"▌ {name}（{code}）")
        lines.append(f"[数据层]")
        # P5修复：支持 scale + scale_unit 新格式
        scale = fund_detail.get("scale")
        scale_unit = fund_detail.get("scale_unit", "亿")
        if scale is not None:
            scale_str = f"{scale:.2f} {scale_unit}"
        else:
            # 兼容旧格式 scale_wan
            scale_wan = fund_detail.get("scale_wan")
            if scale_wan is not None:
                scale_str = f"{scale_wan / 10000:.2f} 亿"
            else:
                scale_str = "N/A"
        lines.append(f"  规模：{scale_str} 经理：{fund_detail.get('manager') or '数据缺失'} | 总费率：{fund_detail.get('fee_total') or fund_detail.get('fee') or '数据缺失'}")

        # 收益标签 — P5修复：兼容 return_1y_label 和 return_label
        return_1y = fund_detail.get("return_1y")
        return_1y_label = fund_detail.get("return_1y_label") or fund_detail.get("return_label", "近1年")
        if return_1y is None:
            return_1y_str = "数据缺失"
        elif isinstance(return_1y, str):
            return_1y_str = return_1y
        else:
            return_1y_str = f"{return_1y:+.2f}%"

        return_3y = fund_detail.get("return_3y")
        return_3y_label = fund_detail.get("return_3y_label", "近3年")
        if return_3y is None:
            # 成立不满3年：显示成立以来收益（P5修复：杜绝"待补充"占位符）
            since_val = fund_detail.get("return_since_inception")
            age_years = fund_detail.get("age_years")
            age_months = fund_detail.get("age_months")
            if since_val is not None and age_years is not None:
                return_3y_label = f"成立以来（{age_years}年{age_months}月）"
                return_3y_str = f"{since_val:+.2f}%"
            elif age_years is not None:
                # 年龄可算但成立以来总值缺失：回退到近1年+年龄说明，绝不显示字面占位符
                fallback_1y = f"{return_1y:+.2f}%" if isinstance(return_1y, (int, float)) else (return_1y or "")
                return_3y_label = f"近1年（成立{age_years}年{age_months}月，成立以来总值暂缺）"
                return_3y_str = fallback_1y or "参见近1年"
            else:
                # 年龄也算不出：完全无数据
                return_3y_label = "近1年"
                return_3y_str = f"{return_1y:+.2f}%" if isinstance(return_1y, (int, float)) else (return_1y or "数据缺失")
        elif isinstance(return_3y, str):
            return_3y_str = return_3y
        else:
            return_3y_str = f"{return_3y:+.2f}%"

        # 最大回撤 — P7修复：标注时间范围
        max_dd = fund_detail.get("max_drawdown")
        drawdown_display = c.get("_drawdown_display")
        drawdown_inception = c.get("_drawdown_inception")

        if drawdown_display and drawdown_display != "数据缺失":
            max_dd_str = drawdown_display
        elif max_dd is not None:
            max_dd_str = f"{max_dd:+.2f}%"
        else:
            max_dd_str = "数据缺失"
        # 如果有成立以来回撤且与近3年不同，附加显示
        if (drawdown_inception and drawdown_inception != "数据缺失"
                and drawdown_display and drawdown_display != "数据缺失"
                and drawdown_inception != drawdown_display):
            max_dd_str = f"{max_dd_str} | 成立以来：{drawdown_inception}"

        lines.append(f"  {return_1y_label}：{return_1y_str} | {return_3y_label}：{return_3y_str} | 最大回撤：{max_dd_str}")
        lines.append(f"[分析层]")
        est_date = fund_detail.get("establishment_date")
        age_years = fund_detail.get("age_years")
        age_months = fund_detail.get("age_months")
        base_info = f"  板块：{c.get('sector', '未知')} | 综合评分：{c.get('score', 'N/A')}"
        if est_date and age_years is not None:
            base_info += f" | 成立于{est_date}（{age_years}年{age_months}月）"
        lines.append(base_info)
        lines.append(f"[VaR 影响]")
        # P8修复：使用 calc_var_impact.py 计算的 var_display（含真实波动率）
        var_display = var_info.get("var_display")
        if var_display:
            lines.append(f"  加入 5% 仓位预计增加 VaR：{var_display}")
        else:
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
    lines.append("- 新闻来源：AKShare（东方财富）")
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
        # P6修复：从独立步骤文件读取并合并
        data = read_all_steps()
        if not data:
            print(json.dumps({"error": "无步骤数据文件，请先运行流水线脚本"}))
            sys.exit(1)
        print(f"[INFO] 从步骤文件合并数据，keys: {list(data.keys())}", file=sys.stderr)
    elif data_file:
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
