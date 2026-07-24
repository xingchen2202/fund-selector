# 安全政策

## 支持的版本

| 版本 | 支持状态 |
|------|---------|
| latest | ✅ 支持 |
| < latest | ❌ 不支持 |

## 报告安全漏洞

**请不要通过 GitHub Issues 公开报告安全漏洞。**

请通过以下方式私下报告：
- 发送邮件给仓库维护者
- 或在 GitHub 上使用 [Private Vulnerability Reporting](https://github.com/xingchen2202/fund-selector/security/advisories/new)

请包含：
- 漏洞描述
- 复现步骤
- 潜在影响评估
- 建议修复方案（如有）

## 安全最佳实践

### 敏感信息

本仓库已配置 .gitignore 排除以下敏感文件：

- `.mcp.json` — MCP 服务器配置（含本地路径）
- `portfolio.json` — 个人持仓数据
- `.env` — 环境变量
- `*.pem`, `*.key` — 证书和密钥

**如果你是贡献者，请确保：**

1. 不要在代码中硬编码 API 密钥或个人路径
2. 提交前检查 `git status` 确认没有意外暂存敏感文件
3. 使用 `git add -p` 逐块审查暂存的更改

### MCP 安全

本仓库使用 MCP（Model Context Protocol）工具获取金融数据。请注意：

- MCP 工具调用会发送到第三方服务（AKShare、东方财富等）
- 不要在提示词中输入真实的账户凭证或个人信息
- 投资建议仅供参考，不构成专业投资意见

## 依赖安全

定期检查依赖更新：

```bash
pip install --upgrade -r requirements.txt
```

如发现依赖漏洞，请通过安全问题报告。
