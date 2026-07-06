#!/usr/bin/env python3
"""审阅 Agent（Reviewer Agent）— 读者视角挑刺
━━━━━━━━━━━━━━━━━━━━
以读者视角审阅文章，挑出逻辑漏洞、事实错误、表述不清。

用法：
    python agents/reviewer_agent.py --input <文章.md>

审阅维度：
1. 事实核查：数据是否准确？来源是否标注？
2. 逻辑核查：推理是否自洽？有没有跳跃？
3. 表述核查：有没有歧义？有没有废话？
4. 风险核查：免责声明是否充分？
"""
import argparse
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    article = Path(args.input).read_text(encoding="utf-8")

    prompt = f"""你是一个挑剔的读者。请审阅以下文章，找出所有问题。

## 审阅维度
1. **事实核查**：数据是否准确？来源是否标注？有没有编造？
2. **逻辑核查**：推理是否自洽？有没有跳跃？因果是否成立？
3. **表述核查**：有没有歧义？有没有废话？段落是否太长？
4. **风险核查**：免责声明是否充分？有没有承诺收益？

## 文章
{article}

## 输出格式
```json
{{
  "score": 85,
  "issues": [
    {{"type": "fact", "line": 12, "issue": "数据未标注来源", "fix": "添加来源"}},
    {{"type": "logic", "line": 25, "issue": "因果跳跃", "fix": "补充中间推理"}}
  ],
  "verdict": "可发布/需修改"
}}
```

只输出 JSON。
"""

    out_path = Path(args.input).with_suffix(".review.json")
    out_path.write_text(prompt, encoding="utf-8")
    print(f"[审阅 Agent] 审阅指令已写入 {out_path}")


if __name__ == "__main__":
    main()
