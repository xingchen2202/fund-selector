#!/usr/bin/env python3
"""
pipeline.py — 独立步骤文件管理
━━━━━━━━━━━━━━━━━━━━
每个脚本写入独立的临时文件，避免竞争条件。
generate_recommend.py 读取所有文件合并。

文件命名（语义化）：
  _pipeline_step0_constraints.json — load_portfolio 输出
  _pipeline_step1_macro.json       — Claude MCP 宏观数据
  _pipeline_step2_candidates.json  — screen_candidates 输出
  _pipeline_step3_funds.json       — Claude MCP 基金验证数据
  _pipeline_step3_akshare.json     — validate_funds AKShare 补充
  _pipeline_step4_var.json         — calc_var_impact 输出
  _pipeline_step5_news.json        — search_news 输出
"""
import json
from pathlib import Path

# Path: fund-selector/.claude/skills/fund-recommend/scripts/pipeline.py
# Go up 5 levels to reach fund-selector/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
REPORTS_DIR = PROJECT_ROOT / "fund-reports"

# 语义化 step 文件命名
STEP_FILES = {
    "step0": REPORTS_DIR / "_pipeline_step0_constraints.json",
    "step1": REPORTS_DIR / "_pipeline_step1_macro.json",
    "step2": REPORTS_DIR / "_pipeline_step2_candidates.json",
    "step3": REPORTS_DIR / "_pipeline_step3_funds.json",
    "step3_akshare": REPORTS_DIR / "_pipeline_step3_akshare.json",
    "step4": REPORTS_DIR / "_pipeline_step4_var.json",
    "step5": REPORTS_DIR / "_pipeline_step5_news.json",
}


def write_step(step_key, data):
    """写入对应步骤的临时文件（覆写模式）"""
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
    for key in ["step0", "step1", "step2", "step3", "step3_akshare", "step4", "step5"]:
        data = read_step(key)
        if isinstance(data, dict):
            merged.update(data)
    return merged


def get_step_path(step_key):
    """获取步骤文件路径"""
    return STEP_FILES.get(step_key)


if __name__ == "__main__":
    # 测试：打印当前各步骤文件状态
    print(f"Reports dir: {REPORTS_DIR}")
    for key, path in STEP_FILES.items():
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        print(f"  {key}: {path.name} exists={exists} size={size}B")
