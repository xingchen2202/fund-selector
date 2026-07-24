# 贡献指南

感谢你对 Fund Selector 的兴趣！

## 如何贡献

### 1. 报告问题

使用 GitHub Issues 报告 bug 或建议新功能。请包含：
- 问题描述
- 复现步骤
- 期望行为 vs 实际行为
- 你的环境（操作系统、Claude Code 版本）

### 2. 提交代码

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -m '@ feat: 功能描述'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

### 3. 提交前检查

运行测试确保没有回归：

```bash
python .claude/skills/fund-selector/tests/agents/test_agents_v2.py
python .claude/skills/fund-selector/tests/tools/test_tools.py
```

### 4. 代码规范

- 提交信息使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式
- SKILL.md 保持简洁（<500 行）
- 新增功能请同步更新 evals/evals.json

## 开发架构

```
.claude/skills/
├── fund-deep-research/    ← 单基金深度研究
├── fund-screener/         ← 基金筛选
├── fund-recommend/        ← 推荐系统
├── fund-selector/         ← 核心调度 + 测试
└── _shared/               ← 共享参考文档
```

## 测试

```bash
# 运行全部测试
python .claude/skills/fund-selector/tests/agents/test_agents_v2.py
python .claude/skills/fund-selector/tests/tools/test_tools.py

# 运行特定 skill 的 evals
python .claude/skills/fund-selector/tests/evals/run_evals.py
```

## 行为准则

请遵守我们的 [Code of Conduct](CODE_OF_CONDUCT.md)。

## 许可证

通过贡献你的代码，你同意你的贡献将在 MIT 许可证下发布。
