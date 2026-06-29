#!/usr/bin/env python3
"""
pipeline.py — 独立步骤数据文件管理
━━━━━━━━━━━━━━━━━━━━
每个脚本写入独立的临时文件，避免竞争条件。
generate_recommend.py 读取所有文件合并。

文件命名：
  _pipeline_step0.json — load_portfolio 输出 (constraints)
  _pipeline_step2.json — screen_candidates 输出 (candidates)
  _pipeline_step3.json — validate_funds 输出 (validated_funds)
  _pipeline_step4.json — calc_var_impact 输出 (var_impacts)
  _pipeline_step5.json — search_news 输出 (news)
"""
import json
from pathlib import Path

# Path: fund-selector/.claude/skills/fund-recommend/scripts/pipeline.py
# Go up 5 levels to reach fund-selector/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
REPORTS_DIR = PROJECT_ROOT / "fund-reports"

STEP_FILES = {
    "step0": REPORTS_DIR / "_pipeline_step0.json",
    "step2": REPORTS_DIR / "_pipeline_step2.json",
    "step3": REPORTS_DIR / "_pipeline_step3.json",
    "step4": REPORTS_DIR / "_pipeline_step4.json",
    "step5": REPORTS_DIR / "_pipeline_step5.json",
}


def write_step(step_key, data):
    """写入对应步骤的临时文件（覆写模式，不读取现有内容）"""
    path = STEP_FILES[step_key]
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_step(step_key):
    """读取对应步骤的临时文件，不存在返回空 dict"""
    path = STEP_FILES[step_key]
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def read_all_steps():
    """读取所有步骤文件并合并为一个 dict"""
    merged = {}
    for key in ["step0", "step2", "step3", "step4", "step5"]:
        data = read_step(key)
        if isinstance(data, dict):
            merged.update(data)
    return merged


if __name__ == "__main__":
    # 测试：打印当前各步骤文件状态
    print(f"Reports dir: {REPORTS_DIR}")
    for key, path in STEP_FILES.items():
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        print(f"  {key}: {path.name} exists={exists} size={size}B")
