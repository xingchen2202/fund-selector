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
