# PLAN-v3: P5 MCP调用职责分离修复

> 修复推荐报告中所有数据字段显示"待补充"/"N/A"的问题

## 问题诊断

### 现象
- 2026-06-29 recommend 报告：经理/费率/收益/回撤全部"待补充"
- 宏观周期"未知（置信度：N/A）"，总市值"N/A 元"

### 根因
P3 修复引入 pipeline 架构，但错误地将 MCP 数据获取职责分配给 Python 脚本：
- `get_macro.py` 输出空模板（无法调用 MCP）
- `validate_funds.py` 只获取 AKShare 数据，MCP 字段留 None
- Python subprocess 无法访问 Claude 内置的 MCP 工具

### 证据
上上版报告（P3前）数据正确，因为 Claude 直接调用 MCP 后手动整合。
P3 后数据全空，因为 pipeline 脚本无法调用 MCP。

---

## 修复方案

### 核心原则
**MCP 调用必须由 Claude 执行，Python 脚本只负责本地计算和文件读写。**

### 执行流改造

```
改造前（断裂）：
  Step 1: Claude调MCP → 数据在对话中 → get_macro.py输出空模板 → 无step1文件
  Step 3: validate_funds.py → 只获取AKShare → MCP字段为None

改造后（修复）：
  Step 1: Claude调MCP → 写入 _pipeline_step1_macro.json ✅
  Step 3: Claude调MCP → 写入 _pipeline_step3_funds.json ✅
  Python脚本: 读取已填好的JSON → 补充AKShare → 计算 → 格式化 ✅
```

### 文件修改清单

#### 1. pipeline.py — 扩展 step 文件映射

```python
# 新增语义化命名
STEP_FILES = {
    "step0": REPORTS_DIR / "_pipeline_step0_constraints.json",
    "step1": REPORTS_DIR / "_pipeline_step1_macro.json",       # Claude写入
    "step2": REPORTS_DIR / "_pipeline_step2_candidates.json",
    "step3": REPORTS_DIR / "_pipeline_step3_funds.json",       # Claude写入
    "step3_akshare": REPORTS_DIR / "_pipeline_step3_akshare.json",  # Python写入
    "step4": REPORTS_DIR / "_pipeline_step4_var.json",
    "step5": REPORTS_DIR / "_pipeline_step5_news.json",
}
```

#### 2. SKILL.md — Step 1 改造

```markdown
## Step 1：宏观环境判断（Claude 执行）

1. 调用以下 MCP 工具（每个独立 try/catch）：
   - cn-financial: get_macro_pmi()
   - cn-financial: get_macro_money_supply()
   - cn-financial: get_valuation_metrics(symbol="000300", num_periods=60)
   - cn-financial: get_north_bound_flow()

2. 基于数据判断经济周期（参考 macro-cycle-guide.md）

3. 将结果写入 _pipeline_step1_macro.json：
   {
     "pmi": {...},
     "money_supply": {...},
     "valuation": {...},
     "north_bound": {...},
     "cycle_judgment": {"phase": "复苏", "confidence": "中", ...},
     "available_indicators": ["PMI", "M2"],
     "unavailable_indicators": ["北向资金"]
   }
```

#### 3. SKILL.md — Step 3 改造

```markdown
## Step 3：候选基金验证（Claude 执行）

1. 从 _pipeline_step2_candidates.json 读取 top10 候选

2. 对每只候选基金调用 cn-mutual-fund MCP：
   - get_fund_info(code) → 规模、经理、费率、成立日期
   - get_fund_nav_history(code, period="3y") → 收益、最大回撤
   - get_fund_portfolio(code) → 前十大持仓

3. 将结果写入 _pipeline_step3_funds.json：
   {
     "candidates": ["003593", ...],
     "verified": [
       {
         "code": "003593",
         "name": "...",
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

#### 4. get_macro.py — 降级为读取+格式化

```python
def main():
    """读取 _pipeline_step1_macro.json，格式化输出"""
    step1_file = REPORTS_DIR / "_pipeline_step1_macro.json"
    if not step1_file.exists():
        print("[WARN] step1 文件不存在", file=sys.stderr)
        return
    with open(step1_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 格式化输出到 stderr 供 Claude 确认
    cycle = data.get("cycle_judgment", {})
    print(f"[MACRO] 周期: {cycle.get('phase')} 置信度: {cycle.get('confidence')}")
```

#### 5. validate_funds.py — 降级为补充工具

```python
def main():
    """读取 _pipeline_step3_funds.json，补充 AKShare 数据"""
    step3_file = REPORTS_DIR / "_pipeline_step3_funds.json"
    if not step3_file.exists():
        print("[WARN] step3 文件不存在", file=sys.stderr)
        return
    with open(step3_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 可选：用 AKShare 验证/补充规模
    write_step("step3_akshare", data)
```

#### 6. generate_recommend.py — 适配新命名

修改 `read_all_steps()` 读取新的语义化文件名。

#### 7. rule-definitions.md — 新增架构约束

新增"三、架构约束"章节，明确：
- MCP 调用必须由 Claude 执行
- Python 脚本只负责本地计算
- 禁止脚本中尝试调用 MCP

#### 8. evals.json — 追加 P5 断言

- C1: 报告不能出现"周期判断：未知"或"总市值：N/A"
- C2: 报告不能出现"经理：待补充"等字段
- C3: step1/step3 文件必须存在

---

## 执行顺序

1. pipeline.py 扩展文件映射
2. SKILL.md 重构 Step 1 和 Step 3
3. get_macro.py 降级
4. validate_funds.py 降级
5. generate_recommend.py 适配
6. rule-definitions.md 新增约束
7. evals.json 追加断言
8. 运行完整流水线验证

## 验证标准

- 推荐报告中所有数据字段有实际数值
- 宏观周期有明确判断（非"未知"）
- 总市值显示正确数值
- evals.json 全部 C1-C3 断言通过
