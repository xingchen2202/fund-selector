---
name: bottleneck-hunter
description: >
  识别产业链中的瓶颈环节和隐形冠军
  when_to_use: 用户询问相关基金研究问题时触发
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily mcp__node_repl
effort: high
---


识别产业链中的瓶颈环节和隐形冠军（二三线龙头）。

## 触发
"供应链瓶颈"、"隐形冠军"、"细分龙头"

## 流程
1. 选定目标行业
2. 产业链图谱分解（上游/中游/下游）
3. 瓶颈识别：供需缺口 + 技术壁垒 + 产能周期
4. 隐形冠军筛选：市占率前三 + 估值合理 + 订单饱满
5. 风险：技术替代 + 客户集中 + 原材料波动

## 输出
- 产业链图谱 + 瓶颈环节标注
- 隐形冠军列表 + 竞争格局
- 风险清单

## 工具依赖
- `mcp__cn-mutual-fund` — 基金信息/净值/经理/持仓获取
- `mcp__cn-financial` — A股行情/宏观/行业数据
- `tools/financial_rigor.py` — Decimal 精度验算（verify-scale/cross-validate）

## 失败处理
- MCP 超时/异常 → 标注"数据不可用"并继续，不中止整体流程
- MCP 返回陈旧数据（如 2014 年北向资金）→ 标注异常跳过该维度
- 全部 MCP 失败 → 输出"当前无法获取实时数据，请稍后重试"
