---
name: news-pulse
description: >
  多 Agent 并行归因，10 分钟内输出涨跌原因
  when_to_use: 用户询问相关基金研究问题时触发
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily mcp__node_repl
effort: high
---


多 Agent 并行归因，10 分钟内输出涨跌原因。

## 触发
"快讯解读"、"为什么涨跌"、"新闻归因"

## 团队结构
| Agent | 覆盖范围 |
|-------|---------|
| 公司事件 Agent | 业绩预告/重组/大股东增减持 |
| 监管政策 Agent | 行业新规/窗口指导/处罚 |
| 行业竞品 Agent | 竞品动态/份额变化 |
| 市场情绪 Agent | 北向资金/融资融券/龙虎榜 |

## 流程
1. 获取涨跌幅异动（±5% 以上）
2. 4 Agent 并行 MCP 搜索
3. Team Lead 汇总归因
4. 生成解读报告

## 输出
- 异动归因（公司/政策/行业/情绪）
- 影响评估 + 后续关注点

## 工具依赖
- `mcp__cn-mutual-fund` — 基金信息/净值/经理/持仓获取
- `mcp__cn-financial` — A股行情/宏观/行业数据
- `tools/financial_rigor.py` — Decimal 精度验算（verify-scale/cross-validate）

## 失败处理
- MCP 超时/异常 → 标注"数据不可用"并继续，不中止整体流程
- MCP 返回陈旧数据（如 2014 年北向资金）→ 标注异常跳过该维度
- 全部 MCP 失败 → 输出"当前无法获取实时数据，请稍后重试"
