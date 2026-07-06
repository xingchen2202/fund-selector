---
name: portfolio-review
description: >
  分析当前组合的仓位、相关性、再平衡需求
  when_to_use: 用户询问相关基金研究问题时触发
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily mcp__node_repl
effort: high
---


分析当前组合的仓位、相关性、再平衡需求。

## 触发
"持仓分析"、"组合管理"、"仓位调整"

## 流程
1. 当前组合总览：总市值 + 板块分布
2. 相关性检查：前三大持仓相关性矩阵
3. 再平衡触发：单一资产偏离目标 >10%
4. 机会成本：持有 vs 换仓的预期收益对比
5. 风险预算：VaR 利用率

## 输出
- 组合结构 + 偏离度
- 再平衡建议（卖出/买入标的 + 金额）
- 风险提示

## 工具依赖
- `mcp__cn-mutual-fund` — 基金信息/净值/经理/持仓获取
- `mcp__cn-financial` — A股行情/宏观/行业数据
- `tools/financial_rigor.py` — Decimal 精度验算（verify-scale/cross-validate）

## 失败处理
- MCP 超时/异常 → 标注"数据不可用"并继续，不中止整体流程
- MCP 返回陈旧数据（如 2014 年北向资金）→ 标注异常跳过该维度
- 全部 MCP 失败 → 输出"当前无法获取实时数据，请稍后重试"
