# 规则定义（共享）

> 本文件为 fund-recommend 和 fund-weekly-report 共享的规则基准。

---

## 一、基金筛选规则（fund-recommend 使用）

### 集中度限制
- **单板块占比上限**: 25%（超过则禁止新增该板块基金）
- **VaR月度上限**: 2000 元（用户风险承受能力）

### 基金筛选标准
| 维度 | 阈值 | 说明 |
|------|------|------|
| 最大回撤（股票型） | < 35% | 超出则排除 |
| 最大回撤（混合型） | < 25% | 超出则排除 |
| 最大回撤（债券型） | < 10% | 超出则排除 |
| 基金规模下限 | 2 亿 | 低于则排除（流动性不足）|

### 规模验证补充说明（P1修复）
- **Excel 数据不含规模字段**：`fund_screening_corrected_YYYYMMDD.xlsx` 不含规模列，不能依赖 Excel 做规模筛选
- **实时获取方式**：通过 AKShare `fund_individual_basic_info_xq(symbol=code)` 获取"最新规模"字段
- **单位换算**："44.81万" = 44.81万元 = 0.004481亿；"2.5亿" = 25000万元
- **验证时机**：Step 2 筛选完成后、Step 3 详细验证前
- **脚本实现**：`screen_candidates.py` 已内置 `validate_scale()` 函数
- **阈值常量**：`SCALE_THRESHOLD_WAN = 20000`（2亿 = 20000万元）
- **失败处理**：AKShare 接口异常时标注"规模数据不可用"，保留待人工核实（不误排除）
| 经理任职最短 | 1 年 | 低于则排除 |
| 费率警告线 | 管理费+托管费 > 1.5%/年 | 标注警告但不排除 |

### 新闻搜索规则
- 必须同时搜索**利多**和**利空**两个方向
- 利空新闻不能为空（防止确认偏误）
- 新闻时间范围：近 7 天
- 失败时标注"新闻搜索不可用"，继续执行

### 输出约束
- 不判断"现在是否是好的买入时机"（不择时）
- 不给出具体买入金额（只给上限建议）
- 必须包含"你需要自己判断的"章节
- 每个数据点标注来源和时间

---

## 二、持仓预警规则（fund-weekly-report 使用）

### 止盈提示
- **触发条件**: 任何基金盈利 > 30%
- **提示级别**: ⚠️ 警告
- **提示内容**: "XX基金盈利已达+X.XX%，建议评估是否部分止盈"
- **显示位置**: 报告顶部【规则提示】区

### 集中度警告
- **触发条件**: 任何板块占总市值 > 25%
- **提示级别**: ⚠️ 警告
- **提示内容**: "XX板块占比X.XX%，超过25%阈值，建议关注分散"
- **显示位置**: 报告顶部【规则提示】区

### 跌幅提示
- **触发条件**: 本周组合总跌幅 > 3%
- **提示级别**: ⚠️ 警告
- **提示内容**: "本周组合跌幅-X.XX%，超过3%阈值"
- **显示位置**: 报告顶部【规则提示】区

### 连续下跌关注
- **触发条件**: 任何基金连续4周下跌
- **提示级别**: ℹ️ 信息
- **提示内容**: "XX基金连续4周下跌，建议关注基本面变化"
- **显示位置**: 报告顶部【规则提示】区

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

### Pipeline 文件命名规范

| 文件 | 写入者 | 内容 |
|------|--------|------|
| _pipeline_step0_constraints.json | load_portfolio.py | 组合约束 |
| _pipeline_step1_macro.json | Claude (MCP) | 宏观指标数据 |
| _pipeline_step2_candidates.json | screen_candidates.py | 候选基金列表 |
| _pipeline_step3_funds.json | Claude (MCP) | 基金详细信息 |
| _pipeline_step3_akshare.json | validate_funds.py | AKShare 补充数据 |
| _pipeline_step4_var.json | calc_var_impact.py | VaR 影响计算 |
| _pipeline_step5_news.json | search_news.py | 新闻搜索结果 |

### 数据流向

```
MCP 工具 ──Claude调用──→ _pipeline_step1_macro.json ──→ Python读取──→ 报告
                         _pipeline_step3_funds.json  ──→ Python读取──→ 报告
AKShare  ──Python调用──→ _pipeline_step2_candidates.json
                         _pipeline_step3_akshare.json
数学计算 ──Python计算──→ _pipeline_step4_var.json
本地数据 ──Python获取──→ _pipeline_step5_news.json
```
