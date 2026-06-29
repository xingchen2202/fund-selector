# P1 修复任务：规模筛选失效

## 任务概述

**问题**：`screen_candidates.py` 未按 `rule-definitions.md` 的规则排除规模 < 2 亿的基金。  
**根因**：Excel 候选池文件 `fund_screening_corrected_20260624.xlsx` 不含"规模"列，筛选条件永远为 False。  
**修复方案**：在 `screen_candidates.py` 中增加 AKShare 实时规模验证（与 MCP 同数据源），排除 < 2 亿基金。

**触发案例**：2026-06-29 推荐报告中出现 024120（44.81万）和 002214（3877万），均远低于 2 亿下限。

---

## Phase 1：根因确认 ✅

- [x] 检查 Excel 列名 → 确认无规模字段（21列，只有净值/收益率/得分）
- [x] 检查 `screen_candidates.py` 第68行 → `if "规模（亿元）" in candidates.columns` 始终 False
- [x] 确认 `validate_funds.py` 是模板脚本，实际由 Claude 调用 MCP

**发现**：
- Excel 列：序号/基金代码/基金简称/日期/单位净值/累计净值/日涨跌幅/近1周-近3年/今年以来/成立以来/成立以来收益/费率/主题分类/风险分类/综合得分
- 无"规模（亿元）"列 → 筛选条件跳过 → 小规模基金混入结果

---

## Phase 2：修复设计 ✅

### 最终实施方案

采用 **AKShare 直接调用**方案（与 cn-mutual-fund MCP 共享同一数据源），在 `screen_candidates.py` 内置 `validate_scale()` 函数。

**选定 AKShare API**：`ak.fund_individual_basic_info_xq(symbol=code)` → 返回 `item/value` 两列，`最新规模` 字段含规模字符串。

**实际代码变更**：
```python
SCALE_THRESHOLD_WAN = 20000  # 2亿 = 20000万元

def get_fund_scale_wan(fund_code):
    """通过 AKShare 获取基金规模（万元），失败返回 None"""
    import akshare as ak
    df = ak.fund_individual_basic_info_xq(symbol=fund_code)
    scale_row = df[df["item"] == "最新规模"]
    scale_str = str(scale_row["value"].values[0])
    if "万" in scale_str:
        return float(scale_str.replace("万", ""))
    elif "亿" in scale_str:
        return float(scale_str.replace("亿", "")) * 10000

def validate_scale(candidates_list):
    """规模验证，返回 (通过列表, 排除列表)"""
    ...
```

### 修改文件

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `screen_candidates.py` | 新增 `get_fund_scale_wan()` + `validate_scale()` | P0 |
| `SKILL.md` | Step 2 筛选逻辑增加第5步"实时规模验证" | P0 |
| `rule-definitions.md` | 增加规模验证补充说明 | P0 |

---

## Phase 3：实施 ✅

### 修改文件清单

| 文件 | 修改内容 | 状态 |
|------|---------|------|
| `screen_candidates.py` | 新增 `get_fund_scale_wan()` / `validate_scale()` / stderr 日志 | ✅ |
| `SKILL.md` | Step 2 筛选逻辑更新为6步（含规模验证） | ✅ |
| `rule-definitions.md` | 新增"规模验证补充说明"章节 | ✅ |
| `evals/evals.json` | 3条自动化断言（B1/B2/B3） | ✅ |

### 实施步骤

1. ✅ 更新 `screen_candidates.py`：内置 AKShare 规模验证
2. ✅ 更新 `SKILL.md`：Step 2 筛选逻辑更新
3. ✅ 更新 `rule-definitions.md`：规模验证说明
4. ✅ 创建 `evals/evals.json`：P1 断言

---

## Phase 4：验证 ✅

### 验收标准

- [x] 024120（规模44.81万）被排除，原因"规模不足2亿"
- [x] 002214（规模3877万）被排除，原因"规模不足2亿"
- [x] 020362（规模744.35万）被排除，原因"规模不足2亿"
- [x] 排除日志写入 stderr

### 测试结果

#### 修复前（baseline: recommend_20260629.txt）
- ❌ 024120（44.81万）出现在推荐
- ❌ 002214（3877万）出现在推荐
- ❌ 020362（744.35万）出现在推荐

#### 修复后
- ✅ 024120（44.81万）→ EXCLUDED: 规模44.81万 < 20000万（2亿）阈值
- ✅ 002214（3877.78万）→ EXCLUDED: 规模3877.78万 < 20000万
- ✅ 020362（744.35万）→ EXCLUDED: 规模744.35万 < 20000万
- ✅ 额外排除：019171（3302万）、019170（9669万）、019330（6106万）
- ⚠️ 保留待人工核实：022083、022084（AKShare 接口异常）

#### 修复后候选基金（规模均 ≥ 2亿）
| 代码 | 规模（万元） | 规模（亿） |
|------|-------------|-----------|
| 003593 | 44,200 | 4.42 |
| 166001 | 289,300 | 28.93 |
| 001881 | 38,900 | 3.89 |
| 005787 | 38,300 | 3.83 |
| 018167 | 33,100 | 3.31 |
| 018168 | 109,500 | 10.95 |
| 018927 | 110,700 | 11.07 |

---

## 决策记录

| 决策 | 理由 |
|------|------|
| Python 脚本无法直接调用 MCP | MCP 工具仅通过 MCP 协议对 Claude 可见，Python 进程无 MCP 访问权限 |
| 采用 AKShare 直接调用 | 与 cn-mutual-fund MCP 共享同一数据源，效果等同 |
| 不修改 Excel 文件 | Excel 是历史快照，不应依赖它存储实时数据 |
| 规模验证放在 Step 2 末尾 | 尽早排除不合格候选，减少后续 Step 3 的 MCP 调用次数 |
| AKShare 异常时保留基金 | 避免因接口故障误排除优质基金，标注"待人工核实" |

---

## 总结

**P1 修复完成**。根因（Excel 无规模列）→ 修复（AKShare 实时验证）→ 验证（6只小规模基金被排除）。
