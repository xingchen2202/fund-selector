---
name: fund-earnings-team
description: >
  4 大师视角并行解读基金定期报告 + 编辑审阅
  when_to_use: 用户询问相关基金研究问题时触发
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily mcp__node_repl
effort: high
---


4 大师视角并行解读基金定期报告 + 编辑审阅 → 公众号可发文章。

## 触发
"多视角财报会"、"深度解读季报"

## 团队结构
| 阶段 | 角色 | 任务 |
|------|------|------|
| Phase 1 | 4 大师 Agent | 并行独立解读 |
| Phase 2 | Team Lead | 汇总冲突 + 综合研判 |
| Phase 3 | 编辑 Agent | 公众号风格润色 |
| Phase 4 | 审阅 Agent | 读者视角挑刺 |

## 流程
1. 获取报告原文（年报/季报/半年报）
2. 4 Agent 各自独立阅读 + 标注关键发现
3. Team Lead 汇总 4 视角（冲突标注）
4. 编辑 Agent 重写为流畅文章
5. 审阅 Agent 抽样验证事实

## 输出
- 4 视角独立点评
- 综合研判文章（公众号可发）
- 数据验证附录

## 工具依赖
- `mcp__cn-mutual-fund` — 基金信息/净值/经理/持仓获取
- `mcp__cn-financial` — A股行情/宏观/行业数据
- `tools/financial_rigor.py` — Decimal 精度验算（verify-scale/cross-validate）

## 失败处理
- MCP 超时/异常 → 标注"数据不可用"并继续，不中止整体流程
- MCP 返回陈旧数据（如 2014 年北向资金）→ 标注异常跳过该维度
- 全部 MCP 失败 → 输出"当前无法获取实时数据，请稍后重试"
