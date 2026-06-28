# skill-design-brief.md
# 由 Claude 网页端生成，Phase 1 时写入项目目录

## 基本信息

- **Skill 名称（kebab-case）：** fund-weekly-report
- **一句话描述：** 自动获取基金持仓净值、计算盈亏、搜索板块新闻，生成每周报告文件
- **复杂度：** high
- **安装位置：** C:\Users\22218\Desktop\fund-selector\.claude\skills\fund-weekly-report\
- **生成日期：** 2026-06-28

---

## Frontmatter 设计

```yaml
---
name: fund-weekly-report
description: >
  生成基金持仓周报。触发词：基金报告、周报、fund report、生成报告、
  查看持仓、持仓分析、基金净值。
  只要用户说"生成报告"或"查看持仓"，即触发本 Skill。
when_to_use: >
  用户想了解当前基金持仓盈亏状态时触发。
  包括：每周定期检查、手动触发分析、定投后更新确认。
  不触发场景：用户只是询问某只基金的信息（由普通对话处理）。
disable-model-invocation: false
user-invocable: true
context:
agent: general-purpose
allowed-tools: Read Write Bash Python
effort: high
---
```

---

## 触发机制设计

### 触发关键词（含中英文变体）
基金报告、周报、fund report、生成报告、查看持仓、持仓分析、
基金净值、持仓盈亏、我的基金、portfolio report

### capability_tags
fund-analysis, portfolio-tracking, weekly-report, akshare, tavily

### aliases
["基金周报", "持仓报告", "fund weekly", "portfolio check", "基金盈亏"]

### examples
- "帮我生成今天的基金报告"
- "查看我的持仓情况"
- "fund report"

### 触发场景
1. 用户说："生成基金报告" → 应触发
2. 用户说："我的基金今天怎么样" → 应触发
3. 用户说："/fund:report" → 手动触发

### 不触发的边界场景
1. "帮我搜索医疗基金" → 由普通对话处理，不触发本 Skill
2. "什么是净值" → 知识问答，不触发

---

## 功能边界

### 能做
- 读取 portfolio.json 获取持仓份额和成本
- 用 AKShare 获取所有基金当日最新净值
- 计算每只基金：当前市值、盈亏金额、盈亏百分比、距回本需涨幅度
- 用 Tavily 搜索各板块近7天新闻（银行、AI、半导体、黄金、纳指）
- 检查规则触发：止盈提示、集中度警告、周跌幅提示
- 生成报告文件保存至 fund-reports 文件夹

### 明确不做
- 不自动执行买卖操作
- 不预测未来净值走势
- 不接入支付宝账户（需手动维护 portfolio.json）
- 不处理港股通基金的实时汇率换算（使用AKShare默认数据）

---

## 输入/输出规范

### 输入
| 类型 | 必须/可选 | 说明 |
|------|---------|------|
| portfolio.json | 必须 | 持仓份额和成本净值 |
| AKShare 网络请求 | 必须 | 获取最新基金净值 |
| Tavily 搜索 | 可选 | 板块新闻，失败时跳过并标注 |

### $ARGUMENTS 设计
无参数。每次触发执行完整流程。
可选扩展：/fund:report --no-news 跳过新闻搜索

### 动态注入需求
```
!`python ${CLAUDE_SKILL_DIR}/scripts/fetch_nav.py`
!`python ${CLAUDE_SKILL_DIR}/scripts/check_rules.py`
```

### 输出
- 格式：.txt 文件（UTF-8编码）
- 路径：C:\Users\22218\Desktop\fund-selector\fund-reports\report_YYYYMMDD.txt
- 同时在对话内输出摘要（前5条最重要信息）

---

## 分层架构规划

```
C:\Users\22218\Desktop\fund-selector\
└── .claude\skills\fund-weekly-report\
    ├── SKILL.md                    ← 路由器 + 工作流指令（约150行）
    ├── references\
    │   ├── portfolio-schema.md     ← portfolio.json 格式说明
    │   ├── rules-definitions.md     ← 规则触发条件定义
    │   └── sector-map.md          ← 基金代码 → 板块映射表
    └── scripts\
        ├── fetch_nav.py           ← AKShare 获取净值
        ├── calculate_pnl.py       ← 盈亏计算
        ├── search_news.py         ← Tavily 新闻搜索
        ├── check_rules.py         ← 规则触发检查
        └── generate_report.py     ← 报告生成和保存
```

### SKILL.md 核心职责
路由器：读取 portfolio.json → 调用脚本 → 整合输出 → 保存报告

### references/ 说明
| 文件 | 内容 | 加载条件 |
|------|------|---------|
| portfolio-schema.md | JSON格式规范 | 每次启动时读取 |
| rule-definitions.md | 规则阈值定义 | 规则检查阶段 |
| sector-map.md | 代码→板块映射 | 新闻搜索阶段 |

### scripts/ 说明
| 脚本 | 功能 | 调用时机 |
|------|------|---------|
| fetch_nav.py | AKShare获取15只基金最新净值 | Step 1 |
| calculate_pnl.py | 计算市值/盈亏/回本距离 | Step 2 |
| search_news.py | Tavily搜索5个板块新闻 | Step 3 |
| check_rules.py | 检查止盈/集中度/跌幅规则 | Step 4 |
| generate_report.py | 整合输出并保存txt文件 | Step 5 |

### Hooks 需求（high 复杂度）
需要 Stop hook 验证报告文件确实生成：
```yaml
hooks:
  Stop:
    - matcher: ".*"
      hooks:
        - type: command
          command: |
            python ${CLAUDE_SKILL_DIR}/scripts/check_report_generated.py \
            2>/dev/null || echo "⚠️ 报告文件未生成，请检查脚本错误"
```

---

## Evals 设计

### 需要覆盖的测试场景
1. 标准路径：portfolio.json 存在 + 网络正常 → 生成完整报告
2. 网络失败：AKShare 超时 → 显示错误，不生成空报告
3. Tavily 失败：新闻搜索失败 → 跳过新闻部分，继续生成报告
4. 规则触发：某基金盈利>30% → 报告顶部显示止盈提示
5. portfolio.json 缺失 → 明确报错提示路径和格式要求

### 关键 Assertions
- 报告文件确实存在于 fund-reports 文件夹
- 报告包含所有15只基金的数据
- 规则触发时有明显标记（如 ⚠️ 符号）
- 不应出现：硬编码的"今天市场上涨"等预测性语言

---

## Registry 条目

```yaml
name: fund-weekly-report
purpose: 自动生成基金持仓周报，含净值、盈亏、新闻、规则提示
complexity: high
research_phase: General
capability_tags: [fund-analysis, portfolio-tracking, weekly-report]
aliases: ["基金周报", "持仓报告", "fund weekly", "基金盈亏"]
examples:
  - "生成基金报告"
  - "查看持仓情况"
  - "/fund:report"
depends_on: []
status: active
```
