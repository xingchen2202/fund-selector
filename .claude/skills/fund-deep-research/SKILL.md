---
name: fund-deep-research
description: >
  对单只基金进行全面深度研究，输出结构化分析报告
  when_to_use: 用户询问相关基金研究问题时触发
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily mcp__node_repl
effort: high
---


对单只基金进行全面深度研究，输出结构化分析报告。

## 触发
"XX 基金怎么样"、"深度研究 XX"、"全面分析 XX"

## 流程
1. MCP 获取基金基本信息、净值历史、经理信息、十大持仓
2. 穿透分析：重仓股财务质量 + 行业配置 + 风格稳定性
3. 六关评分（能力圈/经济特征/护城河/管理层/安全边际/估值）
4. 镜子测试（5 句话说清投资逻辑）
5. 反向测试（若判断错误，最可能原因）

## 输出
- 基本面：规模/经理/费率/业绩/回撤
- 穿透：重仓股质量 + 行业集中度
- 六关评分（★1-5）+ 综合评级
- 风险提示 + 逆向思考

## 工具依赖
- `mcp__cn-mutual-fund` — 基金信息/净值/经理/持仓获取
- `mcp__cn-financial` — A股行情/宏观/行业数据
- `tools/financial_rigor.py` — Decimal 精度验算（verify-scale/cross-validate）

## 失败处理
- MCP 超时/异常 → 标注"数据不可用"并继续，不中止整体流程
- MCP 返回陈旧数据（如 2014 年北向资金）→ 标注异常跳过该维度
- 全部 MCP 失败 → 输出"当前无法获取实时数据，请稍后重试"
