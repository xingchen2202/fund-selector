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
├── .claude/
│   ├── skills/                    ← 自定义 Skills
│   │   ├── _shared/               ← 共享知识库（规则、板块映射等）
│   │   ├── fund-recommend/        ← 基金筛选推荐
│   │   ├── fund-weekly-report/    ← 基金持仓周报
│   │   ├── fund-screener/         ← 基金筛选器
│   │   ├── manager-profiler/      ← 基金经理画像
│   │   ├── asset-allocation/      ← 大类资产配置
│   │   └── execution-planner/     ← 交易执行计划
│   └── settings.local.json        ← 本地配置（不上传）
├── cn-financial-mcp/              ← A 股个股/宏观数据（akshare）
├── cn-mutual-fund/                ← 公募基金数据（akshare）
├── FinanceAgent/                  ← 美股组合管理
├── registry/                      ← Skill 注册表
├── portfolio.json                 ← 持仓数据（私有，不上传）
├── fund-reports/                  ← 生成的报告（不上传）
└── README.md                      ← 本文件
```

## Skills 说明

### 共享知识库（`_shared/`）

多个 Skill 共享的知识文件，避免重复维护：

| 文件 | 用途 | 使用方 |
|------|------|--------|
| `rule-definitions.md` | 筛选规则 + 预警阈值 | fund-recommend, fund-weekly-report |
| `sector-map.md` | 基金代码→板块映射 + 新闻关键词 | fund-recommend, fund-weekly-report |
| `portfolio-schema.md` | 持仓 JSON 格式规范 | fund-weekly-report |
| `macro-cycle-guide.md` | 经济周期判断逻辑 | fund-recommend |
| `perilla-framework.md` | 持仓穿透分析标准 | fund-recommend |

### 主要 Skills

| Skill | 触发方式 | 功能 |
|-------|---------|------|
| `fund-recommend` | "推荐基金" / "买什么" | 4 步流程：宏观→配置→筛选→执行计划 |
| `fund-weekly-report` | "生成报告" / "查看持仓" | 最新净值 + 盈亏 + 板块新闻 + 规则提示 |
| `fund-screener` | "筛选基金" | 多维度基金筛选 |
| `manager-profiler` | "XX经理怎么样" | 从业年限 + 管理产品 + 历史业绩 |
| `asset-allocation` | "当前市场环境" | PE/PB 估值 + 景气度 + 建议比例 |
| `execution-planner` | "怎么买" / "定投方案" | 分批建仓 + 网格策略 |

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
  ],
  "last_updated": "2026-06-28",
  "data_source": "alipay-portfolio-snapshot"
}
```

### 3. 使用方式

在 Claude Code 中直接对话：

- **生成周报**：`/fund-weekly-report` 或说"生成报告"
- **筛选基金**：`/fund-recommend` 或说"推荐基金"
- **查看经理**：说"张坤怎么样"

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
