#!/usr/bin/env python3
"""Eval 运行器 — 执行 evals.json 中的断言
━━━━━━━━━━━━━━━━━━━━
读取 evals.json，对每个 eval 执行 skill 并验证输出。

注意：此运行器验证 skill 文档的结构完整性（触发词、输出段落），
而非实际运行 MCP 调用（需要 Claude Code 环境）。

用法：
    python tests/evals/run_evals.py
"""

import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(r"C:\Users\22218\Desktop\fund-selector")
EVALS = REPO / ".claude/skills/fund-selector/evals/evals.json"
SKILLS_DIR = REPO / ".claude/skills/fund-selector/skills"


def load_evals() -> list:
    if not EVALS.exists():
        print(f"[ERROR] evals.json not found: {EVALS}")
        return []
    data = json.loads(EVALS.read_text(encoding="utf-8"))
    return data.get("evals", [])


def check_skill_exists(skill_name: str) -> bool:
    """检查 skill 文件是否存在（去掉前导 /）."""
    name = skill_name.lstrip("/")
    return (SKILLS_DIR / f"{name}.md").exists()


def check_skill_content(skill_name: str, assertions: list) -> dict:
    """检查 skill 文档是否包含断言要求的内容."""
    name = skill_name.lstrip("/")
    skill_path = SKILLS_DIR / f"{name}.md"
    if not skill_path.exists():
        return {"passed": False, "reason": f"skill file missing: {name}.md"}

    content = skill_path.read_text(encoding="utf-8")
    results = []
    all_passed = True

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
    print("Fund Selector — Skill Eval Runner")
    print("=" * 60)

    for ev in evals:
        eid = ev.get("id", "?")
        skill = ev.get("skill", "?")
        desc = ev.get("description", "")
        assertions = ev.get("assertions", [])

        # 检查 skill 文件存在
        if not check_skill_exists(skill):
            print(f"  ❌ {eid}: {skill} — skill 文件不存在")
            failed_skills.append(eid)
            continue

        # 检查内容断言
        result = check_skill_content(skill, assertions)
        if result["passed"]:
            passed += 1
            print(f"  ✅ {eid}: {skill}")
        else:
            failed_skills.append(eid)
            failed_checks = [c for c in result.get("checks", []) if not c["passed"]]
            print(f"  ❌ {eid}: {skill}")
            for fc in failed_checks:
                print(f"       └─ {fc['assertion']}")

    print()
    print(f"结果：{passed}/{total} 通过")
    if failed_skills:
        print(f"失败：{', '.join(failed_skills)}")
        sys.exit(1)
    else:
        print("✅ 全部通过")


if __name__ == "__main__":
    main()
