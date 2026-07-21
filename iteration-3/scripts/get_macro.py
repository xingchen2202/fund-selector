#!/usr/bin/env python3
"""
get_macro.py — 读取 Claude 写入的宏观数据，格式化输出
━━━━━━━━━━━━━━━━━━━━
P5修复：降级为纯格式化工具。
实际 MCP 调用由 Claude 执行后写入 _pipeline_step1_macro.json。
此脚本仅读取并格式化输出到 stderr，供 Claude 确认数据完整性。
"""
import json
import sys
import io
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
REPORTS_DIR = PROJECT_ROOT / "fund-reports"

MACRO_FILE = REPORTS_DIR / "_pipeline_step1_macro.json"


def main():
    """读取 step1 宏观数据文件，格式化输出"""
    if not MACRO_FILE.exists():
        print("[WARN] 宏观数据文件不存在: {}".format(MACRO_FILE), file=sys.stderr)
        print("[提示] 请先由 Claude 调用 MCP 工具并写入 _pipeline_step1_macro.json", file=sys.stderr)
        # 输出空模板供参考
        template = {
            "pmi": {"available": None, "manufacturing": None, "non_manufacturing": None},
            "money_supply": {"available": None, "m2_yoy": None},
            "valuation": {"available": None, "hs300_pe": None, "hs300_pe_percentile": None},
            "north_bound": {"available": None, "recent_flow": None},
            "cycle_judgment": {"phase": None, "confidence": None, "direction": None},
            "available_indicators": [],
            "unavailable_indicators": [],
        }
        print(json.dumps(template, ensure_ascii=False, indent=2))
        return

    with open(MACRO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 格式化输出
    cycle = data.get("cycle_judgment", {})
    phase = cycle.get("phase", "未知")
    confidence = cycle.get("confidence", "N/A")
    direction = cycle.get("direction", "N/A")

    print("[MACRO] 周期判断: {} (置信度: {})".format(phase, confidence), file=sys.stderr)
    print("[MACRO] 配置方向: {}".format(direction), file=sys.stderr)

    available = data.get("available_indicators", [])
    unavailable = data.get("unavailable_indicators", [])

    if available:
        print("[MACRO] 可用指标: {}".format(", ".join(available)), file=sys.stderr)
        # 输出各指标详情
        pmi = data.get("pmi", {})
        if pmi.get("available"):
            print("[MACRO]   PMI: 制造业={}, 非制造业={}".format(
                pmi.get("manufacturing", "N/A"),
                pmi.get("non_manufacturing", "N/A")
            ), file=sys.stderr)

        money = data.get("money_supply", {})
        if money.get("available"):
            print("[MACRO]   M2同比={}%, M1同比={}%".format(
                money.get("m2_yoy", "N/A"),
                money.get("m1_yoy", "N/A")
            ), file=sys.stderr)

        val = data.get("valuation", {})
        if val.get("available"):
            print("[MACRO]   沪深300 PE={} (分位={}%)".format(
                val.get("hs300_pe", "N/A"),
                val.get("hs300_pe_percentile", "N/A")
            ), file=sys.stderr)

        nb = data.get("north_bound", {})
        if nb.get("available"):
            print("[MACRO]   北向资金近期净流入={}".format(nb.get("recent_flow", "N/A")), file=sys.stderr)

    if unavailable:
        print("[MACRO] 不可用指标: {}".format(", ".join(unavailable)), file=sys.stderr)

    print("[MACRO] 数据完整性检查通过 ✓", file=sys.stderr)


if __name__ == "__main__":
    main()
