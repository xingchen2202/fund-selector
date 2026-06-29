#!/usr/bin/env python3
"""
pipeline.py — 统一数据总线
━━━━━━━━━━━━━━━━━━━━
fund-recommend 各脚本共享的中间数据存储。
文件位置：fund-reports/_pipeline_data.json

结构：
  {
    "candidates": [...],           // screen_candidates.py 写入
    "validated_funds": {...},      // validate_funds.py 写入
    "var_impacts": {...},          // calc_var_impact.py 写入
    "news": {...},                 // search_news.py 写入
    "constraints": {...},          // load_portfolio.py 写入
    "macro": {...}                 // get_macro.py 写入
  }
"""
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
PIPELINE_FILE = PROJECT_ROOT / "fund-reports" / "_pipeline_data.json"


def read_pipeline():
    """读取 pipeline 文件，不存在返回空 dict"""
    if PIPELINE_FILE.exists():
        with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def write_pipeline(key, data):
    """
    将 data 写入 pipeline[key]。
    保留其他字段，只更新指定 key。
    """
    pipeline = read_pipeline()
    pipeline[key] = data
    PIPELINE_FILE.parent.mkdir(exist_ok=True)
    with open(PIPELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(pipeline, f, ensure_ascii=False, indent=2)


def get_pipeline(key, default=None):
    """读取 pipeline 中指定 key 的值"""
    pipeline = read_pipeline()
    return pipeline.get(key, default)


if __name__ == "__main__":
    # 测试：打印当前 pipeline 状态
    pipeline = read_pipeline()
    print(f"Pipeline file: {PIPELINE_FILE}")
    print(f"Exists: {PIPELINE_FILE.exists()}")
    if pipeline:
        print(f"Keys: {list(pipeline.keys())}")
    else:
        print("Pipeline is empty or not found.")
