# Fund Selector v2.0 — 后续优化建议（四轮尽调汇总）

> **日期**：2026-07-21 · **角色**：A 股基金经理 / 个人投资者 / 量化基金 PM
> **基础**：四轮深度尽调（136 测试全绿）+ 11 项 P0/P1/P2 修复后的现状评估

---

## 〇、现状定位（重要）

经过四轮测试与修复，Fund Selector 当前是：

> **"可信赖的投研研究辅助工具"** — 约束已程序化、工具层生产级健壮、工作流完整。

但距离**"专业级投研平台"**仍有差距。以下建议按**投资价值/工时比**排序。

---

## 一、P1 — 高价值优化（建议 1-2 周）

### 1.1 工作流新增"压力测试"具体实现

**现状**：FUND_ANALYSIS_WORKFLOW 已增加 Step5 压力测试章节，但缺少具体计算工具。

**建议**：新增 `tools/stress_tester.py`：
```python
def estimate_extreme_drawdown(fund_drawdowns: list, correlation: float = 0.7) -> dict:
    """基于历史回撤 + 相关性，估计组合极端行情回撤。"""
    # 加权平均回撤 × 极端系数（考虑相关性）
    avg_dd = sum(fund_drawdowns) / len(fund_drawdowns)
    extreme_dd = avg_dd * 1.2  # 极端系数
    # 相关性调整：高相关性 → 极端回撤更大
    correlation_adjustment = 1 + (correlation - 0.5) * 0.3
    adjusted_dd = extreme_dd * correlation_adjustment
    return {
        "average_drawdown": avg_dd,
        "extreme_drawdown": extreme_dd,
        "correlation_adjusted": adjusted_dd,
        "can_absorb": adjusted_dd > -0.25,  # 默认阈值 -25%
        "recommendation": "可承受" if adjusted_dd > -0.25 else "需降低仓位"
    }
```

**投资价值**：⭐⭐⭐⭐ — 这是专业投研与散户分析的核心差异。

### 1.2 持仓相关性计算工具化

**现状**：constraint_validator 已有相关性警告，但未提供具体相关系数。

**建议**：新增 `tools/correlation_checker.py`：
```python
def check_holdings_overlap(fund1_holdings: list, fund2_holdings: list) -> dict:
    """计算两只基金重仓股重叠度。"""
    common = set(fund1_holdings) & set(fund2_holdings)
    return {
        "common_count": len(common),
        "common_stocks": list(common),
        "overlap_rate": len(common) / min(len(fund1_holdings), len(fund2_holdings)),
        "warning": len(common) >= 3
    }
```

**投资价值**：⭐⭐⭐ — 量化分散度，避免伪分散。

### 1.3 CI 覆盖新增测试文件

**现状**：test_mcp_integration.py / test_boundary.py / test_e2e_integration.py 未加入 CI。

**建议**：更新 `.github/workflows/test.yml`，增加：
```yaml
      - name: Run new component tests
        run: |
          python .claude/skills/fund-selector/tools/test_mcp_integration.py
          python .claude/skills/fund-selector/tools/test_boundary.py
          python .claude/skills/fund-selector/tools/test_e2e_integration.py
```

**技术价值**：⭐⭐⭐ — 防止回归。

---

## 二、P2 — 质量保证（建议 2 周）

### 2.1 LLM 输出行为测试

**现状**：测试覆盖工具层，但未测试 skill 实际执行时 LLM 的输出行为。这是**最大的测试缺口**。

**建议**：使用 skill-creator 框架，设计 3-5 个真实 prompt：

| 预期行为 | 测试 prompt |
|---------|------------|
| 推荐后必须调用约束校验 | "推荐 3 只稳健型基金，月投 3000" |
| 约束不通过必须修正 | "推荐 5 只基金，全部重仓制造业" |
| 必须附带免责声明 | "分析中欧新趋势混合" |
| 4 大师视角必须差异化 | "用投研团队分析国泰有色矿业" |

**断言**：输出包含必要段落、约束校验被调用、免责声明存在。

**投资价值**：⭐⭐⭐⭐⭐ — 这是"工具正确"到"系统正确"的关键一跃。

### 2.2 数据时间戳强制

**现状**：工具返回数据无时间戳，无法判断数据时效。

**建议**：所有 MCP 输出强制附带 `data_timestamp` 字段：
```json
{
  "nav": 1.0553,
  "nav_date": "2026-07-21",
  "data_timestamp": "2026-07-21T15:30:00",
  "source": "天天基金"
}
```

并在 constraint_validator 中增加**数据时效校验**：
```python
def _check_data_freshness(rec: dict, warnings: list):
    """数据超过 5 个交易日 → 警告。"""
    for f in rec.get("funds", []):
        data_date = f.get("data_date")
        if data_date and is_stale(data_date, max_days=5):
            warnings.append(f"[数据时效] {f['name']} 数据日期 {data_date} 可能陈旧")
```

**投资价值**：⭐⭐⭐ — 避免基于过期数据做决策。

### 2.3 修复 test_resilience.py 的 pandas 依赖

**现状**：2 个 fallback 测试因系统 Python 无 pandas 失败。

**建议**：将 fallback 测试改为不依赖 pandas（直接 import synthesize 模块而非整个 MCP 包）。

**技术价值**：⭐⭐ — 测试独立性。

---

## 三、P3 — 机构级能力（长期愿景）

### 3.1 从"事后校验"到"生成中约束"

**现状**：constraint_validator 是推荐生成后的校验。

**建议（长期架构演进）**：
- 生成候选池时即过滤违规项（规模<2亿、回撤>35%）
- 资金分配时即检查预算平衡
- 输出前最终校验（双保险）

**投资价值**：⭐⭐⭐ — 效率 + 安全性。

### 3.2 真多 Agent 并行

**现状**：4 大师是"顺序读提示"（文档驱动），非独立推理。

**建议**：使用 Agent 工具启动 4 个独立子 Agent：
```
await agent("value_agent", ...)   # 独立上下文
await agent("growth_agent", ...)  # 独立上下文
# 各自独立 MCP 搜索 + 独立判断 → 汇总
```

**投资价值**：⭐⭐⭐ — 真正的对抗式分析。

### 3.3 组合风险模型（VaR/CVaR）

**现状**：旧架构 `calc_var_impact.py` 有简化 VaR，新架构未集成。

**建议**：集成到 constraint_validator 或独立模块：
```python
def calculate_portfolio_var(holdings: list, confidence: float = 0.95) -> dict:
    """基于持仓股票历史波动率，计算组合 VaR。"""
    # 参数法 VaR：组合波动率 × z_score × 持仓市值
    ...
```

**机构价值**：⭐⭐⭐⭐ — 量化风控核心能力。

### 3.4 多数据源适配（Wind/Choice）

**现状**：仅依赖 AKShare（免费源，质量不稳定）。

**建议**：抽象数据层：
```
data_source:
  primary: akshare
  fallback: wind  # 或 choice, tushare
```

**机构价值**：⭐⭐⭐⭐ — 机构用户准入门槛。

---

## 四、优化优先级矩阵

| 优先级 | 建议 | 投资价值 | 工时 | ROI |
|--------|------|---------|------|-----|
| **P1** | 压力测试工具化 | ⭐⭐⭐⭐ | 1天 | 极高 |
| **P1** | 持仓相关性工具 | ⭐⭐⭐ | 0.5天 | 高 |
| **P1** | CI 覆盖新测试 | ⭐⭐⭐ | 0.5天 | 高 |
| **P2** | LLM 行为测试 | ⭐⭐⭐⭐⭐ | 2天 | 极高 |
| **P2** | 数据时间戳 | ⭐⭐⭐ | 1天 | 中 |
| **P2** | 修复 pandas 依赖 | ⭐⭐ | 0.5天 | 低 |
| **P3** | 生成中约束 | ⭐⭐⭐ | 3天 | 中 |
| **P3** | 真多 Agent | ⭐⭐⭐ | 3天 | 中 |
| **P3** | 组合风险模型 | ⭐⭐⭐⭐ | 5天 | 机构 |
| **P3** | 多数据源 | ⭐⭐⭐⭐ | 5天 | 机构 |

---

## 五、三轮 vs 四轮对比（已修复 vs 待修复）

| 类别 | 已修复（11 项） | 待修复（10 项） |
|------|----------------|----------------|
| P0 | 约束集成 + 修复建议 + 备选方案 | — |
| P1 | 压力测试章节 + 相关性警告 + 标准化标题 | 压力测试工具 + 相关性工具 + CI 覆盖 |
| P2 | MCP 测试 + CI 配置 | LLM 行为测试 + 数据时间戳 + pandas 修复 |
| P3 | — | 生成中约束 + 真多 Agent + 风险模型 + 多数据源 |

---

## 六、一句话总结

**当前状态**：约束已程序化、工具层生产级健壮、工作流完整。

**最高 ROI 的 3 件待办**：
1. **LLM 行为测试**（2 天）— 验证 skill 实际输出质量（最大测试缺口）
2. **压力测试工具化**（1 天）— 从"文档说明"到"可执行计算"
3. **数据时间戳**（1 天）— 避免基于过期数据决策

**做完这 3 件，Fund Selector 从"可信赖"升级为"专业级"。**

---

*基于四轮深度尽调（136 测试）+ 11 项 P0/P1/P2 修复后的完整评估。*
