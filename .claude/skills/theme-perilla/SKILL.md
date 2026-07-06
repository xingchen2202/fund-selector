---
name: theme-perilla
description: >
  紫苏叶主题瓶颈分析。输入热门概念（AI算力/新能源/半导体/机器人等），
  构建产业链图谱，用紫苏叶五因子模型评分瓶颈节点，推荐相关基金和股票。
  移植自 Serenity股神紫苏叶理论（Bilibili BV1fT7z6QE2S）。
when_to_use: >
  用户问"紫苏叶分析 XX"、"XX 产业链瓶颈"、"AI 瓶颈节点投资"、
  "新能源紫苏叶"、"半导体瓶颈"、"机器人产业链分析"时触发。
disable-model-invocation: false
user-invocable: true
allowed-tools: Read Write Bash Python mcp__cn-financial mcp__cn-mutual-fund mcp__tavily
effort: high
---

# 紫苏叶主题瓶颈分析

> **理念来源**：Serenity股神紫苏叶理论（[BV1fT7z6QE2S](https://www.bilibili.com/video/BV1fT7z6QE2S)）
>
> **核心思想**：不追 AI 巨头（金枪鱼大腹），寻找被忽视的"瓶颈节点"（紫苏叶）。

---

## 触发

- "紫苏叶分析 XX"、"XX 产业链瓶颈"
- "AI 瓶颈节点"、"新能源紫苏叶"、"半导体瓶颈"
- "机器人产业链分析"、"创新药瓶颈"

## 输入

热门概念/主题，如：
- "AI算力"
- "新能源"
- "半导体"
- "机器人"
- "创新药"

---

## 五因子瓶颈评分模型

| 因子 | 标准 | 分值 |
|------|------|------|
| 细分市占率 | 行业前3 | 3分 |
| 毛利率 | > 30% | 3分 |
| 机构持仓 | < 10%（被忽视）| 3分 |
| 技术/认证壁垒 | 难以替代 | 3分 |
| 产能约束 | 供给弹性低 | 3分 |

**评级标准**：
- **≥ 12/15**：紫苏叶级（战略稀缺）→ 强烈推荐
- **9-11/15**：潜在瓶颈 → 关注
- **< 9/15**：普通持仓 → 观望

---

## 工作流

### Step 1: 产业链图谱构建

1. 检查 `references/industry-chains/{theme}.md` 是否存在
2. 若存在，直接读取产业链图谱
3. 若不存在，使用 MCP 搜索构建：
   - `mcp__cn-financial__search_stock` 或 `mcp__tavily__tavily_search`
   - 构建上游/中游/下游各环节
   - 各环节上市公司列表

### Step 2: 五因子评分

对产业链中每只候选股票调用 MCP：
- `get_financial_indicators(stock_code)` → 毛利率、ROE
- `get_institutional_holdings(stock_code)` → 机构持仓比例
- `get_company_profile(stock_code)` → 行业地位、技术壁垒
- 結合 `references/industry-chains/{theme}.md` 的行业知识

按五因子模型评分，输出每只股票的紫苏叶得分。

### Step 3: 瓶颈节点筛选

- 评分 ≥ 12/15 → 紫苏叶级瓶颈节点
- 评分 9-11 → 潜在瓶颈
- 评分 < 9 → 排除

### Step 4: 关联基金发现

1. 对每个瓶颈节点，搜索重仓该股票的基金：
   - `get_fund_portfolio(fund_code)` → 检查前十大持仓
2. 计算基金的"紫苏叶指数"：
   - 重仓股平均紫苏叶得分 × 持仓集中度
3. 推荐紫苏叶指数 ≥ 70 的基金

### Step 5: 输出报告

按 `reports/report-template.md` 格式输出完整分析报告。

---

## 工具依赖

| 工具 | 用途 |
|------|------|
| `mcp__cn-financial` | 股票财务/估值/行业数据 |
| `mcp__cn-mutual-fund` | 基金持仓/信息 |
| `mcp__tavily__tavily_search` | 产业链信息搜索 |
| `scripts/perilla_scorer.py` | 五因子评分脚本 |
| `scripts/industry_chain.py` | 产业链图谱构建助手 |
| `scripts/bottleneck_mapper.py` | 瓶颈发现与基金关联 |

---

## 失败处理

- MCP 超时/异常 → 标注"数据不可用"并跳过该维度
- 产业链数据不足 → 标注"需补充研究"
- 全部 MCP 失败 → 输出"当前无法获取实时数据，请稍后重试"

---

## 参考资料

| 文件 | 内容 |
|------|------|
| `references/perilla-framework.md` | 紫苏叶理论完整说明 |
| `references/industry-chains/ai-computing.md` | AI 算力产业链 |
| `references/industry-chains/new-energy.md` | 新能源产业链 |
| `references/industry-chains/semiconductor.md` | 半导体产业链 |
| `references/industry-chains/robotics.md` | 机器人产业链（待补充）|

---

## 注意事项

- 持仓数据来自基金季报，**滞后一个季度**
- 产业链图谱为参考，实际数据以 MCP 实时查询为准
- 始终附带免责声明
