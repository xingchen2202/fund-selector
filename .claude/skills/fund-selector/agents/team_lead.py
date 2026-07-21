#!/usr/bin/env python3
"""Team Lead (Document-Driven Mode) - Generate 4 Master Perspective Prompts
----------------------------------------------------------------------
Inspired by ai-berkshire investment-team skill.

Reads step3 candidate funds, generates 4 perspective prompt files.
Claude reads these prompts and analyzes independently following the
skill documentation framework - no Python scoring scripts.

Usage:
    python agents/team_lead.py --input ../fund-reports/_pipeline_step3.json

Output:
    _agent_prompts/value_prompt.txt      - Buffett perspective
    _agent_prompts/growth_prompt.txt     - Duan Yongping perspective
    _agent_prompts/risk_prompt.txt       - Li Lu perspective
    _agent_prompts/cycle_prompt.txt      - Charlie Munger perspective
"""
import argparse
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32" and (not hasattr(sys.stdout, "encoding") or sys.stdout.encoding.lower() != "utf-8"):
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
    lines = [
        f"### {f.get('name', 'Unknown')} ({f.get('code', '')})",
        f"- Scale: {f.get('scale', 'N/A')} {f.get('scale_unit', 'yi')}",
        f"- Manager: {f.get('manager', 'TBD')} ({f.get('manager_years', '?')} yrs)",
        f"- Fee: {f.get('fee_total', 'N/A')}%",
        f"- 1Y Return: {f.get('return_1y', 'N/A')}",
        f"- 3Y Return: {f.get('return_3y', 'N/A')}",
        f"- Max Drawdown: {f.get('max_drawdown', 'N/A')}",
        f"- Fund Type: {f.get('fund_type', 'N/A')}",
        f"- Sector: {f.get('sector', 'Unknown')}",
    ]
    return "\n".join(lines)


def make_prompt(agent: str, perspective: str, philosophy: str, questions: str,
                funds: list, context: str) -> str:
    funds_md = "\n\n".join(fund_to_markdown(f) for f in funds)
    return f"""You are a research assistant from the **{agent}** perspective. Analyze the following funds independently.

## Your Investment Philosophy
{philosophy}

## Portfolio Context
{context}

## Candidate Funds
{funds_md}

## Your Analysis Tasks
{questions}

## Output Requirements
1. Rate each fund **1-5 stars** (5 = strong recommend)
2. Write **2-3 sentences of specific reasoning** for each fund (must cite specific data like "scale 2.89B", "1Y return +4.9%")
3. Select **one top pick** + reasoning (within 100 words)
4. Overall judgment (within 50 words)

## Output Format
```json
{{
  "agent": "{agent}",
  "rankings": [
    {{"code": "xxxxxx", "name": "xxx", "stars": 4, "reason": "specific reasoning (cite data)"}}
  ],
  "top_pick": "xxxxxx",
  "summary": "overall judgment"
}}
```

Output JSON only, no explanation.
"""


def main():
    parser = argparse.ArgumentParser(description="Team Lead - Generate 4 master perspective prompts")
    parser.add_argument("--input", default=str(REPORTS_DIR / "_pipeline_step3.json"))
    args = parser.parse_args()

    funds = load_step3(Path(args.input))
    if not funds:
        print("[ERROR] step3 has no candidate funds", file=sys.stderr)
        sys.exit(1)

    PROMPTS_DIR.mkdir(exist_ok=True)

    # Portfolio context
    step0_path = REPORTS_DIR / "_pipeline_step0.json"
    context = "A-share mutual fund portfolio"
    if step0_path.exists():
        step0 = json.loads(step0_path.read_text(encoding="utf-8"))
        tv = step0.get("total_value", 0)
        vb = step0.get("var_budget_remaining", 0)
        overloaded = step0.get("overloaded_sectors", {})
        context = f"Total value: {tv:,.0f} RMB, VaR budget: {vb}, overloaded sectors: {', '.join(overloaded.keys()) if overloaded else 'none'}"

    perspectives = [
        {
            "filename": "value_prompt.txt",
            "agent": "Buffett",
            "perspective": "Value Investing (Business Quality + Margin of Safety)",
            "philosophy": "Buy wonderful companies at fair prices. Focus on the FUNDAMENTAL QUALITY of the fund's underlying holdings: wide moat (brand/switching cost/scale), durable competitive advantage, high ROE (>15%), strong free cash flow, low debt. The fund is only as good as the businesses it owns — penetrate to the holdings and assess business quality.",
            "questions": """1. Business quality: Penetrate to the top holdings — do they have wide moats? High ROE? Strong free cash flow? Sustainable competitive advantage?
2. Margin of safety: Is the fund's holdings collectively priced at a discount to intrinsic value? Where does the current NAV rank in 1/3 year history?
3. Management quality: Does the fund manager demonstrate capital allocation discipline? Low turnover? Long-term orientation? No style drift?
4. Rate 1-5 stars + reasoning (2-3 sentences, cite specific data like "top holding ROE 22%", "avg debt ratio 35%")
5. Would you own this portfolio of businesses at the current price?""",
        },
        {
            "filename": "growth_prompt.txt",
            "agent": "Duan Yongping",
            "perspective": "Business Essence (Business Model + Moat)",
            "philosophy": "Do the right things and do them right. Focus: Is the underlying business good (real demand + sustainable)? Is the moat wide (brand/switching cost/scale)? Is the fee honest? Is the scale disciplined? No style drift or chasing hot themes.""",
            "questions": """1. Business model: Is the underlying business good? Does it earn 'the right money'?
2. Moat: Does the fund manager's stock selection logic have a moat? Is it within their circle of competence?
3. Integrity: Are fees honest? Is the scale disciplined? Any 'wrong things' (style drift, chasing trends)?
4. Rate 1-5 stars + reasoning (2-3 sentences, cite specific data)
5. Is this a fund that 'does the right things'?""",
        },
        {
            "filename": "risk_prompt.txt",
            "agent": "Li Lu",
            "perspective": "Risk Signals (Maximum Risk + Management Quality)",
            "philosophy": "First consider what could go wrong. Focus: What is the maximum risk (drawdown in extreme scenarios)? Management quality (integrity + capability)? Uncertainties ('unknown unknowns')? Data transparency?""",
            "questions": """1. Maximum risk: What is the most likely source of loss? How much could drawdown be in extreme scenarios?
2. Management quality: Any integrity issues? Are interests aligned with shareholders?
3. Uncertainties: What are the 'unknown unknowns'? Is data transparent enough?
4. Rate 1-5 stars (5 = lowest risk) + risk warnings (2-3 sentences, cite specific data)
5. Can you bear the maximum loss?""",
        },
        {
            "filename": "cycle_prompt.txt",
            "agent": "Munger",
            "perspective": "Industry Landscape (Competition + Cycle Position)",
            "philosophy": "Invert, always invert. Focus: What cycle stage is the industry in (recovery/expansion/decline)? Is the competition landscape clear (is the leader obvious)? What is the market consensus (could it be wrong)? Any overlooked risks or opportunities?""",
            "questions": """1. Industry landscape: What cycle stage is the fund's main sector in? Is the competition clear?
2. Invert: What is the market consensus? Could it be wrong? Any overlooked risks or opportunities?
3. Multidisciplinary: Examine the fund's logic from psychology/biology/mathematics perspectives
4. Rate 1-5 stars + reasoning (2-3 sentences, cite specific data)
5. Is this a good time to 'buy and hold'?""",
        },
    ]

    for p in perspectives:
        content = make_prompt(p["agent"], p["perspective"], p["philosophy"], p["questions"], funds, context)
        (PROMPTS_DIR / p["filename"]).write_text(content, encoding="utf-8")
        print(f"[Team Lead] Generated {p['filename']} ({p['agent']} perspective)", file=sys.stderr)

    print(f"\n[Team Lead] Done. Next: Claude reads 4 prompts and analyzes independently.", file=sys.stderr)


if __name__ == "__main__":
    main()
