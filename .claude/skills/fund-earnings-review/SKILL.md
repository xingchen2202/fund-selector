---
name: fund-earnings-review
description: >
  解读基金定期报告：季报、半年报、年报
  when_to_use: 用户询问相关基金研究问题时触发
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily mcp__node_repl
effort: high
---


解读基金定期报告：季报、半年报、年报。

## 触发
"季报解读"、"年报分析"、"业绩点评"

## 流程
1. MCP 获取定期报告数据
2. 关键指标变化：规模变动 + 持仓调整 + 业绩归因
3. 风格漂移检测：行业配置变化 + 仓位波动
4. 重仓股变动：新增/剔除 + 增减仓
5. 展望与风险：基金经理观点 + 市场判断

## 输出
- 关键指标变动表
- 持仓调整分析
- 风格稳定性评估
- 风险提示

## 工具依赖
- `mcp__cn-mutual-fund` — 基金信息/净值/经理/持仓获取
- `mcp__cn-financial` — A股行情/宏观/行业数据
- `tools/financial_rigor.py` — Decimal 精度验算（verify-scale/cross-validate）

## 失败处理
- MCP 超时/异常 → 标注"数据不可用"并继续，不中止整体流程
- MCP 返回陈旧数据（如 2014 年北向资金）→ 标注异常跳过该维度
- 全部 MCP 失败 → 输出"当前无法获取实时数据，请稍后重试"
