#!/usr/bin/env python3
"""快否决清单（Rejection Checklist）— A 股基金版
━━━━━━━━━━━━━━━━━━━━
移植自 ai-berkshire (MIT) 的 investment-checklist 8 条红线，
针对 A 股公募基金语境改写为 6 条一票否决。

用法：
    python .claude/skills/fund-recommend/scripts/rejection_checklist.py --code 003593 \\
        --drawdown -0.6191 --fcf-negative --relying-on-next-buyer \\
        --erosion --cannot-afford-zero

    参数为"触发条件"：传了即表示该红线被触发。
    返回码：0 = 全部通过；1 = 至少一条红线触发（否决）。
"""

import argparse
import json
import sys
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 6 条一票否决红线（A 股基金版）
# 移植自 ai-berkshire 的 8 条红线，适配基金研究语境
# ---------------------------------------------------------------------------

RED_LINES = [
    {
        "id": "R1",
        "name": "无法说清底层赚钱方式",
        "arg": "--business-unclear",
        "desc": "无法用 1-2 句话说清基金底层资产靠什么赚钱 → 否决",
    },
    {
        "id": "R2",
        "name": "连续为负的自由现金流 / 持续亏损",
        "arg": "--fcf-negative",
        "desc": "底层重仓股连续 3 年自由现金流为负且看不到改善 → 否决",
    },
    {
        "id": "R3",
        "name": "最大回撤突破稳健阈值",
        "arg": "--drawdown",
        "check": lambda args: args.drawdown is not None and args.drawdown < -0.35,
        "desc": "成立以来最大回撤 < -35%（权益类）→ 否决",
    },
    {
        "id": "R4",
        "name": "竞争优势被不可逆侵蚀",
        "arg": "--erosion",
        "desc": "底层行业/赛道面临不可逆的份额流失（如被新技术替代）→ 否决",
    },
    {
        "id": "R5",
        "name": "靠'下一个接盘者出更高价'赚钱（博傻）",
        "arg": "--relying-on-next-buyer",
        "desc": "估值完全依赖市场情绪/流动性推高，无基本面支撑 → 否决",
    },
    {
        "id": "R6",
        "name": "无法承受归零后果",
        "arg": "--cannot-afford-zero",
        "desc": "仓位过重或底层资产存在退市/清零风险，无法承受归零 → 否决",
    },
]


def _write_rejection(output_path, rejected):
    """将单只基金的否决结果追加写入 pipeline 步骤文件（供 generate_recommend 消费）。"""
    if not output_path:
        return False
    path = Path(output_path)
    try:
        existing = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            existing = list(d.get("rejected", []))
        existing.append(rejected)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"rejected": existing, "rejected_count": len(existing)},
                      f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="快否决清单 — A 股基金版（6 条一票否决红线）",
        epilog="示例:\n  %(prog)s --code 003593 --drawdown -0.6191 --output _pipeline_rejection.json\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--code", required=True, help="基金代码")
    parser.add_argument("--name", default="", help="基金简称")
    parser.add_argument("--business-unclear", action="store_true",
                        help="R1: 无法说清底层赚钱方式")
    parser.add_argument("--fcf-negative", action="store_true",
                        help="R2: 连续为负的自由现金流/持续亏损")
    parser.add_argument("--drawdown", type=float, default=None,
                        help="R3: 成立以来最大回撤（负数，如 -0.61 表示 -61%）")
    parser.add_argument("--erosion", action="store_true",
                        help="R4: 竞争优势被不可逆侵蚀")
    parser.add_argument("--relying-on-next-buyer", action="store_true",
                        help="R5: 靠下一个接盘者出更高价（博傻）")
    parser.add_argument("--cannot-afford-zero", action="store_true",
                        help="R6: 无法承受归零后果")
    parser.add_argument("--output", default=None,
                        help="写入否决结果到 pipeline 步骤文件（如 _pipeline_rejection.json）")

    args = parser.parse_args()

    print("=" * 60)
    print(f"快否决清单 — {args.code} {args.name}")
    print("=" * 60)
    print()

    triggered = []

    # R1
    if args.business_unclear:
        triggered.append("R1")
        print("  ❌ R1 触发: 无法说清底层赚钱方式 → 否决")
    # R2
    if args.fcf_negative:
        triggered.append("R2")
        print("  ❌ R2 触发: 连续为负的自由现金流/持续亏损 → 否决")
    # R3
    if args.drawdown is not None and args.drawdown < -0.35:
        triggered.append("R3")
        print(f"  ❌ R3 触发: 最大回撤 {args.drawdown * 100:.1f}% < -35% → 否决")
    # R4
    if args.erosion:
        triggered.append("R4")
        print("  ❌ R4 触发: 竞争优势被不可逆侵蚀 → 否决")
    # R5
    if args.relying_on_next_buyer:
        triggered.append("R5")
        print("  ❌ R5 触发: 靠下一个接盘者出更高价（博傻）→ 否决")
    # R6
    if args.cannot_afford_zero:
        triggered.append("R6")
        print("  ❌ R6 触发: 无法承受归零后果 → 否决")

    print()
    if triggered:
        ids = ",".join(triggered)
        print(f"  ⛔ 结论: 触发红线 [{ids}]，一票否决。该基金不得进入最终推荐。")
        print()
        print("  宁可错过，不可做错。")
        rejected = {"code": args.code, "name": args.name, "triggered": triggered}
        if _write_rejection(args.output, rejected):
            print(f"  [INFO] 已写入否决结果到 pipeline")
        sys.exit(1)
    else:
        print("  ✅ 全部红线未触发，通过快否决检查。")
        print("  注意: 通过快否决 ≠ 推荐买入，仍需走完整 4 步筛选流程。")
        sys.exit(0)


if __name__ == "__main__":
    main()
