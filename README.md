# Fund Selector — 基金投研助手

基于 Claude Code + MCP 的 A 股公募基金持仓研究与交易规划助手。

## 项目简介

本项目通过 Claude Code 的 MCP 协议和 Skill 机制，实现：

- **基金持仓跟踪**：自动获取最新净值、计算盈亏、生成周报
- **智能筛选**：基于 AKShare 数据的基金筛选和经理画像
- **资产配置**：宏观研判 + 股债比例建议 + 执行计划
- **产业链投资**：紫苏叶理论（供应链隐形冠军筛选）

## 项目结构

```
├── .claude/skills/           ← 自定义 Skills
│   ├── fund-weekly-report/   ← 基金周报生成
│   ├── fund-screener/        ← 基金筛选
│   ├── manager-profiler/     ← 经理画像
│   ├── asset-allocation/     ← 资产配置
│   └── execution-planner/    ← 交易执行
├── cn-financial-mcp/         ← A 股个股/宏观数据（akshare）
├── cn-mutual-fund/           ← 公募基金数据（akshare）
├── registry/                 ← Skill 注册表
├── portfolio.json            ← 持仓数据（私有，不上传）
├── weekly_report.py         ← 独立运行脚本
└── fund-reports/             ← 生成的报告（不上传）
```

## 快速开始

### 1. 安装依赖

```bash
pip install akshare pandas tavily-python
```

### 2. 配置持仓

编辑 `portfolio.json`，填入你的基金代码、份额和成本净值：

```json
{
  "funds": [
    {
      "code": "004597",
      "name": "鹏华中证银行指数LOF C",
      "units": 6136.58,
      "cost_nav": 1.4128,
      "cost_value": 8045.67
    }
  ]
}
```

### 3. 生成周报

```bash
python weekly_report.py
```

或在 Claude Code 中输入 `/fund:report` 触发自动化 Skill。

## 核心功能

| 功能 | 触发方式 | 说明 |
|------|---------|------|
| 基金周报 | `/fund:report` 或 "生成报告" | 净值 + 盈亏 + 新闻 + 规则提示 |
| 基金筛选 | "筛选基金" / "买什么" | 4 步流程：宏观→配置→筛选→执行 |
| 经理画像 | "XX经理怎么样" | 从业年限 + 管理产品 + 历史业绩 |
| 资产配置 | "当前市场环境" | PE/PB 估值 + 景气度 + 建议比例 |

## 投资铁律

1. **底层穿透防重叠**：同一行业仓位重合度不超过 15%
2. **预算硬平衡**：定投金额不超过月净储蓄额
3. **配置比例数学闭环**：筛选金额严格匹配配置比例
4. **常识校验防幻觉**：PE/PB 极端值标注并交叉验证
5. **财务健康预检**：先确认应急金、高息负债、保险
6. **费率穿透**：每次推荐必须披露总费率结构
7. **再平衡机制**：季度回顾，偏离 10% 触发再平衡

## 数据源

- **基金净值**：天天基金网（via AKShare）
- **A 股行情**：AKShare
- **宏观经济**：AKShare + FRED
- **新闻搜索**：Tavily（可选）

## 免责声明

本项目仅供学习研究使用，所有数据和分析仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。

## License

MIT
