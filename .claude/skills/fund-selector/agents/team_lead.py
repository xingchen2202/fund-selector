#!/usr/bin/env python3
"""Team Lead — 多 Agent 对抗式投研调度器
━━━━━━━━━━━━━━━━━━━━
读取 step3 候选基金，生成 4 大师视角 Agent 的 prompt 文件，
供 Claude 通过 Agent 工具并行调度。

用法：
    python agents/team_lead.py --input ../fund-reports/_pipeline_step3.json

输出：
    _agent_prompts/value_prompt.txt      — 巴菲特视角
    _agent_prompts/growth_prompt.txt     — 段永平视角
    _agent_prompts/risk_prompt.txt       — 李录视角
    _agent_prompts/cycle_prompt.txt      — 芒格视角
    _agent_prompts/synthesis_plan.json   — 综合指令
"""
import argparse
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
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
    """将基金数据转为 Markdown 供 Agent 阅读."""
    lines = [
        f"### {f.get('name', '未知')}（{f.get('code', '')}）",
        f"- 规模：{f.get('scale', 'N/A')} {f.get('scale_unit', '亿')}",
        f"- 经理：{f.get('manager', '待确认')}（{f.get('manager_years', '?')} 年）",
        f"- 总费率：{f.get('fee_total', 'N/A')}%",
        f"- 近1年收益：{f.get('return_1y', 'N/A')}",
        f"- 近3年收益：{f.get('return_3y', 'N/A')}",
        f"- 最大回撤：{f.get('max_drawdown', 'N/A')}",
        f"- 板块：{f.get('sector', '未知')}",
        f"- 净值序列长度：{len(f.get('nav_series', []))} 个点",
    ]
    return "\n".join(lines)


def make_value_prompt(funds: list, portfolio_context: str) -> str:
    """巴菲特视角：财务质量 + 估值安全边际."""
    funds_md = "\n\n".join(fund_to_markdown(f) for f in funds)
    return f"""你是沃伦·巴菲特的投研助手。请基于以下基金数据，从**价值投资**视角独立分析。

## 组合背景
{portfolio_context}

## 候选基金
{funds_md}

## 分析要求
1. 财务质量：规模是否够大？费率是否够低？经理是否稳定？
2. 估值安全边际：当前净值在近 1 年/3 年历史中的分位如何？
3. 护城河：基金经理的超额收益能力是否可持续？
4. 给出 1-5 星评级 + 推荐理由（200 字内）
5. 明确标注：你是否愿意把这只基金纳入自己的组合？

## 输出格式
```json
{{
  "agent": "value",
  "rankings": [
    {{"code": "xxxxxx", "stars": 4, "reason": "...", "would_own": true}}
  ],
  "top_pick": "xxxxxx",
  "summary": "整体判断（100 字）"
}}
```

只输出 JSON，不要解释。
"""


def make_growth_prompt(funds: list, portfolio_context: str) -> str:
    """段永平视角：商业模式 + 护城河."""
    funds_md = "\n\n".join(fund_to_markdown(f) for f in funds)
    return f"""你是段永平的投研助手。请基于以下基金数据，从**生意本质**视角独立分析。

## 组合背景
{portfolio_context}

## 候选基金
{funds_md}

## 分析要求
1. 商业模式：这只基金投资的底层生意好不好？赚的是不是"对的钱"？
2. 护城河：基金经理的选股逻辑有没有护城河？是不是在能力圈内？
3. 本分：费率是否诚实？规模是否克制？有没有做"不对的事"（风格漂移、追热点）？
4. 给出 1-5 星评级 + 推荐理由（200 字内）
5. 明确标注：这是不是"做对的事情"的基金？

## 输出格式
```json
{{
  "agent": "growth",
  "rankings": [
    {{"code": "xxxxxx", "stars": 4, "reason": "...", "doing_right_thing": true}}
  ],
  "top_pick": "xxxxxx",
  "summary": "整体判断（100 字）"
}}
```

只输出 JSON，不要解释。
"""


def make_risk_prompt(funds: list, portfolio_context: str) -> str:
    """李录视角：风险信号 + 管理质量."""
    funds_md = "\n\n".join(fund_to_markdown(f) for f in funds)
    return f"""你是李录的投研助手。请基于以下基金数据，从**风险信号**视角独立分析。

## 组合背景
{portfolio_context}

## 候选基金
{funds_md}

## 分析要求
1. 最大风险：这只基金最可能的亏损来源是什么？极端行情下回撤会到多少？
2. 管理质量：基金经理有没有诚信污点？利益是否与持有人一致？
3. 不确定性：有哪些"不知道的未知"？数据是否足够透明？
4. 给出 1-5 星评级（5 星=风险可控）+ 风险提示（200 字内）
5. 明确标注：最大亏损能否承受？

## 输出格式
```json
{{
  "agent": "risk",
  "rankings": [
    {{"code": "xxxxxx", "stars": 4, "max_loss_acceptable": true, "reason": "..."}}
  ],
  "top_pick": "xxxxxx",
  "risk_flags": ["code: 风险描述"],
  "summary": "整体判断（100 字）"
}}
```

只输出 JSON，不要解释。
"""


def make_cycle_prompt(funds: list, portfolio_context: str) -> str:
    """芒格视角：行业格局 + 竞争态势."""
    funds_md = "\n\n".join(fund_to_markdown(f) for f in funds)
    return f"""你是查理·芒格的投研助手。请基于以下基金数据，从**行业格局**视角独立分析。

## 组合背景
{portfolio_context}

## 候选基金
{funds_md}

## 分析要求
1. 行业格局：这只基金重仓的行业处于什么周期阶段？竞争格局清晰吗？
2. 逆向思考：市场共识是什么？共识错了吗？有没有被忽视的风险或机会？
3. 多元思维：用心理学/生物学/数学等不同角度审视这只基金的投资逻辑
4. 给出 1-5 星评级 + 推荐理由（200 字内）
5. 明确标注：当前是"买入并持有"的好时机吗？

## 输出格式
```json
{{
  "agent": "cycle",
  "rankings": [
    {{"code": "xxxxxx", "stars": 4, "reason": "...", "good_timing": true}}
  ],
  "top_pick": "xxxxxx",
  "summary": "整体判断（100 字）"
}}
```

只输出 JSON，不要解释。
"""


def main():
    parser = argparse.ArgumentParser(description="Team Lead — 生成 4 大师视角 Agent prompts")
    parser.add_argument("--input", default=str(REPORTS_DIR / "_pipeline_step3.json"))
    args = parser.parse_args()

    funds = load_step3(Path(args.input))
    if not funds:
        print("[ERROR] step3 无候选基金", file=sys.stderr)
        sys.exit(1)

    PROMPTS_DIR.mkdir(exist_ok=True)

    # 组合背景（从 step0 读取）
    step0_path = REPORTS_DIR / "_pipeline_step0.json"
    portfolio_context = "A 股公募基金组合"
    if step0_path.exists():
        step0 = json.loads(step0_path.read_text(encoding="utf-8"))
        tv = step0.get("total_value", 0)
        vb = step0.get("var_budget_remaining", 0)
        overloaded = step0.get("overloaded_sectors", {})
        portfolio_context = f"总市值 ¥{tv:,.0f}，VaR 预算 ¥{vb}，已超配板块：{', '.join(overloaded.keys()) if overloaded else '无'}"

    # 生成 4 个 prompt 文件
    prompts = {
        "value_prompt.txt": make_value_prompt(funds, portfolio_context),
        "growth_prompt.txt": make_growth_prompt(funds, portfolio_context),
        "risk_prompt.txt": make_risk_prompt(funds, portfolio_context),
        "cycle_prompt.txt": make_cycle_prompt(funds, portfolio_context),
    }

    for name, content in prompts.items():
        p = PROMPTS_DIR / name
        p.write_text(content, encoding="utf-8")
        print(f"[Team Lead] 生成 {p.name} ({len(content)} 字)", file=sys.stderr)

    # 综合指令
    synth = {
        "instruction": "4 Agent 并行完成后，运行 synthesize.py 合并结果",
        "agents": list(prompts.keys()),
        "output": str(REPORTS_DIR / "_agent_synthesized.json"),
    }
    synth_path = PROMPTS_DIR / "synthesis_plan.json"
    synth_path.write_text(json.dumps(synth, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[Team Lead] 完成。下一步：", file=sys.stderr)
    print(f"  1. 并行读取 4 个 prompt 文件", file=sys.stderr)
    print(f"  2. 通过 Agent 工具分别调度 4 个视角", file=sys.stderr)
    print(f"  3. 运行 synthesize.py 合并", file=sys.stderr)


if __name__ == "__main__":
    main()
