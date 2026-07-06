#!/usr/bin/env python3
"""Team Lead（文档驱动模式）— 生成 4 大师视角 prompt
━━━━━━━━━━━━━━━━━━━━
移植自 ai-berkshire investment-team skill。

读取 step3 候选基金，生成 4 个视角的 prompt 文件。
Claude 读取这些 prompt 后，**直接按照 skill 文档的框架独立分析**，
不调用 Python 评分脚本——分析质量由 Claude 的推理能力保证。

用法：
    python agents/team_lead.py --input ../fund-reports/_pipeline_step3.json

输出：
    _agent_prompts/value_prompt.txt      — 巴菲特视角
    _agent_prompts/growth_prompt.txt     — 段永平视角
    _agent_prompts/risk_prompt.txt       — 李录视角
    _agent_prompts/cycle_prompt.txt      — 芒格视角
"""
import argparse
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "fund-reports"
PROMPTS_DIR = REPORTS_DIR / "_agent_prompts"


def load_step3(path: Path) -> list:
    if not path.exists():
        print(f"[ERROR] step3 not found: {path}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("validated_funds", [])


def fund_to_markdown(f: dict) -> str:
    """将基金数据转为 Markdown 供 Claude 阅读."""
    lines = [
        f"### {f.get('name', '未知')}（{f.get('code', '')}）",
        f"- 规模：{f.get('scale', 'N/A')} {f.get('scale_unit', '亿')}",
        f"- 经理：{f.get('manager', '待确认')}（{f.get('manager_years', '?')} 年）",
        f"- 总费率：{f.get('fee_total', 'N/A')}%",
        f"- 近1年收益：{f.get('return_1y', 'N/A')}",
        f"- 近3年收益：{f.get('return_3y', 'N/A')}",
        f"- 最大回撤：{f.get('max_drawdown', 'N/A')}",
        f"- 基金类型：{f.get('fund_type', 'N/A')}",
        f"- 板块：{f.get('sector', '未知')}",
    ]
    return "\n".join(lines)


def make_perspective_prompt(agent_name: str, perspective: str, philosophy: str,
                             questions: str, funds: list, context: str) -> str:
    """生成单个视角的 prompt."""
    funds_md = "\n\n".join(fund_to_markdown(f) for f in funds)
    return f"""你是 **{agent_name}** 的投研助手。请基于以下基金数据，从 **{perspective}** 视角独立分析。

## 你的投资哲学
{philosophy}

## 组合背景
{context}

## 候选基金
{funds_md}

## 你的分析任务
{questions}

## 输出要求
1. 对每只基金给出 **1-5 星评级**（5 星=强烈推荐）
2. 每只基金写 **2-3 句具体理由**（必须引用具体数据，如"规模 28.93 亿"、"近 1 年 +4.9%"）
3. 选出 **首推基金**（1 只）+ 理由（100 字内）
4. 整体判断（50 字内）

## 输出格式
```json
{{
  "agent": "{agent_name}",
  "rankings": [
    {{"code": "xxxxxx", "name": "xxx", "stars": 4, "reason": "具体理由（引用数据）"}}
  ],
  "top_pick": "xxxxxx",
  "summary": "整体判断"
}}
```

只输出 JSON，不要解释。
"""


def main():
    parser = argparse.ArgumentParser(description="Team Lead — 生成 4 大师视角 prompt（文档驱动）")
    parser.add_argument("--input", default=str(REPORTS_DIR / "_pipeline_step3.json"))
    args = parser.parse_args()

    funds = load_step3(Path(args.input))
    if not funds:
        print("[ERROR] step3 无候选基金", file=sys.stderr)
        sys.exit(1)

    PROMPTS_DIR.mkdir(exist_ok=True)

    # 组合背景
    step0_path = REPORTS_DIR / "_pipeline_step0.json"
    context = "A 股公募基金组合"
    if step0_path.exists():
        step0 = json.loads(step0_path.read_text(encoding="utf-8"))
        tv = step0.get("total_value", 0)
        vb = step0.get("var_budget_remaining", 0)
        overloaded = step0.get("overloaded_sectors", {})
        context = f"总市值 ¥{tv:,.0f}，VaR 预算 ¥{vb}，已超配：{', '.join(overloaded.keys()) if overloaded else '无'}"

    # 4 个视角的定义
    perspectives = [
        {
            "filename": "value_prompt.txt",
            "name": "巴菲特",
            "perspective": "价值投资（财务质量 + 估值安全边际）",
            "philosophy": "以合理价格买入优秀企业。关注：规模够大（>10亿）、费率够低（<1.5%）、经理够稳定（>3年）、回撤可控（<30%）、业绩持续跑赢基准。",
            "questions": """1. 财务质量：规模是否够大？费率是否够低？经理是否稳定？
2. 估值安全边际：当前净值在近1年/3年历史中的分位如何？
3. 护城河：基金经理的超额收益能力是否可持续？
4. 给出 1-5 星评级 + 推荐理由（2-3 句，引用具体数据）
5. 明确标注：你是否愿意把这只基金纳入自己的组合？""",
        },
        {
            "filename": "growth_prompt.txt",
            "name": "段永平",
            "perspective": "生意本质（商业模式 + 护城河）",
            "philosophy": "做对的事情，把事情做好。关注：底层生意好不好（真实需求+可持续）、护城河宽不宽（品牌/转换成本/规模效应）、本分不本分（费率诚实、规模克制、不追热点）。",
            "questions": """1. 商业模式：这只基金投资的底层生意好不好？赚的是不是"对的钱"？
2. 护城河：基金经理的选股逻辑有没有护城河？是不是在能力圈内？
3. 本分：费率是否诚实？规模是否克制？有没有做"不对的事"（风格漂移、追热点）？
4. 给出 1-5 星评级 + 推荐理由（2-3 句，引用具体数据）
5. 明确标注：这是不是"做对的事情"的基金？""",
        },
        {
            "filename": "risk_prompt.txt",
            "name": "李录",
            "perspective": "风险信号（最大风险 + 管理质量）",
            "philosophy": "先考虑什么会出错。关注：最大风险是什么（极端行情回撤）、管理质量（诚信+能力）、不确定性（"不知道的未知"）、数据透明度。",
            "questions": """1. 最大风险：这只基金最可能的亏损来源是什么？极端行情下回撤会到多少？
2. 管理质量：基金经理有没有诚信污点？利益是否与持有人一致？
3. 不确定性：有哪些"不知道的未知"？数据是否足够透明？
4. 给出 1-5 星评级（5星=风险可控）+ 风险提示（2-3 句，引用具体数据）
5. 明确标注：最大亏损能否承受？""",
        },
        {
            "filename": "cycle_prompt.txt",
            "name": "芒格",
            "perspective": "行业格局（竞争态势 + 周期位置）",
            "philosophy": "反过来想，总是反过来想。关注：行业处于什么周期阶段（复苏/扩张/衰退）、竞争格局清晰不清晰（龙头是否明确）、市场共识是什么（共识错了吗）、有没有被忽视的风险或机会。",
            "questions": """1. 行业格局：这只基金重仓的行业处于什么周期阶段？竞争格局清晰吗？
2. 逆向思考：市场共识是什么？共识错了吗？有没有被忽视的风险或机会？
3. 多元思维：用心理学/生物学/数学等不同角度审视这只基金的投资逻辑
4. 给出 1-5 星评级 + 推荐理由（2-3 句，引用具体数据）
5. 明确标注：当前是"买入并持有"的好时机吗？""",
        },
    ]

    for p in perspectives:
        content = make_perspective_prompt(
            p["name"], p["perspective"], p["philosophy"], p["questions"], funds, context
        )
        (PROMPTS_DIR / p["filename"]).write_text(content, encoding="utf-8")
        print(f"[Team Lead] 生成 {p['filename']}（{p['name']}视角）", file=sys.stderr)

    print(f"\n[Team Lead] 完成。下一步：Claude 并行读取 4 个 prompt 并独立分析。", file=sys.stderr)


if __name__ == "__main__":
    main()
