# Task Plan — P4 成立不满3年基金标注修复

## 状态

| Phase | 描述 | 状态 |
|-------|------|------|
| Phase 1 | validate_funds.py：新增成立日期获取和年限计算 | ⏳ 待开始 |
| Phase 2 | generate_recommend.py：区分字符串标签和数值显示 | ⏳ 待开始 |
| Phase 3 | 追加 P4 断言到 evals.json | ⏳ 待开始 |
| Phase 4 | 运行完整流水线验证 | ⏳ 待开始 |

## Phase 1: validate_funds.py

**目标**：获取基金成立日期，计算年限，不满3年标注实际时长

**修改要点**：

1. **新增 `get_fund_establishment_date(fund_code)` 函数**：
   ```python
   def get_fund_establishment_date(fund_code):
       """返回 datetime.date 或 None"""
       try:
           import akshare as ak
           df = ak.fund_individual_basic_info_xq(symbol=fund_code)
           if df is not None and not df.empty:
               date_row = df[df["item"] == "成立日期"]
               if not date_row.empty:
                   date_str = str(date_row["value"].values[0])
                   from datetime import datetime
                   return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
       except Exception:
           pass
       return None
   ```

2. **新增 `calc_age_years_months(est_date, ref_date=None)` 函数**：
   ```python
   def calc_age_years_months(est_date, ref_date=None):
       """返回 (years, months)"""
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

3. **修改 `fetch_fund_basic()` 调用上述函数**：
   ```python
   # 获取成立日期
   est_date = get_fund_establishment_date(fund_code)
   if est_date:
       result["establishment_date"] = est_date.isoformat()
       years, months = calc_age_years_months(est_date)
       result["age_years"] = years
       result["age_months"] = months
       if years < 3:
           result["return_3y"] = f"成立以来（{years}年{months}月）"
           result["period_note"] = f"成立于{est_date}，仅{years}年{months}月"
   else:
       result["establishment_date"] = None
   ```

**输入**：`_pipeline_data.json["candidates"]`
**输出**：`_pipeline_data.json["validated_funds"]` 中新增字段

## Phase 2: generate_recommend.py

**目标**：根据 `return_3y` 字段类型决定显示格式

**修改要点**：

在报告生成循环中，修改近3年显示逻辑：
```python
# 近3年显示逻辑
return_3y = fund_detail.get("return_3y")
if return_3y is None:
    return_3y_str = "待补充"
elif isinstance(return_3y, str):
    # 不满3年的标签（如 "成立以来（2年5月）"）
    return_3y_str = return_3y
else:
    # 正常数值（如 51.71）
    return_3y_str = f"{return_3y:+.2f}%"
lines.append(f"  近 3 年：{return_3y_str}")
```

**输入**：`_pipeline_data.json["validated_funds"]`
**输出**：报告文件

## Phase 3: evals.json 追加

**新增断言**：

### B7-establishment-date-check
```json
{
  "id": "B7-establishment-date-check",
  "description": "P4：成立不满3年的基金必须标注实际成立时长",
  "prompt": "运行/fund:recommend，检查报告中020362基金的近3年标注",
  "assertions": [
    {
      "type": "not_contains",
      "value": "近3年：+51.71%",
      "description": "报告中不应出现近3年搭配成立以来收益数值"
    },
    {
      "type": "contains",
      "value": "成立以来",
      "description": "报告应包含成立以来标注"
    },
    {
      "type": "contains",
      "value": "2024-01-12",
      "description": "报告应显示成立日期"
    }
  ]
}
```

## Phase 4: 验证

1. 清空 pipeline
2. 依次运行 load_portfolio → screen_candidates → validate_funds → calc_var_impact
3. 检查 `validated_funds.verified` 中 020362 的 `return_3y` 字段
4. 运行 `generate_recommend.py --pipeline`，检查报告正文

## 依赖关系

```
Phase 1 ─→ Phase 2 ─→ Phase 3 ─→ Phase 4
```

Phase 1 和 Phase 2 无依赖关系，可并行修改，但 Phase 4 依赖两者都完成。
