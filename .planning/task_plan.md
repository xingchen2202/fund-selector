# Task Plan — P5 MCP调用职责分离修复

## 背景

推荐报告中所有数据字段显示"待补充"，宏观周期判断显示"未知"，总市值显示"N/A"。
根因：Python脚本无法调用MCP工具，但pipeline重构后MCP调用逻辑被移入脚本。

## 当前执行流（断裂）

```
Step 1: Claude调用MCP → 数据在对话中 → 运行get_macro.py（模板，输出空数据）→ step1未写入
Step 2: screen_candidates.py → 写入step2 ✅
Step 3: validate_funds.py → 只获取AKShare数据，MCP字段为None → 写入step3（不完整）
Step 4: calc_var_impact.py → 读取step0+step2 → 写入step4 ✅（但total_value=N/A）
Step 5: search_news.py → 写入step5 ✅（但sector=未知导致新闻不匹配）
Step 7: generate_recommend.py → 合并所有step → 大量空字段
```

## 修复后目标执行流

```
Step 0: load_portfolio.py → 写入step0 ✅
Step 1: Claude调用MCP(get_macro_pmi等) → 写入step1（新）
Step 2: screen_candidates.py → 写入step2 ✅
Step 3: Claude调用MCP(get_fund_info等) → 写入step3（新）
Step 4: calc_var_impact.py → 读取step0+step2 → 写入step4 ✅
Step 5: search_news.py → 读取step2 → 写入step5 ✅
Step 6: generate_recommend.py → 合并step0-5 → 完整报告 ✅
```

## Phase 列表

| Phase | 描述 | 状态 | 依赖 |
|-------|------|------|------|
| Phase 1 | pipeline.py 扩展支持 step1/step3 | ✅ complete | 无 |
| Phase 2 | SKILL.md 重构 Step1+Step3 为 Claude MCP调用 | ✅ complete | Phase 1 |
| Phase 3 | get_macro.py 降级为纯格式化工具 | ✅ complete | Phase 1 |
| Phase 4 | validate_funds.py 降级为纯格式化工具 | ✅ complete | Phase 1 |
| Phase 5 | rule-definitions.md 新增架构约束 | ✅ complete | 无 |
| Phase 6 | evals.json 追加 P5 断言 | ✅ complete | Phase 2-4 |
| Phase 7 | 运行完整流水线验证 | ✅ complete | 全部 |

---

## Phase 1: pipeline.py 扩展

**目标**：pipeline.py 支持 step1 和 step3 文件

**修改**：
```python
STEP_FILES = {
    "step0": REPORTS_DIR / "_pipeline_step0.json",
    "step1": REPORTS_DIR / "_pipeline_step1.json",  # 新增
    "step2": REPORTS_DIR / "_pipeline_step2.json",
    "step3": REPORTS_DIR / "_pipeline_step3.json",  # 新增（原step3改为step3b）
    "step4": REPORTS_DIR / "_pipeline_step4.json",
    "step5": REPORTS_DIR / "_pipeline_step5.json",
}
```

**注意**：validate_funds.py 当前写入 step3，需改名为 step3b（AKShare数据），step3 留给 Claude MCP 数据。

或者更清晰的命名：
- `_pipeline_step1_macro.json` — Claude 写入的宏观数据
- `_pipeline_step3_funds.json` — Claude 写入的基金验证数据
- `_pipeline_step3_akshare.json` — Python 写入的 AKShare 数据（原 step3）

**决策**：使用语义化命名，避免数字混淆。

---

## Phase 2: SKILL.md 重构

**目标**：Step 1 和 Step 3 改为 Claude 主导 MCP 调用

### Step 1 改造（宏观数据）

**改造前**：
```
## Step 1：宏观环境判断
分别调用以下 MCP 工具...
然后运行：python get_macro.py
```

**改造后**：
```
## Step 1：宏观环境判断（Claude 执行）

1. 调用以下 MCP 工具（每个独立 try/catch）：
   - get_macro_pmi()
   - get_macro_money_supply()
   - get_valuation_metrics(symbol="000300", num_periods=60)
   - get_north_bound_flow()

2. 基于数据判断经济周期（参考 macro-cycle-guide.md）

3. 将结果写入 _pipeline_step1_macro.json：
   ```json
   {
     "pmi": {"available": true, "manufacturing": 51.2, ...},
     "money_supply": {...},
     "valuation": {...},
     "north_bound": {...},
     "cycle_judgment": {"phase": "复苏", "confidence": "中", "direction": "..."},
     "available_indicators": ["PMI", "M2"],
     "unavailable_indicators": ["北向资金"]
   }
   ```

4. 运行 python format_macro.py（格式化输出到 stderr）
```

### Step 3 改造（基金验证）

**改造前**：
```
## Step 3：候选基金验证
运行脚本：python validate_funds.py
对每只候选基金调用：get_fund_info() / get_fund_nav_history() / get_fund_portfolio()
```

**改造后**：
```
## Step 3：候选基金验证（Claude 执行）

1. 从 _pipeline_step2.json 读取 top10 候选列表

2. 对每只候选基金调用 cn-mutual-fund MCP：
   - get_fund_info(code) → 规模、经理、费率、成立日期
   - get_fund_nav_history(code, period="3y") → 计算近1年/近3年收益、最大回撤
   - get_fund_portfolio(code) → 前十大持仓

3. 将结果写入 _pipeline_step3_funds.json：
   ```json
   {
     "candidates": ["003593", "166001", ...],
     "verified": [
       {
         "code": "003593",
         "name": "国泰景气行业灵活配置混合",
         "scale_wan": 44200,
         "manager": "XXX",
         "fee": "1.5%",
         "return_1y": 5.55,
         "return_1y_label": "近1年",
         "return_3y": -12.86,
         "return_3y_label": "近3年",
         "max_drawdown": -19.94,
         "establishment_date": "2017-03-20",
         "age_years": 9,
         "age_months": 3,
         "top_holdings": [...]
       }
     ]
   }
   ```

4. 同时运行 python validate_funds.py（获取AKShare补充数据：规模验证）
   写入 _pipeline_step3_akshare.json
```

---

## Phase 3: get_macro.py 降级

**目标**：从"模板输出"改为"读取step1并格式化"

**修改**：
```python
def main():
    """读取 _pipeline_step1_macro.json，格式化输出到 stderr"""
    step1_file = REPORTS_DIR / "_pipeline_step1_macro.json"
    if not step1_file.exists():
        print("[WARN] step1 文件不存在，请先运行 Claude MCP 调用", file=sys.stderr)
        return

    with open(step1_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 格式化输出（供 Claude 确认数据完整性）
    cycle = data.get("cycle_judgment", {})
    print(f"[MACRO] 周期判断: {cycle.get('phase', '未知')} (置信度: {cycle.get('confidence', 'N/A')})")
    print(f"[MACRO] 可用指标: {', '.join(data.get('available_indicators', []))}")
    print(f"[MACRO] 不可用指标: {', '.join(data.get('unavailable_indicators', []))}")
```

---

## Phase 4: validate_funds.py 降级

**目标**：从"AKShare获取+空字段"改为"读取step3并补充AKShare"

**修改**：
```python
def main():
    """读取 _pipeline_step3_funds.json，补充 AKShare 数据，写入 step3_akshare"""
    step3_file = REPORTS_DIR / "_pipeline_step3_funds.json"
    if not step3_file.exists():
        print("[WARN] step3 文件不存在，请先运行 Claude MCP 调用", file=sys.stderr)
        return

    with open(step3_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # AKShare 补充验证（规模确认等）
    for fund in data.get("verified", []):
        code = fund.get("code", "")
        # 可选：用 AKShare 验证规模
        # 如果 MCP 已获取规模，此处跳过
        if fund.get("scale_wan") is None:
            fund["scale_wan"] = get_fund_scale_wan(code)

    write_step("step3_akshare", data)
```

---

## Phase 5: rule-definitions.md 新增架构约束

在文件末尾新增：

```markdown
---

## 三、架构约束（fund-recommend 铁律）

### MCP 调用职责分离

> **核心原则**：所有 MCP 工具调用必须由 Claude 执行，不得放入 Python 脚本。

**原因**：
- MCP 工具（cn-financial、cn-mutual-fund、tavily）是 Claude 内置工具
- Python subprocess 无法访问 MCP 工具
- 脚本中调用 MCP 会导致数据获取失败，显示"待补充"

**职责分工**：

| 执行者 | 职责 |
|--------|------|
| Claude | 调用 MCP 工具（get_macro_pmi, get_fund_info 等）|
| Claude | 将 MCP 结果写入 pipeline JSON 文件 |
| Python 脚本 | 本地文件读写、数学计算、报告格式化 |
| Python 脚本 | AKShare 调用（纯本地接口，非 MCP）|

**禁止的实践**：
- ❌ Python 脚本中尝试 import MCP 或调用 MCP 工具
- ❌ Python 脚本输出"待补充"给本应 MCP 填充的字段
- ❌ Claude 直接运行脚本获取数据，而不调用 MCP

**正确的流程**：
1. Claude 调用 MCP 工具获取数据
2. Claude 将数据写入 _pipeline_stepN.json
3. Python 脚本读取 JSON 进行计算/格式化
4. generate_recommend.py 合并所有 JSON 生成报告
```

---

## Phase 6: evals.json P5 断言

```json
{
  "id": "C1-mcp-macro-data",
  "description": "P5：宏观数据必须从MCP获取，不能全为N/A",
  "prompt": "运行/fund:recommend，检查报告",
  "assertions": [
    {
      "type": "not_contains",
      "value": "周期判断：未知（置信度：N/A）",
      "description": "宏观周期不能全为未知"
    },
    {
      "type": "not_contains",
      "value": "总市值：N/A 元",
      "description": "总市值不能为N/A"
    }
  ]
},
{
  "id": "C2-mcp-fund-data",
  "description": "P5：基金数据必须从MCP获取，经理/费率不能全为待补充",
  "prompt": "运行/fund:recommend，检查报告中的基金数据层",
  "assertions": [
    {
      "type": "not_contains",
      "value": "经理：待补充",
      "description": "经理字段不能为待补充"
    },
    {
      "type": "not_contains",
      "value": "总费率：待补充",
      "description": "费率字段不能为待补充"
    },
    {
      "type": "not_contains",
      "value": "近1年：待补充",
      "description": "近1年收益不能为待补充"
    },
    {
      "type": "not_contains",
      "value": "近3年：待补充",
      "description": "近3年收益不能为待补充"
    },
    {
      "type": "not_contains",
      "value": "最大回撤：待补充",
      "description": "最大回撤不能为待补充"
    }
  ]
},
{
  "id": "C3-pipeline-step1-exists",
  "description": "P5：step1 文件必须由 Claude MCP 调用生成",
  "prompt": "运行/fund:recommend 后检查 fund-reports/ 目录",
  "assertions": [
    {
      "type": "file_exists",
      "value": "_pipeline_step1_macro.json",
      "description": "step1 宏观数据文件必须存在"
    },
    {
      "type": "file_exists",
      "value": "_pipeline_step3_funds.json",
      "description": "step3 基金验证文件必须存在"
    }
  ]
}
```

---

## Phase 7: 验证

1. 清空 pipeline（删除 fund-reports/_pipeline_step*.json）
2. 按 SKILL.md 新流程执行
3. 检查报告无"待补充"/"N/A"
4. 运行 evals.json 全部断言

## 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/pipeline.py` | 修改 | 扩展支持 step1/step3（语义化命名）|
| `SKILL.md` | 修改 | Step1+Step3 改为 Claude MCP 调用 |
| `scripts/get_macro.py` | 修改 | 降级为读取step1并格式化 |
| `scripts/validate_funds.py` | 修改 | 降级为读取step3并补充AKShare |
| `scripts/generate_recommend.py` | 修改 | 适配新的 step 文件命名 |
| `../_shared/rule-definitions.md` | 修改 | 新增架构约束章节 |
| `evals/evals.json` | 修改 | 追加 C1-C3 P5 断言 |
