# PLAN-v3: P1-3 经理主理人判定防呆 + P2-1 估值工具失败降级

> 基于 2026-07-24 iteration-3 重测审计报告

## 问题诊断

### P1-3：经理排序反转导致主理人误判

**现象**：
- 2026-07-23 MCP 返回 `"郑晓辉 刘睿聪"`（郑在前）
- 2026-07-24 MCP 返回 `"刘睿聪 郑晓辉"`（刘在前）
- 若模型按 MCP 顺序取第一个为主理人 → 误判刘睿聪

**实际**：
- 郑晓辉 5336 天 > 刘睿聪 1303 天 → 郑晓辉才是主理人

**根因**：iteration-2 规则虽写"比较从业年限"，但未明确禁止按 MCP 顺序取第一个的捷径行为。

### P2-1：估值分位工具返回空

**现象**：
```
get_valuation_metrics("000300") → {error: "估值指标数据为空 (000300)"}
```

**根因**：iteration-2 规则要求调用此工具，但未写工具失败时的降级路径。

---

## 修复方案

### P1-3：经理主理人判定防呆

强化 `.claude/skills/fund-deep-research/SKILL.md` 的经理查询容错规则：

1. **禁止**以 MCP 返回顺序判定主理人
2. **必须**查询并比较每个经理的累计从业时间（天数）
3. 输出附注判定依据："经查询，XX 从业 N 天 > YY 从业 M 天，判定 XX 为主理人"
4. 差距 < 10% → 标注"双经理制，话语权接近"

### P2-1：估值工具失败降级链

在 `.claude/skills/fund-deep-research/SKILL.md` 宏观研判铁律中增加降级链：

```
优先级 1: get_valuation_metrics → 成功则输出 PE + 历史分位
    ↓ 失败
优先级 2: 改用其他 PE/PB 工具 → 输出绝对值 + 标注"分位暂不可用"
    ↓ 失败
优先级 3: 标注 [⚠️ 估值数据不可用] + 用 PMI/M2/北向资金定性判断
    ↓
底线: 严禁编造估值分位数字
```

---

## 文件修改清单

| 文件 | 操作 | 涉及问题 |
|------|------|---------|
| `.claude/skills/fund-deep-research/SKILL.md` | 修改 | P1-3, P2-1 |
| `.claude/skills/asset-allocation/SKILL.md` | 修改（如存在） | P2-1 |
| `.claude/skills/fund-selector/evals/evals.json` | 追加 B3-1~B3-3 | P1-3, P2-1 |

---

## 新增 eval 断言

### B3-1：经理主理人判定
```
prompt: "帮我分析基金 000001 的基金经理，谁是主理人"
assertions:
  - contains "郑晓辉"
  - contains "主理人"
  - contains "从业"（附注判定依据）
  - not_contains "刘睿聪 为主理人"
```

### B3-2：估值工具失败降级
```
prompt: "帮我选基金，当前沪深300 估值分位多少"
assertions:
  - any_of_contains ["分位", "估值数据不可用", "PE", "PMI"]
  - not_contains "约 30% 分位"（严禁编造）
  - not_contains "大约 50% 分位"（严禁编造）
```

### B3-3：经理判定附注从业天数
```
prompt: "帮我分析基金 110011 的基金经理张坤和彭珂，谁话语权更大"
assertions:
  - contains "张坤"
  - contains "主理人"
  - contains "5047"（张坤从业天数）
  - contains "1014"（彭珂从业天数）
```

---

## 验证标准

- B3-1：模型判定郑晓辉为主理人，附注从业天数
- B3-2：估值失败后降级到宏观指标，无编造分位
- B3-3：张坤 5047 天 > 彭珂 1014 天，判定张坤为主理人
- 原有 B1/B2 断言无退化

---

## 执行顺序

1. `.claude/skills/fund-deep-research/SKILL.md` 修改
2. `.claude/skills/asset-allocation/SKILL.md` 修改（如存在）
3. `evals.json` 追加 B3-1~B3-3
4. 运行完整 evals 验证

---

## 与 iteration-2 的关系

| iteration | 修复的问题 | 状态 |
|-----------|-----------|------|
| iteration-2 | P0-1 持仓穿透降级、P0-2 费率多源获取、P1-1 风险指标交叉验证、P1-2 经理查询容错、P2 估值分位查询 | ✅ 已修复 |
| **iteration-3** | **P1-3 经理主理人判定防呆、P2-1 估值工具失败降级** | ⏳ 本次 |
