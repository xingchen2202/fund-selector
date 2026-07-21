#!/usr/bin/env python3
"""报告审计工具（Report Audit）— 双源核验 + CI 门
━━━━━━━━━━━━━━━━━━━━
移植并增强自 ai-berkshire (MIT) report_audit.py。

对比旧版（正则+15%随机抽样）的改进：
1. 双源核验：支持 fetched_value（主源）+ fetched_value2（副源），1% 容差判定
2. 降级逻辑：单源通过+单源不通过 → ⚠️ 警告（而非 fail），避免 GAAP/Non-GAAP、汇率等口径差异误杀
3. 标签去重 + 噪声过滤：按 "label|rounded_val|unit" 去重；过滤"来源/说明/年份"等无效标签
4. 多结构提取：覆盖多列表格、KV 冒号行、加粗数字三类结构
5. CI 门：verdict 返回非零退出码（0=通过，1=打回），可直接挂 CI

零外部依赖 — 仅 Python stdlib。Python >= 3.7。

用法：
    python tools/report_audit.py extract --report <报告.md> [--sample-rate 0.15]
    python tools/report_audit.py verdict --results '<JSON抽样结果>'
"""

import argparse
import json
import random
import re
import sys
import io

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

# 1% 容差（移植自 ai-berkshire）
_TOLERANCE = 0.01

# 数据点提取模式：(正则, 单位标签, 类别)
_PATTERNS = [
    (r'([\d,，\.]+)\s*%',                          '%',    'percent'),
    (r'([\d,，\.]+)\s*亿(元|美元|港元|RMB|USD|HKD)?', '亿',    'hundred_million'),
    (r'([\d,，\.]+)\s*[xX倍]',                     'x',    'multiple'),
    (r'([\d,，\.]+)\s*万亿',                        '万亿', 'trillion'),
    (r'\$\s*([\d,，\.]+)\s*([BMT亿])',               '$',    'usd_abs'),
    (r'\|\s*[~约]?\$?([\d,，\.]+)\s*\|',             '',     'table_num'),
]

# KV 冒号行：标签：数值（单位可选）
_KV_LABEL_RE = re.compile(
    r'(?P<label>[一-龥A-Za-z][^\|\n：:*]{1,30})[：:]\s*[~约]?\$?'
    r'(?P<num>[\d,，\.]+)\s*(?P<unit>亿[元美港]?元?|万亿|[xX倍]|%|[BMT])?'
)

# 无效标签噪声过滤（移植自 ai-berkshire _is_valid_label）
_LABEL_SKIP = {"来源", "说明", "备注", "附录", "数据", "来源说明"}
_LABEL_SKIP_PREFIX = ("---", "===")


def _is_valid_label(label: str) -> bool:
    """过滤无效标签：纯年份、markdown 分隔符、短噪声词。"""
    t = label.strip()
    if not t or len(t) < 2:
        return False
    if re.fullmatch(r'\d{4}[-/年]?', t):
        return False
    if t in _LABEL_SKIP:
        return False
    if any(t.startswith(p) for p in _LABEL_SKIP_PREFIX):
        return False
    return True


def _clean_num(raw: str) -> float:
    """清洗数值字符串（去除千分位、全角逗号）。"""
    return float(raw.replace(",", "").replace("，", ""))


def extract_data_points(report_path: str, sample_rate: float = 0.15) -> dict:
    """从报告中提取可验证的数据点，随机抽样。

    覆盖三类结构：多列表格、KV 冒号行、加粗/普通数字。
    按 "label|rounded_val|unit" 去重，过滤无效标签。
    """
    text = Path(report_path).read_text(encoding="utf-8")

    data_points = []
    seen = set()  # 去重键：label|rounded_val|unit

    def _add(label: str, val: str, unit: str, context: str, position: int):
        if not _is_valid_label(label):
            return
        try:
            num = _clean_num(val)
        except ValueError:
            return
        key = f"{label.strip()}|{round(num, 2)}|{unit}"
        if key in seen:
            return
        seen.add(key)
        data_points.append({
            "label": label.strip(),
            "value": val,
            "unit": unit,
            "context": context,
            "position": position,
        })

    # 结构 1：通用正则（数字+单位）
    for pat, unit, _cat in _PATTERNS:
        for m in re.finditer(pat, text):
            val = m.group(1)
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            context = text[start:end].replace('\n', ' ')
            # 从上下文左侧提取标签（最近的一个 KV 标签或行首词）
            label = _guess_label(text, m.start())
            _add(label, val, unit, context, m.start())

    # 结构 2：KV 冒号行
    for m in _KV_LABEL_RE.finditer(text):
        label = m.group("label")
        val = m.group("num")
        unit = (m.group("unit") or "").strip()
        start = max(0, m.start() - 20)
        end = min(len(text), m.end() + 20)
        context = text[start:end].replace('\n', ' ')
        _add(label, val, unit, context, m.start())

    # 随机抽样
    n_sample = max(1, int(len(data_points) * sample_rate))
    sampled = random.sample(data_points, min(n_sample, len(data_points)))

    return {
        "total_points": len(data_points),
        "sampled_count": len(sampled),
        "sample_rate": sample_rate,
        "samples": sampled,
        "instruction": f"请验证以下 {len(sampled)} 个数据点（抽样率 {sample_rate:.0%}），"
                       f"标注每个数据点的来源和准确性。",
    }


def _guess_label(text: str, pos: int) -> str:
    """从数值位置向前猜测标签（取最近一行冒号前的文本或行首词）。"""
    line_start = text.rfind("\n", 0, pos)
    line_start = line_start + 1 if line_start != -1 else 0
    line = text[line_start:pos]
    # 尝试 "标签：" 或 "标签:" 模式
    m = re.search(r'([一-龥A-Za-z][^\n：:]{1,20})[：:]\s*$', line)
    if m:
        return m.group(1).strip()
    # 退路：取行首连续中文/英文词
    m2 = re.match(r'\s*([一-龥A-Za-z][^\n：:]{1,30}?)[：:\s]*$', line)
    if m2:
        return m2.group(1).strip()
    return "未标注"


def _pct_diff(reported: float, fetched: float) -> float:
    """相对偏差。报告值为 0 时特殊处理。"""
    if reported == 0:
        return 0.0 if fetched == 0 else float("inf")
    return abs(reported - fetched) / abs(reported)


def audit_verdict(results_json: str) -> dict:
    """根据验证结果输出审计结论（双源核验 + 降级逻辑）。

    每个数据点可含：
      - reported: 报告值（数值）
      - fetched_value: 主源核验值（可选）
      - fetched_value2: 副源核验值（可选）
      - verified: 兼容旧版的布尔判定（可选）

    判定规则（移植自 ai-berkshire）：
      - 双源均在 1% 容差内 → ✅ 通过
      - 双源均超容差 → ❌ 不通过
      - 单通过单不通过 → ⚠️ 警告（口径差异可能，人工复核）
      - 未提供核验值 → 跳过
    """
    try:
        results = json.loads(results_json)
    except Exception:
        results = []

    total = len(results)
    if total == 0:
        return {"verdict": "无法审计", "pass_rate": 0, "passed": 0, "failed": 0, "warned": 0}

    passed = failed = warned = 0
    fail_items = []
    warn_items = []

    for r in results:
        reported = r.get("reported")
        # 兼容旧版布尔 verified
        if r.get("verified") is True and reported is None:
            passed += 1
            continue
        if r.get("verified") is False:
            failed += 1
            fail_items.append(r)
            continue

        fetched = r.get("fetched_value")
        if fetched is None or reported is None:
            continue  # 未提供核验值，跳过

        try:
            reported_f = _clean_num(str(reported)) if isinstance(reported, str) else float(reported)
            fetched_f = _clean_num(str(fetched)) if isinstance(fetched, str) else float(fetched)
        except (ValueError, TypeError):
            continue

        diff1 = _pct_diff(reported_f, fetched_f)
        pass1 = diff1 <= _TOLERANCE

        fetched2 = r.get("fetched_value2")
        if fetched2 is not None:
            try:
                fetched2_f = _clean_num(str(fetched2)) if isinstance(fetched2, str) else float(fetched2)
            except (ValueError, TypeError):
                fetched2_f = None
            diff2 = _pct_diff(reported_f, fetched2_f) if fetched2_f is not None else None
            pass2 = (diff2 is None) or (diff2 <= _TOLERANCE)
        else:
            pass2 = True  # 单源时视为通过

        if pass1 and pass2:
            passed += 1
        elif not pass1 and not pass2:
            failed += 1
            fail_items.append(r)
        else:
            # 降级：单源通过+单源不通过 → 警告（口径差异）
            warned += 1
            warn_items.append(r)

    checked = passed + failed + warned
    pass_rate = passed / checked * 100 if checked else 0

    if failed == 0 and warned == 0:
        verdict = "通过"
    elif failed == 0:
        verdict = "有条件通过（含警告）"
    else:
        verdict = "不通过"

    return {
        "verdict": verdict,
        "pass_rate": round(pass_rate, 1),
        "passed": passed,
        "failed": failed,
        "warned": warned,
        "total": total,
        "checked": checked,
        "failed_items": fail_items,
        "warned_items": warn_items,
    }


def main():
    parser = argparse.ArgumentParser(description="报告审计工具 — 双源核验 + CI 门")
    sub = parser.add_subparsers(dest="command")

    ex = sub.add_parser("extract", help="从报告提取数据点并抽样")
    ex.add_argument("--report", required=True)
    ex.add_argument("--sample-rate", type=float, default=0.15)

    ve = sub.add_parser("verdict", help="根据验证结果输出审计结论")
    ve.add_argument("--results", required=True)

    args = parser.parse_args()

    if args.command == "extract":
        result = extract_data_points(args.report, args.sample_rate)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "verdict":
        result = audit_verdict(args.results)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        # 非零退出码表示打回，方便 CI/脚本判断（移植自 ai-berkshire）
        if result.get("verdict") == "不通过":
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
