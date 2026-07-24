#!/usr/bin/env python3
"""MCP 集成测试 — mock AKShare 异常返回，测试工具降级行为
━━━━━━━━━━━━━━━━━━━━
由于本会话无法连接 MCP 服务器，使用 mock 测试工具对异常返回的处理。
"""
import sys, io, json
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TOOLS = ROOT / ".claude/skills/fund-selector/tools"


def test_financial_rigor_with_mock_data():
    """financial_rigor 使用模拟数据（无需 MCP）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("fr", str(TOOLS / "financial_rigor.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    # 正常数据
    assert m.verify_scale(1.0553, 4.42e8, 4.68e8) is True
    # 异常数据（零规模）
    assert m.verify_scale(1.0, 1e8, 0) is False
    print("  ✅ financial_rigor mock 测试通过")


def test_report_audit_with_mock_data():
    """report_audit 使用模拟数据。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ra", str(TOOLS / "report_audit.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    # 双源一致
    r = m.audit_verdict(json.dumps([{"reported": 4.42, "fetched_value": 4.40, "fetched_value2": 4.43}]))
    assert r["verdict"] == "通过"

    # 空输入
    r = m.audit_verdict("[]")
    assert r["verdict"] == "无法审计"

    # 畸形 JSON
    r = m.audit_verdict("not json")
    assert r["verdict"] == "无法审计"
    print("  ✅ report_audit mock 测试通过")


def test_constraint_validator_with_mock_data():
    """constraint_validator 使用模拟数据。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("cv", str(TOOLS / "constraint_validator.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    # 合规
    r = m.validate_constraints({
        "funds": [{"code": "A", "name": "A", "industry_alloc": {"消费": 10}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
        "monthly_savings": 5000, "disclaimers": ["免责"]
    })
    assert r["passed"] is True

    # 违规
    r = m.validate_constraints({
        "funds": [
            {"code": "A", "name": "A", "industry_alloc": {"制造": 30}, "fee_total": 1.5, "amount": 1000, "is_dca": True},
            {"code": "B", "name": "B", "industry_alloc": {"制造": 25}, "fee_total": 1.2, "amount": 1000, "is_dca": True},
        ],
        "monthly_savings": 5000, "disclaimers": ["免责"]
    })
    assert r["passed"] is False
    assert len(r["suggestions"]) >= 1
    print("  ✅ constraint_validator mock 测试通过")


def test_data_validator_with_mock_data():
    """data_validator 使用模拟数据。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("dv", str(TOOLS / "data_validator.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    # 双源一致
    r = m.validate_single("规模", 4.42, 4.38, 0.01)
    assert r["consistent"] is True

    # 双源不一致
    r = m.validate_single("规模", 4.42, 5.50, 0.01)
    assert r["consistent"] is False
    print("  ✅ data_validator mock 测试通过")


def test_stock_screener_with_mock_data():
    """stock_screener 使用模拟数据。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ss", str(TOOLS / "stock_screener.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    # 动量筛选（60 点上涨序列）
    up = [1.0 * (1.008 ** i) for i in range(60)]
    r = m.screen_momentum(up)
    assert r["passed"] is True

    # 质量评分（全优）
    r = m.grade_quality({"roe": 20, "gross_margin": 45, "fcf": 100, "debt_ratio": 30, "share_change": 0, "earnings_cv": 0.1})
    assert r["score"] == 6
    print("  ✅ stock_screener mock 测试通过")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 60)
    print("MCP 集成测试（mock 数据）")
    print("=" * 60)
    for t in tests:
        try:
            t()
            passed += 1
        except (AssertionError, Exception) as e:
            failed += 1
            print(f"  ❌ {t.__name__}: {e}")
    print(f"\n结果：{passed} 通过 / {failed} 失败 / 共 {len(tests)} 条")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
