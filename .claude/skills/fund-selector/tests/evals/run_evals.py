#!/usr/bin/env python3
"""Eval 运行器 — 结构 + 引用 + 内容三层校验
━━━━━━━━━━━━━━━━━━━━
对比旧版（仅做文档字符串匹配），本版增加：
1. 结构完整性：每个 skill 必须具备 触发/流程/输出/工具依赖/失败处理 5 个段落
2. 工具引用可解析：tools/*.py 引用必须指向真实文件；MCP 引用必须使用已知服务器前缀
3. 内容断言（保留）：contains / contains_any / not_contains

注意：此运行器验证 skill 文档的结构完整性与引用正确性，
而非实际运行 MCP 调用（需要 Claude Code 环境）。
行为正确性（skill 执行时是否产出对应段落）由 skill-creator 的迭代 eval 覆盖。

用法：
    python tests/evals/run_evals.py
"""

import json
import re
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
EVALS = REPO / ".claude/skills/fund-selector/evals/evals.json"
SKILLS_DIR = REPO / ".claude/skills/fund-selector/skills"
TOOLS_DIR = REPO / ".claude/skills/fund-selector/tools"

# 已知的 MCP 服务器前缀（引用校验用）
KNOWN_MCP_PREFIXES = ("mcp__cn-financial", "mcp__cn-mutual-fund", "mcp__tavily", "mcp__node_repl")

# 每个 skill 文档必须具备的段落
REQUIRED_SECTIONS = ["触发", "流程", "输出", "工具依赖", "失败处理"]


def load_evals() -> list:
    if not EVALS.exists():
        print(f"[ERROR] evals.json not found: {EVALS}")
        return []
    data = json.loads(EVALS.read_text(encoding="utf-8"))
    return data.get("evals", [])


def check_skill_exists(skill_name: str) -> bool:
    name = skill_name.lstrip("/")
    return (SKILLS_DIR / f"{name}.md").exists()


def check_structure(content: str) -> dict:
    """检查 skill 文档是否具备完整的 5 个段落。"""
    missing = [s for s in REQUIRED_SECTIONS if s not in content]
    return {
        "passed": not missing,
        "missing_sections": missing,
    }


def check_tool_refs(content: str) -> dict:
    """检查 tools/*.py 引用是否指向真实文件，MCP 引用是否使用已知前缀。"""
    problems = []
    # 引用形式如 `tools/financial_rigor.py` 或 tools/xxx.py
    for ref in re.findall(r"tools/([a-z_]+\.py)", content):
        if not (TOOLS_DIR / ref).exists():
            problems.append(f"tools/{ref} 不存在")
    # MCP 引用：mcp__server__tool，校验 server 前缀
    for mcp in re.findall(r"mcp__([a-z-]+)__\w+", content):
        if f"mcp__{mcp}" not in KNOWN_MCP_PREFIXES:
            problems.append(f"未知 MCP 服务器: mcp__{mcp}")
    return {"passed": not problems, "problems": problems}


def check_skill_content(skill_name: str, assertions: list) -> dict:
    """检查 skill 文档的内容断言 + 结构 + 引用。"""
    name = skill_name.lstrip("/")
    skill_path = SKILLS_DIR / f"{name}.md"
    if not skill_path.exists():
        return {"passed": False, "reason": f"skill file missing: {name}.md"}

    content = skill_path.read_text(encoding="utf-8")
    results = []
    all_passed = True

    # 结构完整性
    struct = check_structure(content)
    results.append({"assertion": "结构完整(触发/流程/输出/工具依赖/失败处理)", "passed": struct["passed"],
                    "detail": f"缺失: {struct['missing_sections']}" if not struct["passed"] else ""})
    if not struct["passed"]:
        all_passed = False

    # 工具引用可解析
    refs = check_tool_refs(content)
    results.append({"assertion": "工具引用可解析", "passed": refs["passed"],
                    "detail": f"问题: {refs['problems']}" if not refs["passed"] else ""})
    if not refs["passed"]:
        all_passed = False

    # 内容断言
    for a in assertions:
        atype = a.get("type", "")
        value = a.get("value", "")
        desc = a.get("description", "")

        if atype == "contains":
            ok = value in content
        elif atype == "not_contains":
            ok = value not in content
        elif atype == "contains_any":
            ok = any(v in content for v in value)
        else:
            ok = True

        if not ok:
            all_passed = False
        results.append({"assertion": desc, "passed": ok})

    return {"passed": all_passed, "checks": results}


def main():
    evals = load_evals()
    if not evals:
        print("No evals to run.")
        return

    total = len(evals)
    passed = 0
    failed_skills = []

    print("=" * 60)
    print("Fund Selector — Skill Eval Runner (结构+引用+内容)")
    print("=" * 60)

    for ev in evals:
        eid = ev.get("id", "?")
        skill = ev.get("skill", "?")
        assertions = ev.get("assertions", [])

        if not check_skill_exists(skill):
            print(f"  ❌ {eid}: {skill} — skill 文件不存在")
            failed_skills.append(eid)
            continue

        result = check_skill_content(skill, assertions)
        if result["passed"]:
            passed += 1
            print(f"  ✅ {eid}: {skill}")
        else:
            failed_skills.append(eid)
            print(f"  ❌ {eid}: {skill}")
            for fc in result.get("checks", []):
                if not fc["passed"]:
                    detail = f" ({fc['detail']})" if fc.get("detail") else ""
                    print(f"       └─ {fc['assertion']}{detail}")

    print()
    print(f"结果：{passed}/{total} 通过")
    if failed_skills:
        print(f"失败：{', '.join(failed_skills)}")
        sys.exit(1)
    else:
        print("✅ 全部通过")


if __name__ == "__main__":
    main()
