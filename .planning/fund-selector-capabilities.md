# Fund Selector — 能力清单（对比基准）
> 2026-07-06 更新，含 ai-berkshire 移植后的完整能力

## 一、Skill 层（6 个入口）

| Skill | 触发词 | 核心能力 |
|-------|--------|---------|
| `fund-recommend` | 推荐基金、买什么基金 | 全市场筛选 + 双 Agent + 穿透检查 |
| `fund-screener` | 筛选基金、帮我选 | 多维度评分（夏普/回撤/规模/经理/费率）|
| `fund-weekly-report` | 持仓报告、周报 | 持仓盈亏 + 新闻 + 规则触发 |
| `manager-profiler` | 经理画像、XX经理怎么样 | 经理深度分析 |
| `asset-allocation` | 资产配置、股债比例 | 宏观研判 + 配置建议 |
| `execution-planner` | 建仓计划、定投、网格 | DCA/金字塔/网格执行方案 |

## 二、Agent 层

| Agent | 文件 | 评分维度 |
|-------|------|---------|
| 进攻 Agent | `agents/offense_agent.py` | 收益/动量/赛道景气 |
| 防守 Agent | `agents/defense_agent.py` | 回撤/波动/经理稳定性/规模费率 |
| 综合器 | `agents/agents/synthesizer.py` | 混合得分 + 冲突检测（排名差≥3）|

## 三、工具层（脚本）

| 脚本 | 功能 |
|------|------|
| `scripts/load_portfolio.py` | 读取组合约束 |
| `scripts/screen_candidates.py` | Excel 候选池筛选 |
| `scripts/validate_funds.py` | 基金验证 + 回撤过滤 |
| `scripts/calc_var_impact.py` | VaR 计算（P8修复）|
| `scripts/search_news.py` | AKShare 新闻搜索 |
| `scripts/generate_recommend.py` | 报告生成（含 6 个移植函数）|
| `scripts/financial_rigor.py` | Decimal 精度工具（移植）|
| `scripts/rejection_checklist.py` | 快否决清单（移植）|

## 四、移植自 ai-berkshire 的能力

| 能力 | 对应函数/模块 | 测试覆盖 |
|------|-------------|---------|
| 信息丰富度分级(A/B/C) | `generate_report.grade_data_richness` | 3 tests |
| 定投三情景 | `generate_report.build_dca_scenarios` | 2 tests |
| 芒格反向测试 | `generate_report.build_reverse_test` | 2 tests |
| 镜子测试(5句话) | `generate_report.build_mirror_test` | 2 tests |
| 六关评分(★1-5) | `generate_report.score_six_gates` | 3 tests |
| Decimal 精度工具 | `financial_rigor.py` 7 子命令 | 2 tests |
| 快否决6条红线 | `rejection_checklist.py` | 2 tests |

## 五、数据源（MCP）

| 服务器 | 工具数 | 用途 |
|--------|--------|------|
| cn-financial | 42 | A股行情/财报/宏观/行业 |
| cn-mutual-fund | ~20 | 基金信息/净值/经理/持仓 |

## 六、运行模式

- **单 Agent 模式**：串行 pipeline，MCP ~30 次
- **双 Agent 模式**：进攻+防守并行 → 综合器，可暴露单一视角盲区

## 七、已知局限

- ❌ 无 WebSocket/实时推送
- ❌ 无 FOF 组合回测引擎
- ❌ 无季报滞后自动校准
- ❌ 新闻搜索依赖单一接口（无多源交叉）
- ❌ 无用户风险偏好问卷自适应
- ❌ 无止损后自动复盘机制
