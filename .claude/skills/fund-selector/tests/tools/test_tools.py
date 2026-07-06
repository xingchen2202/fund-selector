#!/usr/bin/env python3
"""测试工具层（5 个工具）"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(r"C:\Users\22218\Desktop\fund-selector")
TOOLS = REPO / ".claude/skills/fund-selector/tools"


def _import(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(TOOLS / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_financial_rigor_scale():
    """规模验算：份额×净值 vs 报告规模"""
    m = _import("financial_rigor")
    # 4.42亿份 × 1.0553 = 4.664亿 vs 报告 4.68亿 → 偏差 <5% 应通过
    passed = m.verify_scale(1.0553, 4.42e8, 4.68e8)
    assert passed is True, "偏差 <5% 应通过"


def test_financial_rigor_valuation():
    """估值验算：PE/PB 计算正确"""
    m = _import("financial_rigor")
    r = m.verify_valuation(1.0553, eps=0.052, bps=1.08)
    assert "PE" in r and "PB" in r
    # PE = 1.0553 / 0.052 ≈ 20.29; PB = 1.0553 / 1.08 ≈ 0.98
    assert 20.0 < r["PE"] < 21.0
    assert 0.9 < r["PB"] < 1.0


def test_financial_rigor_cross_validate():
    """交叉验证：偏差 <1% 应一致"""
    m = _import("financial_rigor")
    r = m.cross_validate("规模", {"MCP": 4.42, "Excel": 4.38}, "亿", tolerance_pct=2.0)
    assert r["all_consistent"] is True
    assert abs(r["consensus"] - 4.40) < 0.05


def test_financial_rigor_benford():
    """Benford 检测：自然数据应符合"""
    m = _import("financial_rigor")
    # 构造符合 Benford 分布的数据
    import random
    random.seed(42)
    vals = []
    for _ in range(100):
        d = random.randint(1, 9)
        vals.append(float(d) * random.uniform(1, 10))
    r = m.benford_check(vals)
    assert r is not None
    assert "mad" in r


def test_data_validator_single():
    """单数据点验证"""
    m = _import("data_validator")
    r = m.validate_single("规模", 4.42, 4.38, 0.01)
    assert r["consistent"] is True
    assert r["deviation"] < 1.0


def test_data_validator_batch():
    """批量验证"""
    m = _import("data_validator")
    data = {
        "规模": {"primary": 4.42, "secondary": 4.38},
        "费率": {"primary": 1.5, "secondary": 1.5},
    }
    r = m.batch_validate(data, 0.01)
    assert r["summary"]["pass_rate"] == 100.0


def test_stock_screener_momentum():
    """动量筛选：上涨序列应通过"""
    m = _import("stock_screener")
    up = [1.0 * (1.008 ** i) for i in range(60)]
    r = m.screen_momentum(up)
    assert r["passed"] is True
    assert r["signal"] in ("强", "中")


def test_stock_screener_quality():
    """质量评分：全优应 6/6"""
    m = _import("stock_screener")
    data = {"roe": 20, "gross_margin": 45, "fcf": 100, "debt_ratio": 30, "share_change": 0, "earnings_cv": 0.1}
    r = m.grade_quality(data)
    assert r["score"] == 6
    assert r["position_advice"] == "8%"


def test_report_audit_extract():
    """报告审计：提取数据点并抽样"""
    m = _import("report_audit")
    # 写临时报告
    report = REPORTS_DIR / "_test_report_audit.md"
    report.write_text("""
# 测试报告
基金规模 4.42 亿元，近1年收益 62.03%。
PE(TTM) 20.3 倍，PB 0.98 倍。
基金经理任职 3.5 年。
""", encoding="utf-8")
    try:
        r = m.extract_data_points(str(report), 1.0)  # 100% 抽样
        assert r["total_points"] >= 3
        assert r["sampled_count"] >= 3
    finally:
        if report.exists(): report.unlink()


def test_report_audit_verdict():
    """审计结论：全部通过→通过"""
    m = _import("report_audit")
    results = json.dumps([
        {"code": "A", "verified": True},
        {"code": "B", "verified": True},
    ])
    r = m.audit_verdict(results)
    assert r["verdict"] == "通过"
    assert r["pass_rate"] == 100.0


REPORTS_DIR = REPO / "fund-reports"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            sys.stderr.write(f"  ✅ {t.__name__}\n")
        except AssertionError as e:
            failed += 1
            sys.stderr.write(f"  ❌ {t.__name__}: {e}\n")
    sys.stderr.write(f"\n结果：{passed} 通过 / {failed} 失败 / 共 {len(tests)} 条\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
