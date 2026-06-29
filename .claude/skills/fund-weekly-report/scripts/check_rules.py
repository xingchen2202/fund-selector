#!/usr/bin/env python3
"""
check_rules.py — 检查规则触发
━━━━━━━━━━━━━━━━━━━━
读取 calculate_pnl.py 的输出（JSON），
根据 ../_shared/rules-definitions.md 中的阈值检查规则。
输出 JSON 到 stdout。

用法:
    python check_rules.py <pnl_json_path>
    或: python calculate_pnl.py ... | python check_rules.py -

退出码:
    0 — 无规则触发
    1 — 有规则触发（输出仍正常）
"""

import sys
import json
import io
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 规则阈值（与 rules-definitions.md 保持一致）
THRESHOLDS = {
    "profit_alert": 30.0,       # 止盈提示：盈利 > 30%
    "concentration": 25.0,      # 集中度警告：板块占比 > 25%
    "weekly_loss": -3.0,        # 跌幅提示：周跌幅 > 3%
}

# 板块映射（基金代码 → 板块）
SECTOR_MAP = {
    "004597": "银行",
    "013477": "金融科技",
    "024725": "人工智能",
    "008888": "半导体",
    "017437": "纳斯达克",
    "025720": "港股科技",
    "023729": "科创板",
    "008702": "黄金",
    "000216": "黄金",
    "009033": "黄金",
    "005164": "均衡",
    "022015": "债券",
    "004503": "债券",
    "013279": "FOF",
    "012349": "港股科技",
}


def check_rules(pnl_data):
    """检查所有规则，返回触发的提示列表"""
    alerts = []
    holdings = pnl_data.get("holdings", [])
    summary = pnl_data.get("summary", {})

    # ── 规则 1: 止盈提示 ──
    for h in holdings:
        if h.get("pnl_pct", 0) > THRESHOLDS["profit_alert"]:
            alerts.append({
                "level": "warning",
                "type": "profit_alert",
                "message": f"⚠️ {h['name']}（{h['code']}）盈利已达 +{h['pnl_pct']:.2f}%，超过30%阈值，建议评估是否部分止盈",
            })

    # ── 规则 2: 集中度警告 ──
    total_value = summary.get("total_value", 0)
    if total_value > 0:
        sector_values = {}
        for h in holdings:
            if "error" in h:
                continue
            sector = SECTOR_MAP.get(h["code"], "其他")
            sector_values[sector] = sector_values.get(sector, 0) + h.get("current_value", 0)

        for sector, value in sector_values.items():
            pct = round(value / total_value * 100, 2)
            if pct > THRESHOLDS["concentration"]:
                alerts.append({
                    "level": "warning",
                    "type": "concentration",
                    "message": f"⚠️ {sector}板块占比 {pct:.2f}%，超过25%阈值，建议关注分散",
                })

    # ── 规则 3: 跌幅提示 ──
    total_pnl_pct = summary.get("total_pnl_pct", 0)
    if total_pnl_pct < THRESHOLDS["weekly_loss"]:
        alerts.append({
            "level": "warning",
            "type": "weekly_loss",
            "message": f"⚠️ 组合总盈亏 {total_pnl_pct:.2f}%，跌幅超过3%阈值",
        })

    return alerts


def main():
    if len(sys.argv) < 2:
        print("[ERROR] 用法: python check_rules.py <pnl.json 或 ->", file=sys.stderr)
        sys.exit(1)

    source = sys.argv[1]
    if source == "-":
        pnl_data = json.load(sys.stdin)
    else:
        pnl_path = Path(source)
        if not pnl_path.exists():
            print(f"[ERROR] 文件不存在: {pnl_path}", file=sys.stderr)
            sys.exit(1)
        with open(pnl_path, "r", encoding="utf-8") as f:
            pnl_data = json.load(f)

    alerts = check_rules(pnl_data)
    print(json.dumps(alerts, ensure_ascii=False, indent=2))
    sys.exit(1 if alerts else 0)


if __name__ == "__main__":
    main()
