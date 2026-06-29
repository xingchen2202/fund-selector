# P1 研究发现

## 根因分析

### 问题现象
2026-06-29 的推荐报告中：
- 024120 中邮核心主题混合C：规模 44.81万（0.004481亿），出现在推荐中
- 002214 中海沪港深价值优选混合A：规模 3877.78万（0.387亿），出现在推荐中
- 020362 中海沪港深价值优选混合C：规模 744.35万（0.074亿），出现在推荐中

### 代码分析

**screen_candidates.py 第68-69行**：
```python
if "规模（亿元）" in candidates.columns:
    candidates = candidates[candidates["规模（亿元）"] >= 2]
```

这段代码的意图是筛选规模 ≥ 2 亿的基金，但条件 `if "规模（亿元）" in candidates.columns` 检查 Excel 中是否存在"规模（亿元）"列。

### Excel 文件分析

**文件**：`fund_screening_corrected_20260624.xlsx`  
**Sheet**：`1-防守型(推荐定投)`  
**列数**：21列  
**实际列名**：

| 索引 | 列名 |
|------|------|
| 0 | 序号 |
| 1 | 基金代码 |
| 2 | 基金简称 |
| 3 | 日期 |
| 4 | 单位净值 |
| 5 | 累计净值 |
| 6 | 日涨跌幅 |
| 7 | 近1周 |
| 8 | 近1月 |
| 9 | 近3月 |
| 10 | 近6月 |
| 11 | 近1年 |
| 12 | 近2年 |
| 13 | 近3年 |
| 14 | 今年以来 |
| 15 | 成立以来 |
| 16 | 成立以来收益 |
| 17 | 费率 |
| 18 | 主题分类 |
| 19 | 风险分类 |
| 20 | 综合得分 |

**结论**：Excel 不含任何规模相关字段，筛选条件永远为 False。

### 调用链分析

```
SKILL.md Step 2
  → python screen_candidates.py
    → 读取 Excel（无规模列）
    → if "规模（亿元）" in columns: → False → 跳过筛选
    → 输出 top10（含小规模基金）
  → Claude 调用 MCP get_fund_info()（仅获取基本信息，未检查规模）
  → 生成报告（含不合格基金）
```

### 关键缺陷

1. **screen_candidates.py**：依赖 Excel 中不存在的列做筛选
2. **SKILL.md**：Step 2 和 Step 3 之间无规模验证步骤
3. **validate_funds.py**：是模板脚本，实际由 Claude 手动调用 MCP，但未要求规模检查
4. **rule-definitions.md**：虽然定义了"基金规模下限 2 亿"，但未说明如何获取规模数据

## 修复方案对比

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A. Python 直接调用 AKShare | 在 screen_candidates.py 中直接 import akshare 获取规模 | 自动化，不依赖 Claude | AKShare 首次调用慢（10秒+）；脚本职责膨胀 |
| B. SKILL.md 增加 Step 2.5 | 在 SKILL.md 中要求 Claude 调用 MCP 获取规模并过滤 | 职责清晰；利用已有 MCP 工具；尽早排除减少后续调用 | 依赖 Claude 执行 |
| C. 修改 Excel 文件 | 在 Excel 中添加规模列 | 不需要额外 MCP 调用 | Excel 是历史快照，规模数据会过时 |

**推荐方案 B**：SKILL.md 增加 Step 2.5。

理由：
1. MCP 工具（cn-mutual-fund）已提供 `get_fund_info()` 接口，返回"最新规模"字段
2. 由 Claude 执行，职责清晰
3. 尽早排除不合格候选，减少 Step 3 的 MCP 调用次数
4. 不修改 Excel 文件（保持历史快照的纯粹性）

## 相关文件路径

- `.claude/skills/fund-recommend/scripts/screen_candidates.py` — 筛选脚本
- `.claude/skills/fund-recommend/SKILL.md` — Skill 定义
- `.claude/skills/fund-recommend/scripts/validate_funds.py` — 验证模板
- `.claude/skills/_shared/rule-definitions.md` — 规则定义
- `fund_screening_corrected_20260624.xlsx` — Excel 候选池

---

# P3 研究发现

## 根因分析

### 问题现象
2026-06-29 的推荐报告中：
- 3 只推荐基金的新闻均未写入报告正文（显示"无"）
- VaR 影响数值来自临时估算，非 `calc_var_impact.py` 的输出

### 数据流断裂点

```
当前数据流（断裂）：

load_portfolio.py ──stdout──→ Claude 读取 → 数据在对话上下文中
screen_candidates.py ─stdout──→ Claude 读取 → 数据在对话上下文中
validate_funds.py ──模板输出──→ Claude 调用 MCP → 数据未写入文件 ❌
calc_var_impact.py ──未运行──→ Claude 手动估算 → 数据未写入文件 ❌
search_news.py ──模板输出──→ Claude 调用 Tavily → 数据未写入文件 ❌
                    ↓
generate_recommend.py ← 读取一个 JSON（仅含约束+候选）
                    ↓
报告缺少 VaR + 新闻 → 显示"无"/"N/A"
```

### 关键缺陷

1. **validate_funds.py**：模板脚本，实际数据由 Claude 手动获取，但从未写入文件
2. **calc_var_impact.py**：从未被实际运行，Claude 在对话中手动估算
3. **search_news.py**：模板脚本，Claude 通过 Tavily MCP 获取新闻，但未写入文件
4. **generate_recommend.py**：只接受一个 JSON 参数，无法接收多脚本输出
5. **SKILL.md Step 7**：只运行 `generate_recommend.py`，没有先运行验证/计算/搜索脚本

### 修复方案

引入 `_pipeline_data.json` 作为统一数据总线：

```
修复后数据流：

screen_candidates.py → stdout JSON → Claude 读取并写入 pipeline["candidates"]
validate_funds.py → 读取 pipeline → 调用 MCP → 写入 pipeline["funds"]
calc_var_impact.py → 读取 pipeline → 计算 → 写入 pipeline["var"]
search_news.py → 读取 pipeline → 调用 Tavily → 写入 pipeline["news"]
                    ↓
generate_recommend.py --pipeline → 读取完整 pipeline → 生成完整报告
```

### 设计决策

| 决策点 | 选项 A | 选项 B | 选择 |
|--------|--------|--------|------|
| 数据传递方式 | 文件（_pipeline_data.json） | Claude 上下文传递 | A（可靠、可调试） |
| 写入方式 | 每个脚本覆写整个文件 | 每个脚本只写自己字段 | B（解耦、可独立运行） |
| generate_recommend 接口 | 只读 pipeline | 兼容旧单文件模式 | A+B（--pipeline 标志） |
| 执行顺序 | SKILL.md 硬编码 | 脚本自己检测依赖 | A（简单可控） |

---

# P4 研究发现

## 根因分析

### 问题现象
2026-06-29 的推荐报告中：
- 020362 中海沪港深价值优选混合C：成立日期 2024-01-12，报告标注"近3年：+51.71%"
- 该 +51.71% 是成立以来收益（约2.5年），非真正的3年收益

### MCP 数据分析

调用 `get_fund_info("020362")` 返回：
```json
{
  "成立时间": "2024-01-12",
  "业绩表现": [
    {"周期": "成立以来", "本产品区间收益": 51.71},
    {"周期": "近1年", "本产品区间收益": 23.85}
  ]
}
```

**关键发现**：
1. MCP 返回的数据中没有明确的"3年收益"字段
2. "51.71%" 属于 `"周期": "成立以来"` 的收益
3. 报告生成时 Claude 将"成立以来"收益误标为"近3年"

### 代码分析

**validate_funds.py** 当前不获取成立日期：
```python
# 当前代码
result = {
    "return_3y": None,  # 始终为 None，未填充
    ...
}
```

**generate_recommend.py** 直接使用 MCP 数据：
```python
# Claude 在 SKILL.md 流程中调用 get_fund_info() 获取"3年收益"
# 但未检查基金成立时间，直接标注为"近3年"
```

### 修复方案

1. **validate_funds.py**：从 AKShare 获取"成立日期"字段
2. 计算成立年限，不满3年的标注为"成立以来（X年X月）"
3. **generate_recommend.py**：区分字符串标签和数值

### 设计决策

| 决策点 | 选项 A | 选项 B | 选择 |
|--------|--------|--------|------|
| 数据来源 | AKShare 获取成立日期 | MCP get_fund_info 获取 | A（已在 AKShare 调用流程中） |
| 不满3年标注 | 修改 return_3y 字段为字符串 | 新增 period_note 字段 | A+B（return_3y 存标签，period_note 存说明） |
| 满3年基金 | return_3y 为 None，由 MCP 填充 | 直接由 AKShare 计算 | A（AKShare 净值历史 API 不稳定） |
