# P2 修复进度日志

## Session 1 — 2026-06-29（实施）

### 修改内容

#### 1. `fund-weekly-report/scripts/search_news.py`
- SECTOR_QUERIES 搜索词全部中文化（加"中文"后缀）
- Tavily 搜索加入 `days=7` 参数
- `max_results` 从 3 增加到 5
- 新增中文标题优先排序逻辑
- 输出新增 `published_date` 和 `time_warning` 字段
- 新增 `is_older_than_7_days()` 函数

#### 2. `fund-recommend/scripts/search_news.py`
- 模板文件，同样更新搜索词为中文
- 添加 P2 修复要点注释

#### 3. `sector-map.md`
- 搜索词表移除英文列
- 新闻搜索策略更新（days=7、中文、超期标注）

#### 4. `evals/evals.json`
- 追加 B4（搜索词中文化）、B5（days=7）、B6（时间检查）

### 测试结果

#### 搜索词验证
```
全部8个搜索词均为中文：
✅ 中国银行板块 最新政策 利率 2026年6月 中文
✅ 中国金融科技 数字金融 最新政策 2026年6月 中文
✅ 中国AI算力 人工智能 最新消息 2026年6月 中文
✅ 中国半导体芯片 集成电路 最新消息 2026年6月 中文
✅ 美国纳斯达克 美股科技 AI 最新消息 2026年6月 中文
✅ 黄金市场 金价走势 分析 2026年6月 中文
✅ 港股科技 恒生科技指数 最新消息 2026年6月 中文
✅ 中国科创板 科创50 最新消息 2026年6月 中文
```

#### Tavily 返回语言
- Tavily 是全球搜索引擎，中文搜索词也可能返回英文结果
- 已增加中文标题优先排序逻辑
- 实际效果取决于 Tavily 内容库

### 待用户确认
- [ ] 是否需要更强的中文语言限制（如 `lang="zh"` 如果 Tavily 支持）
- [ ] 是否需要更新 SKILL.md 中 Step 5 的新闻搜索说明

---

# P3 修复进度 — 2026-06-29

## 状态：已完成

### 修改内容

#### 1. 新建 `pipeline.py` — 统一数据总线
- `PIPELINE_FILE` 指向 `fund-reports/_pipeline_data.json`
- `read_pipeline()` / `write_pipeline(key, data)` / `get_pipeline(key)` 三个函数
- 所有脚本共享同一份数据

#### 2. `load_portfolio.py` — 末尾追加 pipeline 写入
- 计算结果写入 `pipeline["constraints"]`

#### 3. `screen_candidates.py` — 末尾追加 pipeline 写入
- 筛选结果写入 `pipeline["candidates"]`

#### 4. `validate_funds.py` — 重写为实际执行脚本
- 从 pipeline 读取 candidates
- 调用 AKShare `fund_individual_basic_info_xq` 获取规模
- 写入 `pipeline["validated_funds"]`
- 注意：净值历史由 Claude 通过 cn-mutual-fund MCP 获取（AKShare API 变化导致不可靠）

#### 5. `calc_var_impact.py` — 修改为读取 pipeline
- 从 pipeline 读取 constraints.existing_var 和 candidates
- 计算每只基金的边际 VaR
- 写入 `pipeline["var_impacts"]`

#### 6. `search_news.py` — 重写为实际执行脚本
- 从 pipeline 读取 candidates
- 调用 Tavily REST API 搜索新闻（需要 TAVILY_API_KEY）
- 写入 `pipeline["news"]`

#### 7. `generate_recommend.py` — 新增 --pipeline 模式
- `--pipeline` 参数从 `_pipeline_data.json` 读取完整数据
- 支持 `validated_funds` 的 `{verified: [{...}, ...]}` 结构
- 保留向后兼容（指定 JSON 文件路径）
- 添加 UTF-8 stdout wrapper（Windows GBK 兼容性）

#### 8. `SKILL.md` — Step 7 更新为 4 步流水线
- 7.1 validate_funds.py → pipeline["validated_funds"]
- 7.2 calc_var_impact.py → pipeline["var_impacts"]
- 7.3 search_news.py → pipeline["news"]
- 7.4 generate_recommend.py --pipeline

#### 9. `evals.json` — 追加 B3-data-flow 断言
- 5 个断言：无"新闻：无"、无"VaR影响：无"、包含"利多"、包含"利空"、包含"VaR"

### 测试结果
```
Pipeline keys: ['constraints', 'candidates', 'validated_funds', 'var_impacts']
Candidates: 9
Validated: 9
VaR impacts: 9

B3-data-flow assertions:
PASS: 报告中不应出现 新闻：无
PASS: 报告中不应出现 VaR影响：无
PASS: 报告应包含利多
PASS: 报告应包含利空
PASS: 报告应包含VaR
```

### 已知限制
- `search_news.py` 需要 TAVILY_API_KEY 环境变量，否则新闻显示"无"
- `validate_funds.py` 只获取规模数据，净值/经理等由 Claude MCP 获取
- AKShare API 变化导致无法直接获取单只基金净值历史

---

# P4 修复计划 — 2026-06-29

## 状态：已规划，待用户确认执行

### 问题
- 成立不满3年的基金在报告中显示"近3年：+51.71%"，但该数字实为成立以来收益
- MCP 返回的业绩数据中"成立以来"收益被误标为"近3年"
- 020362（2024-01-12成立）被标注"近3年：+51.71%"，实际仅2年5个月

### 方案
- `validate_funds.py` 新增获取成立日期，计算成立年限
- 不满3年的基金，`return_3y` 字段改为字符串标签 `"成立以来（2年5月）"`
- `generate_recommend.py` 区分字符串标签和数值显示

### 产物
- `.planning/PLAN-P4.md` — 完整修复计划
- `.planning/findings.md` — 追加 P4 根因分析
- `.planning/progress.md` — 本文档

---

# P3 修复计划 — 2026-06-29

## 状态：已规划，待用户确认执行

### 问题
- `generate_recommend.py` 无法读取 VaR 和新闻数据
- 各脚本独立运行，数据停留在 Claude 对话上下文中
- 最终报告显示"无"或临时估算值

### 方案
- 建立 `_pipeline_data.json` 统一数据总线
- 4 个脚本分别写入自己负责的字段
- `generate_recommend.py --pipeline` 读取完整数据

### 产物
- `.planning/PLAN-P3.md` — 完整修复计划
- `.planning/findings.md` — 追加 P3 根因分析
- `.planning/progress.md` — 本文档
