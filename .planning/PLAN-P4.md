# P4 修复计划 — 成立不满3年的基金标注"近3年"误导

## 状态：✅ 已完成 (iteration-2)

## 问题描述

### 现象
`validate_funds.py` 生成的 `validated_funds` 数据中，`return_3y` 字段为 `None`（未填充），但 Claude 在生成报告时使用 MCP `get_fund_info()` 返回的"3年收益"字段。对于成立不满3年的基金，MCP 返回的"3年收益"实际是"成立以来收益"，但标签仍为"近3年"，严重误导。

### 具体案例
- 基金：中海沪港深价值优选混合C（020362）
- 成立日期：2024-01-12（约2年5个月，截至2026-06-29）
- MCP `get_fund_info` 返回：`业绩表现` 中 `"周期": "成立以来"`, `"本产品区间收益": 51.71`
- 报告标注：近3年：+51.71%（实为成立以来收益，约2.5年）

### 根因
1. `validate_funds.py` 不获取基金成立时间
2. `generate_recommend.py` 不校验成立年限，直接使用 MCP 返回的"3年收益"字段
3. MCP `get_fund_info()` 对成立不满3年的基金，其"3年收益"字段返回的是"成立以来收益"，但字段名仍为"3年"

### 修复方案

在 `validate_funds.py` 中：
1. 从 AKShare `fund_individual_basic_info_xq` 获取"成立日期"字段
2. 计算成立至今的年数
3. 不满3年的基金，在 `return_3y` 字段中写入标签 `"成立以来（X年X月）"` 而非数值
4. 在 `period_note` 字段中标注实际成立时长

在 `generate_recommend.py` 中：
5. 如果 `return_3y` 是字符串标签（非数值），直接显示该标签
6. 如果 `return_3y` 是数值，按原格式显示

## 修改清单

### 1. `validate_funds.py` — 获取成立日期并标注

**新增函数**：
```python
def get_fund_establishment_date(fund_code):
    """通过 AKShare 获取基金成立日期，返回 date 对象或 None"""
    try:
        import akshare as ak
        df = ak.fund_individual_basic_info_xq(symbol=fund_code)
        if df is not None and not df.empty:
            date_row = df[df["item"] == "成立日期"]
            if not date_row.empty:
                date_str = str(date_row["value"].values[0])
                from datetime import datetime
                return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        pass
    return None

def calc_age_years_months(est_date, ref_date=None):
    """计算成立日期到参考日期的年数和月数"""
    if ref_date is None:
        from datetime import date
        ref_date = date.today()
    years = ref_date.year - est_date.year
    months = ref_date.month - est_date.month
    if ref_date.day < est_date.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    return years, months
```

**修改 `fetch_fund_basic()`**：
- 调用 `get_fund_establishment_date(fund_code)` 获取成立日期
- 如果成立不满3年：
  - `result["return_3y"]` = `f"成立以来（{Y}年{M}月）"` （字符串标签）
  - `result["period_note"]` = f"成立于{est_date}，仅{Y}年{M}月"
- 如果成立满3年：
  - `result["return_3y"]` = `None` （由 Claude MCP 填充实际3年收益）
  - `result["period_note"]` = None

**输出格式变更**：
```python
# 新增字段
"establishment_date": "2024-01-12",  # 成立日期（ISO格式）
"age_years": 2,                      # 成立年数
"age_months": 5,                     # 成立月数（不满年的部分）
"return_3y": "成立以来（2年5月）",    # 不满3年时为字符串标签
"period_note": "成立于2024-01-12，仅2年5月"  # 说明文字
```

### 2. `generate_recommend.py` — 智能显示标签

**修改报告生成逻辑**：
```python
# 近3年显示逻辑
return_3y = fund_detail.get("return_3y")
if return_3y is None:
    return_3y_str = "待补充"
elif isinstance(return_3y, str):
    # 不满3年的标签（如 "成立以来（2年5月）"）
    return_3y_str = return_3y
else:
    # 正常数值
    return_3y_str = f"{return_3y:+.2f}%"
lines.append(f"  近 3 年：{return_3y_str}")
```

## 实施步骤

| 步骤 | 文件 | 操作 |
|------|------|------|
| 1 | `validate_funds.py` | 新增 `get_fund_establishment_date()` 函数 |
| 2 | `validate_funds.py` | 新增 `calc_age_years_months()` 函数 |
| 3 | `validate_funds.py` | 修改 `fetch_fund_basic()` 获取成立日期并判断 |
| 4 | `generate_recommend.py` | 修改报告生成逻辑，区分字符串标签和数值 |
| 5 | `evals.json` | 追加 P4 断言 |
| 6 | `PLAN-P4.md` | 本文档 |

## 断言设计（evals.json 追加）

### B7-establishment-date-check
- **描述**：P4：成立不满3年的基金必须标注实际成立时长
- **prompt**：运行/fund:recommend，检查报告中020362基金的"近3年"标注
- **assertions**：
  - `not_contains`: `近3年：+51.71%` — 报告中不应出现"近3年"搭配成立以来收益数值
  - `contains`: `成立以来` — 报告应包含"成立以来"标注
  - `contains`: `2024-01-12` — 报告应显示成立日期

### B8-return-3y-label-type
- **描述**：P4：return_3y字段对不满3年基金应为字符串标签
- **prompt**：检查 pipeline 中 validated_funds 的 020362 基金 return_3y 字段
- **assertions**：
  - `source_contains`: `成立以来` — return_3y 应包含"成立以来"

## 风险与注意事项

1. **AKShare API 变化**：`fund_individual_basic_info_xq` 返回的字段名可能随 AKShare 版本变化
   - 缓解：使用 `df[df["item"] == "成立日期"]` 模糊匹配

2. **日期计算精度**：使用 `date.today()` 作为参考日期
   - 注意：如果报告生成日期不同，月数可能有1个月偏差

3. **向后兼容**：满3年基金的 `return_3y` 仍为 `None`，由 Claude MCP 填充
   - 不影响现有逻辑

## 验证方案

1. 运行完整流水线（P1+P2+P3）
2. 检查 `fund-reports/_pipeline_data.json` 中 `validated_funds.verified` 的 020362 条目
3. 确认 `return_3y` 字段为 `"成立以来（2年5月）"` 而非数值
4. 运行 `generate_recommend.py --pipeline`，检查报告中 020362 的显示
