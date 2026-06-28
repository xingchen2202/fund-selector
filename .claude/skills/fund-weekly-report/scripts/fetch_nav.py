#!/usr/bin/env python3
"""
fetch_nav.py — 获取基金最新净值
━━━━━━━━━━━━━━━━━━━━
读取 portfolio.json，通过 akshare 获取所有基金最新单位净值。
输出 JSON 到 stdout，供下游脚本消费。

数据获取策略:
  1. 批量接口 fund_open_fund_daily_em() — 覆盖绝大多数开放式基金
  2. 回退接口 fund_open_fund_info_em() — 覆盖 FOF/QDII 等净值延迟品种

用法:
    python fetch_nav.py <portfolio_json_path>
    输出: [{"code": "004597", "name": "...", "nav": 1.3111, "nav_date": "2026-06-26"}, ...]

退出码:
    0 — 全部成功
    1 — 部分或全部失败（输出仍包含成功的数据）
"""

import sys
import json
import io
from pathlib import Path

# Windows GBK 兼容性
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def get_nav_batch(fund_codes, ak):
    """批量获取开放式基金净值"""
    results = {}
    need_fallback = []

    try:
        df_daily = ak.fund_open_fund_daily_em()
        code_col = df_daily.columns[0]
        name_col = df_daily.columns[1]
        nav_cols = sorted(
            [c for c in df_daily.columns if "单位净值" in c],
            reverse=True
        )
        latest_nav_col = nav_cols[0] if nav_cols else None
        latest_nav_date = latest_nav_col.split("-")[0] if latest_nav_col else "unknown"

        for code in fund_codes:
            row = df_daily[df_daily[code_col] == code]
            if not row.empty and latest_nav_col:
                nav_val = row[latest_nav_col].values[0]
                if nav_val and str(nav_val).strip() and str(nav_val) != "nan":
                    results[code] = {
                        "nav": float(nav_val),
                        "nav_date": latest_nav_date,
                        "name": str(row[name_col].values[0]),
                    }
                else:
                    need_fallback.append(code)
            else:
                need_fallback.append(code)
    except Exception as e:
        print(f"[!] 批量接口异常: {e}", file=sys.stderr)
        need_fallback.extend(fund_codes)

    # 回退接口（FOF/QDII）
    if need_fallback:
        for code in need_fallback:
            try:
                df_info = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
                if df_info is not None and not df_info.empty:
                    df_info = df_info.sort_values("净值日期")
                    latest = df_info.iloc[-1]
                    results[code] = {
                        "nav": float(latest["单位净值"]),
                        "nav_date": str(latest["净值日期"]),
                        "name": "",  # 回退接口无名称
                    }
            except Exception as e:
                print(f"[!] 回退接口获取 {code} 失败: {e}", file=sys.stderr)

    return results


def main():
    if len(sys.argv) < 2:
        print("[ERROR] 用法: python fetch_nav.py <portfolio_json_path>", file=sys.stderr)
        sys.exit(1)

    portfolio_path = Path(sys.argv[1])
    if not portfolio_path.exists():
        print(f"[ERROR] 文件不存在: {portfolio_path}", file=sys.stderr)
        sys.exit(1)

    with open(portfolio_path, "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    fund_codes = [fund["code"] for fund in portfolio["funds"]]
    fund_names = {fund["code"]: fund["name"] for fund in portfolio["funds"]}

    # 延迟 import（首次较慢）
    import akshare as ak

    print(f"[INFO] 获取 {len(fund_codes)} 只基金净值...", file=sys.stderr)
    nav_data = get_nav_batch(fund_codes, ak)

    # 组装输出
    output = []
    success_count = 0
    for code in fund_codes:
        if code in nav_data:
            entry = nav_data[code]
            output.append({
                "code": code,
                "name": fund_names.get(code, entry.get("name", "")),
                "nav": entry["nav"],
                "nav_date": entry["nav_date"],
            })
            success_count += 1
        else:
            output.append({
                "code": code,
                "name": fund_names.get(code, ""),
                "nav": None,
                "nav_date": None,
            })

    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n[INFO] 成功: {success_count}/{len(fund_codes)}", file=sys.stderr)
    sys.exit(0 if success_count == len(fund_codes) else 1)


if __name__ == "__main__":
    main()
