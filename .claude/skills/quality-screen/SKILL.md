---
name: quality-screen
description: >
  用 7 条硬规则 + 3 条豁免规则排除劣质基金
  when_to_use: 用户询问相关基金研究问题时触发
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily mcp__node_repl
effort: high
---


用 7 条硬规则 + 3 条豁免规则排除劣质基金。

## 触发
"质量筛选"、"排除坏基金"、"负面清单"

## 7 条硬规则（触发任一条即排除）
1. 近 10 年平均 ROE < 10%
2. 连续 3 年自由现金流为负
3. 利息保障倍数 < 3x
4. 毛利率连续 3 年下降
5. 现金/盈余质量 < 70%
6. 净利率 < 3%
7. 近 3 年股本稀释 > 15%

## 3 条豁免（硬规则触发但可豁免）
1. 处于大规模扩张期（资本开支 > 收入 30%）
2. 强周期行业底部（ROE 触底反弹中）
3. 无形资产驱动（品牌/专利估值未入账）

## 输出
- 排除列表 + 触发的规则
- 豁免清单 + 豁免理由
- 通过筛选的基金列表

## 工具依赖
- `mcp__cn-mutual-fund` — 基金信息/净值/经理/持仓获取
- `mcp__cn-financial` — A股行情/宏观/行业数据
- `tools/financial_rigor.py` — Decimal 精度验算（verify-scale/cross-validate）

## 失败处理
- MCP 超时/异常 → 标注"数据不可用"并继续，不中止整体流程
- MCP 返回陈旧数据（如 2014 年北向资金）→ 标注异常跳过该维度
- 全部 MCP 失败 → 输出"当前无法获取实时数据，请稍后重试"
