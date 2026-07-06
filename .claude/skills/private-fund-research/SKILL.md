---
name: private-fund-research
description: >
  研究非公开募集的基金，使用替代数据和关联方分析
  when_to_use: 用户询问相关基金研究问题时触发
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily mcp__node_repl
effort: high
---


研究非公开募集的基金（私募股权、私募基金、专项计划）。

## 触发
"私募研究"、"XX 私募怎么样"、"非公开基金"

## 流程
1. 替代数据源：企查协/天眼查 + 关联方分析
2. 管理人背景：核心团队 + 历史项目
3. 底层资产穿透：项目质量 + 现金流
4. 风险评级：流动性 + 杠杆 + 集中度
5. A/B/C 级数据丰富度分级

## 输出
- 管理透画像
- 底层资产质量
- 风险评级 + 数据可信度

## 工具依赖
- `mcp__cn-mutual-fund` — 基金信息/净值/经理/持仓获取
- `mcp__cn-financial` — A股行情/宏观/行业数据
- `tools/financial_rigor.py` — Decimal 精度验算（verify-scale/cross-validate）

## 失败处理
- MCP 超时/异常 → 标注"数据不可用"并继续，不中止整体流程
- MCP 返回陈旧数据（如 2014 年北向资金）→ 标注异常跳过该维度
- 全部 MCP 失败 → 输出"当前无法获取实时数据，请稍后重试"
