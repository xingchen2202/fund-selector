#!/usr/bin/env python3
"""
generate_report.py — 生成基金持仓周报
━━━━━━━━━━━━━━━━━━━━
整合净值数据、盈亏计算、新闻搜索、规则检查，
生成完整的文字报告并保存到 fund-reports/ 目录。

用法:
    python generate_report.py <pnl_json_path> <news_json_path> <alerts_json_path> <output_dir>

输出:
    report_YYYYMMDD.txt — 完整周报文件
    stdout — 报告文本（供对话内展示）

退出码:
    0 — 成功
    1 — 输入错误
"""

import sys
import json
import io
from datetime import datetime
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def generate_report(pnl_data, news_data, alerts, output_dir):
    """生成报告文本并保存到文件"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    datetime_str = now.strftime("%Y-%m-%d %H:%M")
    filename = f"report_{now.strftime('%Y%m%d')}.txt"
    output_path = Path(output_dir) / filename

    holdings = pnl_data.get("holdings", [])
    summary = pnl_data.get("summary", {})

    lines = []

    # ── 标题 ──
    lines.append(f"=== 基金持仓周报 {date_str} ===")
    lines.append("")

    # ── 规则提示 ──
    if alerts:
        lines.append("【规则提示】")
        for alert in alerts:
            lines.append(alert["message"])
        lines.append("")

    # ── 持仓概览 ──
    lines.append("【持仓概览】")
    total_value = summary.get("total_value", 0)
    total_cost = summary.get("total_cost", 0)
    total_pnl = summary.get("total_pnl", 0)
    total_pnl_pct = summary.get("total_pnl_pct", 0)

    lines.append(f"总市值：{total_value:,.2f} 元")
    lines.append(f"总成本：{total_cost:,.2f} 元")
    pnl_sign = "+" if total_pnl >= 0 else ""
    lines.append(f"总盈亏：{pnl_sign}{total_pnl:,.2f} 元 ({pnl_sign}{total_pnl_pct:.2f}%)")
    lines.append("")

    # ── 各基金明细 ──
    lines.append("【各基金明细】")
    lines.append(f"{'基金名称':<20} {'持有市值':>10} {'盈亏金额':>10} {'盈亏%':>8} {'备注':<12}")
    lines.append("-" * 64)

    for h in holdings:
        if "error" in h:
            lines.append(f"{h['name']:<20} {'---':>10} {'---':>10} {'---':>8} 数据缺失")
            continue

        # 备注：回本涨幅
        note = ""
        if h["recovery_pct"] > 0:
            note = f"回本+{h['recovery_pct']:.1f}%"
        elif h["pnl_pct"] >= 30:
            note = "止盈关注"

        pnl_sign = "+" if h["pnl_amount"] >= 0 else ""
        lines.append(
            f"{h['name'][:18]:<20} "
            f"{h['current_value']:>10,.2f} "
            f"{pnl_sign}{h['pnl_amount']:>9,.2f} "
            f"{pnl_sign}{h['pnl_pct']:>7.2f}% "
            f"{note:<12}"
        )

    lines.append("")

    # ── 板块新闻摘要（P6修复：支持新格式） ──
    if news_data:
        lines.append("【板块新闻摘要】")
        # 新格式：dict of {sector: {positive: [], negative: []}}
        if isinstance(news_data, dict):
            for sector, data in news_data.items():
                if isinstance(data, dict):
                    pos = "；".join(data.get("positive", [])[:2])
                    neg = "；".join(data.get("negative", [])[:2])
                    lines.append(f"[{sector}] 利多: {pos} | 利空: {neg}")
                else:
                    lines.append(f"[{sector}] {data}")
        # 旧格式：list of dicts
        elif isinstance(news_data, list):
            for item in news_data:
                sector = item.get("sector", "未知")
                summary_text = item.get("summary", "无数据")
                lines.append(f"[{sector}] {summary_text}")
        lines.append("")

    # ── 数据说明 ──
    lines.append("【数据说明】")
    lines.append(f"净值来源：天天基金网（AKShare）")
    lines.append(f"新闻来源：东方财富（AKShare）")
    lines.append(f"生成时间：{datetime_str}")
    lines.append("本报告仅供参考，不构成投资建议")

    # ── 输出 ──
    report_text = "\n".join(lines)

    # 保存文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    # 输出到 stdout
    print(report_text)
    print(f"\n[INFO] 报告已保存: {output_path}", file=sys.stderr)

    return str(output_path)


def main():
    if len(sys.argv) < 5:
        print("[ERROR] 用法: python generate_report.py <pnl.json> <news.json> <alerts.json> <output_dir>",
              file=sys.stderr)
        sys.exit(1)

    pnl_path = Path(sys.argv[1])
    news_path = Path(sys.argv[2])
    alerts_path = Path(sys.argv[3])
    output_dir = sys.argv[4]

    for path, name in [(pnl_path, "pnl"), (news_path, "news"), (alerts_path, "alerts")]:
        if not path.exists():
            print(f"[WARN] {name}.json 不存在: {path}，将使用空数据", file=sys.stderr)

    # 读取数据
    with open(pnl_path, "r", encoding="utf-8") as f:
        pnl_data = json.load(f)
    with open(news_path, "r", encoding="utf-8") as f:
        news_data = json.load(f)
    with open(alerts_path, "r", encoding="utf-8") as f:
        alerts = json.load(f)

    output_path = generate_report(pnl_data, news_data, alerts, output_dir)
    print(f"\n[DONE] {output_path}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
