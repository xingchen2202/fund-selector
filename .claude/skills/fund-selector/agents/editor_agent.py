#!/usr/bin/env python3
"""编辑 Agent（Editor Agent）— 润色排版
━━━━━━━━━━━━━━━━━━━━
将研究初稿润色为公众号可发文章。

用法：
    python agents/editor_agent.py --input <初稿.md> --output <终稿.md>

风格规范：
- 标题：吸引眼球但不标题党
- 段落：每段不超过 5 行
- 数据：关键数据加粗
- 结尾：必须有免责声明
"""
import argparse
import sys
import io
from pathlib import Path

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    draft = Path(args.input).read_text(encoding="utf-8")

    # 这里只做标记，实际润色由 Claude 完成
    prompt = f"""请将以下研究初稿润色为公众号可发文章。

## 润色要求
1. 标题：吸引眼球但不标题党（不超过 20 字）
2. 开头：用 1-2 句话抓住读者（痛点/好奇心）
3. 正文：每段不超过 5 行，关键数据加粗
4. 结尾：总结观点 + 免责声明
5. 风格：专业但不枯燥，像和朋友聊天

## 初稿
{draft}

## 输出
直接输出润色后的 Markdown 全文。
"""

    Path(args.output).write_text(prompt, encoding="utf-8")
    print(f"[编辑 Agent] 润色指令已写入 {args.output}")


if __name__ == "__main__":
    main()
