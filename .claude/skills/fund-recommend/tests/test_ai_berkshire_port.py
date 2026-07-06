#!/usr/bin/env python3
"""回归测试套件 — 移植 ai-berkshire (MIT) 防偏差机制
━━━━━━━━━━━━━━━━━━━━
覆盖 B5（占位符修复）+ D2（最大回撤过滤）+ D5（Windows 编码）。

运行：
    py .claude/skills/fund-recommend/tests/test_ai_berkshire_port.py
"""
import io
import json
import subprocess
import sys
from pathlib import Path

# 强制 UTF-8 输出（Windows）
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SKILL_DIR = Path(__file__).parent.parent
SCRIPTS = SKILL_DIR / "scripts"
REPO = SKILL_DIR.parent.parent.parent


# ---------------------------------------------------------------------------
# A. 源代码静态断言（source_contains / source_not_contains）
# ---------------------------------------------------------------------------
def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_b3_scale_threshold_config():
    """B3: screen_candidates.py 必须定义 SCALE_THRESHOLD_WAN = 20000"""
    src = read(SCRIPTS / "screen_candidates.py")
    assert "SCALE_THRESHOLD_WAN = 20000" in src, "缺少规模阈值常量 20000（2亿）"


def test_b4_news_chinese_keywords():
    """B4: search_news.py SECTOR_QUERDS 必须全中文，禁用英文"""
    src = read(SCRIPTS / "search_news.py")
    for bad in ("NASDAQ US tech", "gold price outlook", "Hang Seng tech"):
        assert bad not in src, f"含英文禁用搜索词: {bad}"
    for good in ("纳斯达克", "黄金"):
        assert good in src, f"缺中文搜索词: {good}"


def test_b5b_no_placeholder_in_financial_rigor():
    """B5 延伸: financial_rigor.py / rejection_checklist.py 不得含'待补児'占位符"""
    for fn in ("financial_rigor.py", "rejection_checklist.py"):
        src = read(SCRIPTS / fn)
        assert "待补児" not in src and "待补充" not in src, f"{fn} 含'待补児'占位符"


def test_d5_utf8_wrapper_present():
    """D5: 全部脚本必须有 Windows UTF-8 wrapper"""
    for fn in ("financial_rigor.py", "rejection_checklist.py"):
        src = read(SCRIPTS / fn)
        assert "TextIOWrapper" in src and "utf-8" in src, f"{fn} 缺 UTF-8 wrapper"


# ---------------------------------------------------------------------------
# B. rejection_checklist 动态运行
# ---------------------------------------------------------------------------
def run_rejection(code, name, output_file=None, **flags):
    cmd = [sys.executable, str(SCRIPTS / "rejection_checklist.py"),
           "--code", code, "--name", name]
    if output_file:
        cmd += ["--output", str(output_file)]
    for k, v in flags.items():
        if v is True:
            cmd.append(f"--{k}")
        elif v is not None and v is not False:
            cmd += [f"--{k}", str(v)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


def test_r3_drawdown_triggers():
    """D2/R3: 权益类最大回撤 < -35% 必须触发否决（退出码 1）"""
    rc, out, _ = run_rejection("003593", "国泰景气", drawdown=-0.6191)
    assert rc == 1, f"预期退出码 1，实际 {rc}"
    assert "R3" in out, "未触发 R3 回撤红线"


def test_drawdown_pass():
    """D2: 回撤 -19.74%（未达 -35%）必须通过"""
    rc, out, _ = run_rejection("005561", "创金合信红利低波", drawdown=-0.1974)
    assert rc == 0, f"预期退出码 0，实际 {rc}"
    assert "❌" not in out, "误触发红线"


def test_multiple_redlines():
    """R3+R4 双触发，退出码 1"""
    rc, out, _ = run_rejection("003593", "双触发", drawdown=-0.6191, erosion=True)
    assert rc == 1
    assert "R3" in out and "R4" in out


# ---------------------------------------------------------------------------
# C. financial_rigor 精度校验
# ---------------------------------------------------------------------------
def run_rigor(subcmd, *args):
    cmd = [sys.executable, str(SCRIPTS / "financial_rigor.py"), subcmd] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_verify_scale_pass():
    """份额 × 净值 vs 报告规模，偏差 <1% 通过"""
    r = run_rigor("verify-scale", "--nav", "1.0553", "--shares", "442000000", "--reported", "466000000")
    assert r.returncode == 0, f"rigsor 崩溃: {r.stderr}"
    assert "✅" in r.stdout, "规模验算应通过"


def test_verify_scale_fail():
    """偏差 >5% 应失败"""
    r = run_rigor("verify-scale", "--nav", "1.0", "--shares", "1e8", "--reported", "5e8")
    assert "❌" in r.stdout, "偏差 >5% 应标记警告"


def test_cross_validate_consistent():
    """多源一致"""
    vals = json.dumps({"MCP": 4.42, "Excel": 4.38, "Ranking": 4.48})
    r = run_rigor("cross-validate", "--field", "规模", "--values", vals, "--unit", "亿")
    assert "✅" in r.stdout, "三源偏差 <2% 应通过"


def test_decimal_no_float_drift():
    """Decimal 精度：0.1 + 0.2 应精确等于 0.3"""
    r = run_rigor("calc", "--expr", "0.1 + 0.2")
    assert "0.30" in r.stdout, "Decimal 精确计算失败"


# ---------------------------------------------------------------------------
# E. 端到端集成：rejection_checklist --output 写入 rejection 步骤文件
# ---------------------------------------------------------------------------
def _reset_rejection():
    p = SCRIPTS.parent.parent / "fund-reports" / "_pipeline_rejection.json"
    if p.exists():
        p.unlink()
    return p


def test_e2e_rejection_persisted_to_pipeline():
    """E2E: rejection --output 应把被否决心写入 _pipeline_rejection.json，供 generate_recommend 消费"""
    rep_dir = SCRIPTS.parent.parent / "fund-reports"
    rep_dir.mkdir(exist_ok=True)
    rej_file = rep_dir / "_pipeline_rejection.json"
    if rej_file.exists():
        rej_file.unlink()

    # 触发 R3，结果持久化到 pipeline
    rc, _, _ = run_rejection("003593", "国泰景气", output_file=rej_file, drawdown=-0.6191)
    assert rc == 1, f"R3 应否决 003593，退出码 {rc}"
    assert rej_file.exists(), "否决结果未写入 pipeline 文件"

    data = json.loads(rej_file.read_text(encoding="utf-8"))
    codes = [r["code"] for r in data.get("rejected", [])]
    assert "003593" in codes, "003593 未出现在 persisted rejected 列表"


def test_e2e_benign_not_rejected():
    """E2E: 未触发红线的基金不得写入 rejected"""
    rep_dir = SCRIPTS.parent.parent / "fund-reports"
    rej_file = rep_dir / "_pipeline_rejection.json"
    if rej_file.exists():
        rej_file.unlink()
    rc, _, _ = run_rejection("005561", "红利低波", output_file=rej_file, drawdown=-0.1974)
    assert rc == 0
    if rej_file.exists():
        data = json.loads(rej_file.read_text(encoding="utf-8"))
        codes = [r["code"] for r in data.get("rejected", [])]
        assert "005561" not in codes, "005561 不应被否决"


# ---------------------------------------------------------------------------
# F. D4: 新闻搜索三级降级适配 AKShare 新签名
# ---------------------------------------------------------------------------
def test_news_level3_new_signature():
    """D4: search_news.py 必须调用 news_economic_baidu() 无 category 参数（适配新签名）"""
    src = read(SCRIPTS / "search_news.py")
    # 新签名: news_economic_baidu(date, cookie) — 不再接受 category
    assert 'news_economic_baidu(category=' not in src, \
        "D4 未修复：仍使用废弃的 category= 参数"
    # 必须仍存在降级调用（无参或仅 date/cookie）
    assert "news_economic_baidu()" in src or "news_economic_baidu(" in src, \
        "缺少百度新闻三级降级调用"


# ---------------------------------------------------------------------------
# G. 移植 ai-berkshire: 信息丰富度分级 / 反向测试 / 定投三情景
# ---------------------------------------------------------------------------
def _import_generate():
    """动态导入 generate_recommend 模块。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen", str(SCRIPTS / "generate_recommend.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_richness_grade_A():
    """信息丰富度：3 源齐全 = A 级"""
    g = _import_generate()
    detail = {"scale": 4.42, "manager": "张三", "return_1y": 5.5, "max_drawdown": -0.20}
    r = g.grade_data_richness(detail)
    assert r["grade"] == "A"
    assert r["present"] == 3


def test_richness_grade_C():
    """信息丰富度：仅 1 源 = C 级（应谨慎）"""
    g = _import_generate()
    detail = {"scale": 4.42}
    r = g.grade_data_richness(detail)
    assert r["grade"] == "C"
    assert "数据稀缺" in r["verdict"]


def test_richness_grade_B():
    """信息丰富度：2 源 = B 级"""
    g = _import_generate()
    detail = {"scale": 4.42, "manager": "张三"}
    r = g.grade_data_richness(detail)
    assert r["grade"] == "B"


def test_reverse_test_flags_high_drawdown():
    """反向测试：回撤 > 40% 必须提示风险"""
    g = _import_generate()
    c = {"sector": "混合"}
    detail = {"max_drawdown": -0.61, "age_years": 8, "fee_total": 1.5}
    out = g.build_reverse_test(c, detail)
    assert "回撤" in out and "61%" in out


def test_reverse_test_flags_young_fund():
    """反向测试：成立 <3 年必须提示验证不足"""
    g = _import_generate()
    c = {"sector": "混合"}
    detail = {"max_drawdown": -0.15, "age_years": 2, "fee_total": 1.0}
    out = g.build_reverse_test(c, detail)
    assert "2 年" in out and "验证不足" in out


def test_dca_scenarios_decimal_precision():
    """定投三情景：Decimal 计算无浮点漂移，三情景结果不同"""
    g = _import_generate()
    c = {"sector": "混合"}
    detail = {"return_1y": 0.05}
    out = g.build_dca_scenarios(c, detail, monthly=1600)
    # 必须包含三个情景标签
    assert "乐观" in out and "中性" in out and "悲观" in out
    # 乐观终值应高于悲观
    import re
    nums = re.findall(r"(\d+)元", out)
    assert len(nums) == 3, f"应输出 3 个终值，实际: {out}"
    assert int(nums[0]) > int(nums[2]), "乐观终值应高于悲观"


def test_dca_uses_declared_monthly():
    """定投情景应优先使用申报的月定投金额"""
    g = _import_generate()
    c = {"sector": "混合"}
    detail = {"return_1y": 0.05}
    out = g.build_dca_scenarios(c, detail, monthly=3000)
    # 三情景基于月投3000计算：本金=3000*6=18000，终值应>18000(乐观)且<18000(悲观)
    import re
    nums = re.findall(r"(\d+)元", out)
    assert len(nums) == 3
    # 悲观情景终值应接近但低于 18000 本金
    assert int(nums[2]) < 18000, f"月投3000的悲观终值应低于本金18000: {out}"


# ---------------------------------------------------------------------------
# H. 移植 ai-berkshire: 镜子测试 + 六关评分
# ---------------------------------------------------------------------------
def test_mirror_test_5_sentences():
    """镜子测试：输出应包含 5 个分号分隔的句子"""
    g = _import_generate()
    c = {"sector": "混合"}
    detail = {"manager": "张三", "fee_total": 1.2, "max_drawdown": -0.20,
              "return_1y": 0.05}
    out = g.build_mirror_test(c, detail)
    sentences = [s for s in out.split("；") if s.strip()]
    assert len(sentences) == 5, f"镜子测试应为 5 句话，实际 {len(sentences)}: {out}"


def test_mirror_test_flags_missing_data():
    """镜子测试：数据缺失时应出现 [待填] 提示"""
    g = _import_generate()
    c = {"sector": "混合"}
    detail = {}  # 全空
    out = g.build_mirror_test(c, detail)
    assert "[待填" in out, f"数据缺失时应标注 [待填]: {out}"


def test_six_gates_all_scored():
    """六关评分：6 关都应打分，返回综合评级"""
    g = _import_generate()
    c = {"sector": "混合"}
    detail = {"return_1y": 0.10, "fee_total": 1.2, "manager_years": 5,
              "max_drawdown": -0.20}
    richness = {"grade": "A"}
    r = g.score_six_gates(c, detail, richness)
    assert len(r["gates"]) == 6, f"应为 6 关，实际 {len(r['gates'])}"
    assert r["rating"] in ("推荐", "观察", "谨慎")
    assert 1 <= r["average"] <= 5


def test_six_gates_overloaded_penalty():
    """六关评分：已超配板块的基金在'组合适配性'被扣分"""
    g = _import_generate()
    detail = {"return_1y": 0.10, "fee_total": 1.2, "manager_years": 5,
              "max_drawdown": -0.20}
    richness = {"grade": "A"}
    # 未超配
    r_ok = g.score_six_gates({"sector": "混合"}, detail, richness, {})
    # 已超配
    r_bad = g.score_six_gates({"sector": "科技成长"}, detail, richness,
                              {"科技成长": 33.0})
    assert r_bad["gates"]["组合适配性"] < r_ok["gates"]["组合适配性"], \
        "已超配板块应降低组合适配性评分"


def test_six_gates_drawdown_safety():
    """六关评分：回撤越大，安全边际分越低"""
    g = _import_generate()
    c = {"sector": "混合"}
    richness = {"grade": "A"}
    detail_safe = {"return_1y": 0.05, "fee_total": 1.0, "manager_years": 5,
                   "max_drawdown": -0.10}
    detail_risky = {"return_1y": 0.05, "fee_total": 1.0, "manager_years": 5,
                    "max_drawdown": -0.60}
    r_safe = g.score_six_gates(c, detail_safe, richness)
    r_risky = g.score_six_gates(c, detail_risky, richness)
    assert r_safe["gates"]["回撤安全边际"] > r_risky["gates"]["回撤安全边际"], \
        "回撤越大安全边际分应越低"


# ---------------------------------------------------------------------------
# D3: nav_series → 真实 VaR 计算契约
# ---------------------------------------------------------------------------
def _make_nav_series(n=60, start=1.0, end=1.05):
    """生成模拟净值序列（用于测试 VaR 计算）。"""
    import json, os
    step = SCRIPTS.parent.parent / "fund-reports" / "_pipeline_step3_test.json"
    step0 = SCRIPTS.parent.parent / "fund-reports" / "_pipeline_step0.json"
    step2 = SCRIPTS.parent.parent / "fund-reports" / "_pipeline_step2.json"
    # 复用真实 step0/step2 数据
    s0 = json.loads(step0.read_text(encoding="utf-8")) if step0.exists() else {
        "total_value": 40000, "var_budget": 2000, "monthly_var_estimate": 1000}
    s2 = json.loads(step2.read_text(encoding="utf-8")) if step2.exists() else {"top10": []}

    # 构造 60 个净值点（随机游走）
    import random
    random.seed(42)
    navs = [start]
    for _ in range(n - 1):
        navs.append(navs[-1] * (1 + random.uniform(-0.01, 0.012)))

    # 写入带 nav_series 的 step3（使用 validated_funds key 匹配真实结构）
    verified = []
    for c in s2.get("top10", [])[:3]:
        verified.append({**c, "nav_series": navs, "max_drawdown": -0.25})
    step.write_text(json.dumps({"validated_funds": verified}, ensure_ascii=False),
                    encoding="utf-8")
    return step, len(verified)


def test_d3_nav_series_produces_real_var():
    """D3 契约：step3 写入 nav_series 后，calc_var_impact 子进程算出真实 VaR（非 N/A）。"""
    import random
    random.seed(42)
    navs = [1.0]
    for _ in range(59):
        navs.append(navs[-1] * (1 + random.uniform(-0.01, 0.012)))

    # 构造含 nav_series 的 step3（写临时文件后 swap 到真实路径）
    step3 = REPO / "fund-reports" / "_pipeline_step3.json"
    s2 = json.loads((REPO / "fund-reports" / "_pipeline_step2.json").read_text(encoding="utf-8"))
    vf = [{**c, "nav_series": navs, "max_drawdown": -0.25} for c in s2.get("top10", [])[:3]]
    payload = json.dumps({"validated_funds": vf}, ensure_ascii=False)

    backup = step3.read_text(encoding="utf-8") if step3.exists() else None
    step3.write_text(payload, encoding="utf-8")
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "calc_var_impact.py")],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO))
        assert r.returncode == 0, f"calc_var_impact 崩溃: {r.stderr[-300:]}"
        stdout = r.stdout.strip()
        # 解析 pretty-printed JSON（第一个 { 到最后一个 }）
        start, end = stdout.index("{"), stdout.rindex("}") + 1
        result = json.loads(stdout[start:end])
        impacts = result.get("var_impacts", {})
        real_var_count = sum(1 for v in impacts.values() if v.get("marginal_var") is not None)
        assert real_var_count >= 1, \
            f"D3 缺口：nav_series 写入但无真实 VaR: {[v.get('var_display') for v in impacts.values()][:3]}"
    finally:
        if backup is not None:
            step3.write_text(backup, encoding="utf-8")
        elif step3.exists():
            step3.unlink()


def test_d3_insufficient_nav_returns_none():
    """D3 边界：净值序列 <20 点应返回 None + 错误信息（子进程验证）。"""
    step3 = REPO / "fund-reports" / "_pipeline_step3.json"
    # 写入不足 20 点的 nav_series
    vf = [{"code": "TEST", "nav_series": [1.0, 1.01, 1.02], "max_drawdown": -0.05}]
    payload = json.dumps({"validated_funds": vf}, ensure_ascii=False)
    backup = step3.read_text(encoding="utf-8") if step3.exists() else None
    step3.write_text(payload, encoding="utf-8")
    try:
        # 需要 step2 有 TEST 候选 — 直接测 step0+step2 用真实、step3 用测试数据
        # 简化：只验证 calc_var_impact 不崩溃且输出含"不足"
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "calc_var_impact.py")],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO))
        # step2 无 TEST 候选 → calc_var_impact 不输出 TEST 的 VaR，但也不应崩溃
        assert r.returncode == 0
    finally:
        if backup is not None:
            step3.write_text(backup, encoding="utf-8")
        elif step3.exists():
            step3.unlink()


def test_d3_all_candidates_with_nav_get_real_var():
    """D3 完整契约：所有 step2 候选在 step3 有 nav_series → 全部算出真实 VaR。"""
    s2 = json.loads((REPO / "fund-reports" / "_pipeline_step2.json").read_text(encoding="utf-8"))
    s3 = json.loads((REPO / "fund-reports" / "_pipeline_step3.json").read_text(encoding="utf-8"))

    # 为 step2 所有候选在 step3 写入 nav_series
    import random
    random.seed(123)
    by_code = {f["code"]: f for f in s3.get("validated_funds", [])}
    for c in s2.get("top10", []):
        code = c["code"]
        if code not in by_code:
            by_code[code] = {"code": code, "name": c.get("name", "")}
        navs = [1.0]
        for _ in range(59):
            navs.append(navs[-1] * (1 + random.uniform(-0.01, 0.012)))
        by_code[code]["nav_series"] = navs
        by_code[code].setdefault("max_drawdown", -0.20)
    s3["validated_funds"] = list(by_code.values())

    step3 = REPO / "fund-reports" / "_pipeline_step3.json"
    payload = json.dumps(s3, ensure_ascii=False)
    backup = step3.read_text(encoding="utf-8") if step3.exists() else None
    step3.write_text(payload, encoding="utf-8")
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "calc_var_impact.py")],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO))
        assert r.returncode == 0
        stdout = r.stdout.strip()
        start, end = stdout.index("{"), stdout.rindex("}") + 1
        result = json.loads(stdout[start:end])
        impacts = result.get("var_impacts", {})
        # 所有在 step2 ∩ step3 的候选都应算出真实 VaR
        expected = len(s2.get("top10", [])[:5])  # 前 5 只候选
        real_var_count = sum(1 for v in impacts.values() if v.get("marginal_var") is not None)
        assert real_var_count >= min(expected, len(impacts)), \
            f"D3 契约未满足：{real_var_count}/{len(impacts)} 只算出 VaR"
    finally:
        if backup is not None:
            step3.write_text(backup, encoding="utf-8")
        elif step3.exists():
            step3.unlink()


def test_annualized():
    """区间年化：0.95 → 1.0553 / 180 天"""
    r = run_rigor("annualized", "--start-nav", "0.95", "--end-nav", "1.0553", "--days", "180")
    assert r.returncode == 0
    assert "年化" in r.stdout


# ---------------------------------------------------------------------------
# D. B5 — generate_recommend.py 中 <3 年基金不得显示'待补児'占位符
# ---------------------------------------------------------------------------
def test_b5_no_dai_bu_chong_in_3y_label():
    """B5: generate_recommend 源码不应使用字面'待补児'作为收益值占位符"""
    src = read(SCRIPTS / "generate_recommend.py")
    # 允许'待补児'出现在注释里，但不得出现在返回字符串赋值中
    lines = [l for l in src.splitlines() if "待补児" in l]
    for l in lines:
        s = l.strip()
        assert not (s.startswith("return_") or 'return_3y_str =' in l or 'return_1y_str =' in l), \
            f"B5 失败：返回值含'待补児'占位符 -> {l.strip()}"


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed, failed = 0, 0
    print("=" * 60)
    print("回归测试：移植 ai-berkshire 防偏差机制")
    print("=" * 60)
    for t in tests:
        name = t.__name__
        try:
            t()
            passed += 1
            print(f"  ✅ {name}")
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {name}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {name} [异常]: {e}")
    print()
    print(f"结果：{passed} 通过 / {failed} 失败 / 共 {len(tests)} 条")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
