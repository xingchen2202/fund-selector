# Task Plan — 创建 /theme-perilla Skill

> 目标：基于紫苏叶理论（Serenity股神 BV1fT7z6QE2S）创建独立的主题瓶颈分析 skill

---

## Goal

创建 `/theme-perilla` skill，输入热门概念（AI算力/新能源/半导体等），通过紫苏叶五因子模型评分产业链瓶颈节点，推荐相关基金和股票。

---

## Phases

### Phase 1: 规划与调研 ✅
- [x] 读取紫苏叶理论来源（Bilibili BV1fT7z6QE2S）
- [x] 确认五因子模型标准
- [x] 设计 skill 架构
- [ ] 创建 task_plan.md / findings.md / progress.md

### Phase 2: 创建 SKILL.md ✅
- [x] 编写 frontmatter（name, description, when_to_use, allowed-tools）
- [x] 定义触发词
- [x] 编写完整工作流（Step 1-6）
- [x] 定义输出格式

### Phase 3: 创建核心脚本 ✅
- [x] `scripts/perilla_scorer.py` — 五因子评分核心
- [x] `scripts/industry_chain.py` — 产业链图谱构建
- [x] (bottleneck_mapper 逻辑合并到 industry_chain)

### Phase 4: 创建参考资料 ✅
- [x] `references/perilla-framework.md` — 理论说明完整版
- [x] `references/industry-chains/ai-computing.md` — AI算力产业链
- [x] `references/industry-chains/new-energy.md` — 新能源产业链
- [x] `references/industry-chains/semiconductor.md` — 半导体产业链

### Phase 5: 创建测试与报告模板 ✅
- [x] `evals/evals.json` — 6 条测试断言
- [x] `reports/report-template.md` — 报告模板

### Phase 6: 测试验证 ✅
- [x] SKILL.md frontmatter 检查（7/7）
- [x] perilla_scorer.py 运行
- [x] industry_chain.py 运行
- [x] evals.json 6 条断言定义

---

## Key Decisions

| 决策 | 选择 | 理由 |
|------|------|------|
| skill 类型 | 独立 skill | 不依附现有 19 个 skill，独立触发 |
| 五因子来源 | Serenity股神 BV1fT7z6QE2S | 视频原版的瓶颈节点投资法 |
| 评分阈值 | ≥12/15 = 紫苏叶级 | 符合视频原版标准 |
| 产业链数据 | references/industry-chains/ | 每个主题一个 md，可扩展 |
| MCP 依赖 | cn-financial + cn-mutual-fund | 获取真实财务/持仓数据 |

---

## Output Structure

```
.claude/skills/theme-perilla/
├── SKILL.md
├── scripts/
│   ├── perilla_scorer.py
│   ├── industry_chain.py
│   └── bottleneck_mapper.py
├── references/
│   ├── perilla-framework.md
│   └── industry-chains/
│       ├── ai-computing.md
│       ├── new-energy.md
│       └── semiconductor.md
├── evals/
│   └── evals.json
└── reports/
    └── report-template.md
```
