---
name: fund-series
description: >
  为目标基金/行业生成 8 篇系列研报（约 120k 字）
  when_to_use: 用户询问相关基金研究问题时触发
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily mcp__node_repl
effort: high
---


为目标基金/行业生成 8 篇系列研报（约 120k 字，公众号可发）。

## 触发
"XX 行业系列"、"系列研报"、"深度覆盖"

## 系列规划
1. 行业总览：产业链图谱 + 市场规模
2. 上游环节：原材料/设备/技术
3. 中游环节：制造/组装/集成
4. 下游环节：应用/渠道/终端
5. 龙头公司深度
6. 竞争格局：市场份额 + 壁垒
7. 投资逻辑：核心假设 + 催化剂
8. 风险提示：政策/技术/市场

## 流程
1. Team Lead 启动 4 Agent 并行覆盖不同环节
2. 各环节独立研究 + 数据验证
3. 编辑 Agent 润色统一风格
4. 审阅 Agent 质量把关

## 输出
- 8 篇系列文章（每篇 ~15k 字）
- 数据附录 + 来源标注

## 工具依赖
- `mcp__cn-mutual-fund` — 基金信息/净值/经理/持仓获取
- `mcp__cn-financial` — A股行情/宏观/行业数据
- `tools/financial_rigor.py` — Decimal 精度验算（verify-scale/cross-validate）

## 失败处理
- MCP 超时/异常 → 标注"数据不可用"并继续，不中止整体流程
- MCP 返回陈旧数据（如 2014 年北向资金）→ 标注异常跳过该维度
- 全部 MCP 失败 → 输出"当前无法获取实时数据，请稍后重试"
