# Portfolio Schema

## 文件路径
`C:\Users\22218\Desktop\fund-selector\portfolio.json`

## 格式规范

```json
{
  "funds": [
    {
      "code": "004597",          // 基金6位代码（字符串）
      "name": "鹏华中证银行指数LOF C",  // 基金全称
      "units": 6136.58,           // 持有份额（浮点数，精确到小数点后2-4位）
      "cost_nav": 1.4128,         // 成本净值（买入时的单位净值）
      "cost_value": 8045.67       // 成本金额（元）
    }
  ],
  "last_updated": "2026-06-28",  // 最后更新日期
  "data_source": "alipay-portfolio-snapshot-2026-06-24",  // 数据来源
  "note": "说明文字"
}
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 6位基金代码，保持前导零 |
| name | string | 是 | 基金完整名称 |
| units | float | 是 | 持有份额 |
| cost_nav | float | 是 | 买入时的单位净值 |
| cost_value | float | 是 | 成本金额（元） |

## 计算关系

- 当前市值 = units × 最新净值
- 盈亏金额 = 当前市值 - cost_value
- 盈亏百分比 = 盈亏金额 / cost_value × 100%

## 注意事项
- 代码必须是字符串类型（避免前导零被去掉）
- 同一基金不重复出现
- 货币基金（如余额宝）也可纳入，净值固定为1
