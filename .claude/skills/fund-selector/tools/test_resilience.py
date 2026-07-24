#!/usr/bin/env python3
"""工作流完备性与降级韧性测试"""
import sys, io, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TOOLS = ROOT / ".claude/skills/fund-selector/tools"
REPORTS = REPO / "fund-reports"


def _import(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(TOOLS / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_graceful_degradation_missing_all_data():
    """全部数据缺失时，约束校验应返回合理结果而非崩溃。"""
    m = _import("constraint_validator")
    r = m.validate_constraints({})
    assert isinstance(r["passed"], bool)
    assert len(r["failures"]) == 0  # 无数据 = 无法证伪 = 通过


def test_partial_data_handling():
    """部分数据缺失时，应跳过缺失项检查。"""
    m = _import("constraint_validator")
    rec = {
        "funds": [{"code": "A", "name": "A", "industry_alloc": {"制造": 10}, "fee_total": 1.5, "amount": 1000, "is_dca": True}],
        # 无 monthly_savings → 跳过预算检查
        # 无 target_allocation → 跳过配置闭环
        "disclaimers": ["免责"],
    }
    r = m.validate_constraints(rec)
    assert r["passed"] is True  # 无违规数据


def test_report_audit_partial_verification():
    """部分数据有核验值、部分无 → 应分别处理。"""
    m = _import("report_audit")
    results = json.dumps([
        {"reported": 4.42, "fetched_value": 4.40},  # 有核验
        {"reported": 29.0, "fetched_value": None},   # 无核验
    ])
    r = m.audit_verdict(results)
    assert r["checked"] == 1  # 只有1个被核验
    assert r["total"] == 2


def test_cross_validate_handles_string_values():
    """cross_validate 应处理字符串数值（如 "4.42"）。"""
    m = _import("financial_rigor")
    # JSON 解析后通常是 float，但测试字符串输入
    r = m.cross_validate("规模", {"A": 4.42, "B": "4.38"}, "亿")
    # "4.38" 字符串会被 exact() 转为 Decimal
    assert isinstance(r["all_consistent"], bool) or r["all_consistent"] is None


def test_nav_history_fallback_simulation():
    """模拟净值历史降级：主源失败 → 备用源（纯 Python，不依赖 pandas）。"""
    def try_sources_sync_pure(*sources):
        last_error = None
        for name, func, kwargs in sources:
            try:
                result = func(**kwargs)
                if result is not None and result:
                    return result
                continue
            except Exception as e:
                last_error = e
                continue
        if last_error:
            raise last_error
        return None

    def failing_source():
        raise ConnectionError("API timeout")
    def success_source():
        return [1, 2, 3]

    result = try_sources_sync_pure(
        ("primary", failing_source, {}),
        ("fallback", success_source, {}),
    )
    assert len(result) == 3, "应降级到备用源"




def test_nav_history_all_sources_fail():
    """全部源失败 → 应抛出异常（不崩溃）。"""
    def try_sources_sync_pure(*sources):
        last_error = None
        for name, func, kwargs in sources:
            try:
                result = func(**kwargs)
                if result is not None and result:
                    return result
                continue
            except Exception as e:
                last_error = e
                continue
        if last_error:
            raise last_error
        return None

    def fail1():
        raise ConnectionError("timeout")
    def fail2():
        raise ValueError("invalid")

    try:
        try_sources_sync_pure(
            ("primary", fail1, {}),
            ("fallback", fail2, {}),
        )
        assert False, "应抛出异常"
    except (ConnectionError, ValueError):
        pass  # 预期行为




def test_constraint_validator_with_api_error_markers():
    """模拟 API 返回错误标记（如 "数据不可用"、None）。"""
    m = _import("constraint_validator")
    rec = {
        "funds": [{"code": "A", "name": "A", "industry_alloc": {}, "fee_total": None, "amount": 0, "is_dca": True}],
        "monthly_savings": 0,  # API 可能返回 0 表示未知
        "disclaimers": ["免责"],
    }
    r = m.validate_constraints(rec)
    assert isinstance(r["passed"], bool)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✅ {t.__name__}")
        except (AssertionError, Exception) as e:
            failed += 1
            print(f"  ❌ {t.__name__}: {e}")
    print(f"\n结果：{passed} 通过 / {failed} 失败 / 共 {len(tests)} 条")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
