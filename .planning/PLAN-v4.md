# PLAN-v4: Iteration 3 — P7/P8/P9 数据质量修复

> 修复三个数据缺陷：最大回撤过滤失效、VaR 假精确、新闻分类错误
> 日期：2026-06-29

---

## 问题诊断汇总

| ID | 现象 | 根因 | 严重度 |
|----|------|------|--------|
| P7 | -75% 混合型基金仍被推荐 | generate_recommend.py 只显示回撤，不过滤；单字段语义不明 | 🔴 高 |
| P8 | 三只基金 VaR 完全相同 45.82元 | calc_var_impact.py 用固定 vol=0.15，未读 NAV 序列 | 🔴 高 |
| P9 | "走弱"被标为利多 | NEGATIVE_WORDS 缺词，单一新闻源 | 🟡 中 |

---

## P7 — 最大回撤过滤器修复

### 根因

1. `validate_funds.py:136` — `max_drawdown` 留为 None，不获取
2. `generate_recommend.py:213` — 只显示，不过滤
3. 整个代码库无 drawdown 过滤函数
4. 单字段 `max_drawdown` 无法区分"近3年"与"成立以来"

### 修复方案

#### 修改 1：SKILL.md Step 3 — Claude 提取双回撤字段

在 Step 3 的 `get_fund_nav_history` 调用说明中增加：

```markdown
调用2：get_fund_nav_history(fund_code=fund_code, period="3y")
  → 提取：
    - return_1y: 近1年收益
    - return_3y: 近3年收益（成立≥3年时）
    - drawdown_3y: 近3年最大回撤（从净值序列计算，窗口=3年）
    - drawdown_inception: 成立以来最大回撤（API 直接返回）
    - nav_history: 净值序列（用于 VaR 计算和回撤验证）
  → 注意：若基金成立<3年，drawdown_3y 设为 null，
    过滤时使用 drawdown_inception + 放宽阈值
```

#### 修改 2：generate_recommend.py — 新增 filter_by_drawdown()

在 `generate_report()` 的候选处理逻辑中，`limit_candidates()` 之前插入：

```python
# 基金类型 → 回撤阈值（绝对值）
DRAWDOWN_THRESHOLDS = {
    "股票型": 0.35,
    "混合型": 0.25,
    "债券型": 0.10,
}
DRAWDOWN_RELAXED = 0.50  # 成立以来数据放宽阈值


def classify_fund_type(fund_name, sector):
    """根据基金名称和板块推断基金类型（股票型/混合型/债券型）"""
    if not fund_name:
        return "混合型"
    name = fund_name.lower()
    if any(w in name for w in ["债券", "债", "中短债", "纯债"]):
        return "债券型"
    if any(w in name for w in ["股票", "股"]):
        return "股票型"
    # 灵活配置、混合、均衡 → 混合型
    return "混合型"


def filter_by_drawdown(candidates, fund_details):
    """
    按最大回撤阈值过滤候选基金。

    规则：
    - 优先使用 drawdown_3y（近3年）
    - 缺失时使用 drawdown_inception（成立以来）+ 放宽阈值 -50%
    - 两者都缺失：保留，标注"[⚠️ 回撤数据缺失]"
    """
    filtered = []
    for c in candidates:
        code = c.get("code", "")
        name = c.get("name", "")
        detail = {}
        for f in fund_details:
            if f.get("code") == code:
                detail = f
                break

        fund_type = classify_fund_type(name, c.get("sector", ""))
        threshold = DRAWDOWN_THRESHOLDS.get(fund_type, 0.25)

        dd_3y = detail.get("drawdown_3y")
        dd_inception = detail.get("drawdown_inception")

        if dd_3y is not None:
            if abs(dd_3y) <= threshold:
                filtered.append(c)
                print(f"[DRAWDOWN] {code} {name}: 近3年{dd_3y:.2%} ≤ {threshold:.0%} ✅",
                      file=sys.stderr)
            else:
                print(f"[EXCLUDE] {code} {name}: 近3年回撤{dd_3y:.2%} > {threshold:.0%}（{fund_type}）❌",
                      file=sys.stderr)
        elif dd_inception is not None:
            # 数据降级：使用成立以来 + 放宽阈值
            if abs(dd_inception) <= DRAWDOWN_RELAXED:
                c["_drawdown_relaxed"] = True
                filtered.append(c)
                print(f"[DRAWDOWN] {code} {name}: 成立以来{dd_inception:.2%}（放宽阈值{DRAWDOWN_RELAXED:.0%}）⚠️",
                      file=sys.stderr)
            else:
                print(f"[EXCLUDE] {code} {name}: 成立以来回撤{dd_inception:.2%} > {DRAWDOWN_RELAXED:.0%} ❌",
                      file=sys.stderr)
        else:
            # 完全无数据
            c["_drawdown_missing"] = True
            filtered.append(c)
            print(f"[WARN] {code} {name}: 回撤数据缺失，保留待人工核实", file=sys.stderr)

    return filtered
```

#### 修改 3：generate_recommend.py — 报告标注时间范围

```python
# 最大回撤显示（标注时间范围）
dd_3y = fund_detail.get("drawdown_3y")
dd_inception = fund_detail.get("drawdown_inception")
dd_parts = []
if dd_3y is not None:
    dd_parts.append(f"近3年：{dd_3y:+.2f}%")
if dd_inception is not None:
    dd_parts.append(f"成立以来：{dd_inception:+.2f}%")
if dd_parts:
    max_dd_str = " | ".join(dd_parts)
else:
    max_dd_str = "数据缺失"

# 如果使用了放宽阈值，添加提示
if c.get("_drawdown_relaxed"):
    max_dd_str += " [成立以来，非近3年]"
```

#### 修改 4：rule-definitions.md — 明确阈值适用时间范围

```markdown
### 最大回撤过滤规则（P7修复）
| 基金类型 | 近3年阈值 | 成立以来放宽阈值 |
|---------|----------|----------------|
| 股票型 | < 35% | < 50% |
| 混合型 | < 25% | < 50% |
| 债券型 | < 10% | < 50% |

- **优先使用近3年数据**（drawdown_3y）
- 近3年数据不可用时：使用成立以来数据（drawdown_inception），阈值统一放宽至 -50%
- 两者都缺失：保留待人工核实，标注 [⚠️ 回撤数据缺失]
- 报告中每个回撤数字必须标注时间范围（近3年/成立以来）
- 基金类型判断：名称含"债券/债"→债券型，含"股票/股"→股票型，其余→混合型
```

---

## P8 — VaR 真实波动率计算

### 根因

1. `calc_var_impact.py:64` — `new_fund_vol: float = 0.15` 固定默认值
2. 第 103 行循环中未传入每只基金的实际波动率
3. NAV 序列存在 step3 但 calc_var_impact.py 从未读取

### 修复方案

#### 修改：calc_var_impact.py — 完整重写

```python
#!/usr/bin/env python3
"""
calc_var_impact.py — 基于真实净值序列计算 VaR 影响
━━━━━━━━━━━━━━━━━━━━
读取 step3 的 nav_history，计算每只基金的实际年化波动率，
再计算边际 VaR。无净值序列时标注"数据不足"。
"""
import json
import math
import sys
import io
from pathlib import Path
from statistics import mean, stdev

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
REPORTS_DIR = PROJECT_ROOT / "fund-reports"


def read_step(step_key):
    try:
        script_dir = Path(__file__).parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from pipeline import read_step
        return read_step(step_key)
    except Exception:
        return {}


def write_var_impacts(data):
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from pipeline import write_step
    write_step("step4", {"var_impacts": data})


def compute_annual_volatility(nav_series):
    """
    从净值序列计算年化波动率。

    Args:
        nav_series: list of {"date": "YYYY-MM-DD", "nav": float}

    Returns:
        float: 年化波动率（如 0.25 表示 25%）
        None: 数据不足（少于30个数据点）
    """
    if not nav_series or len(nav_series) < 30:
        return None

    # 按日期排序
    sorted_navs = sorted(nav_series, key=lambda x: x.get("date", ""))
    navs = [item["nav"] for item in sorted_navs if item.get("nav")]

    if len(navs) < 30:
        return None

    # 日收益率
    returns = []
    for i in range(1, len(navs)):
        if navs[i - 1] > 0:
            r = (navs[i] - navs[i - 1]) / navs[i - 1]
            returns.append(r)

    if len(returns) < 29:
        return None

    # 年化波动率 = 日收益率标准差 × √252
    avg = mean(returns)
    variance = sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)
    daily_vol = math.sqrt(variance)
    annual_vol = daily_vol * math.sqrt(252)

    return annual_vol


def compute_marginal_var(investment, annual_vol, existing_var, correlation=0.5):
    """
    计算加入新基金后的边际 VaR。

    月度 VaR（95%）= 投资金额 × 年化波动率 × 1.645 × √(21/252)
    边际 VaR = 组合 VaR(加入后) - 组合 VaR(加入前)
    """
    # 新基金的月度 VaR
    monthly_vol = annual_vol * math.sqrt(21 / 252)
    new_fund_var = investment * monthly_vol * 1.645  # 95% 置信度

    # 组合边际 VaR（考虑相关性）
    combined_var = math.sqrt(
        existing_var ** 2 + new_fund_var ** 2 +
        2 * correlation * existing_var * new_fund_var
    )
    marginal_var = combined_var - existing_var

    return {
        "new_fund_var": round(new_fund_var, 2),
        "combined_var": round(combined_var, 2),
        "marginal_var": round(marginal_var, 2),
        "annual_vol": round(annual_vol, 4),
        "exceeds_budget": marginal_var > 2000,
    }


def main():
    # 读取约束
    step0 = read_step("step0")
    existing_var = step0.get("monthly_var_estimate", 1000)
    existing_value = step0.get("total_value", 50000)

    # 读取候选基金
    step2 = read_step("step2")
    candidates = step2.get("top10", step2.get("candidates", []))
    if not candidates:
        print(json.dumps({"error": "step2 中无 candidates"}))
        sys.exit(1)

    # 读取 step3 获取净值序列
    step3 = read_step("step3")
    verified_funds = step3.get("verified", [])
    if isinstance(verified_funds, dict):
        verified_funds = verified_funds.get("verified", [])

    # 构建 code → nav_history 映射
    nav_map = {}
    for f in verified_funds:
        code = f.get("code", "")
        nav_history = f.get("nav_history")
        if code and nav_history:
            nav_map[code] = nav_history

    # 模拟加入 5% 仓位
    new_fund_value = existing_value * 0.05

    print(f"[INFO] 计算 VaR: 现有VaR={existing_var}, 新增仓位={new_fund_value:.0f}元",
          file=sys.stderr)

    var_results = {}
    for c in candidates:
        code = c.get("code", "")
        name = c.get("name", "")

        nav_series = nav_map.get(code)
        annual_vol = compute_annual_volatility(nav_series) if nav_series else None

        if annual_vol is not None and annual_vol > 0:
            result = compute_marginal_var(new_fund_value, annual_vol, existing_var)
            status = "⚠️ 超出预算" if result["exceeds_budget"] else "✅ 可接受"
            print(f"[VaR] {code} {name}: 年化波动率={annual_vol:.2%}, "
                  f"边际VaR={result['marginal_var']}元 {status}", file=sys.stderr)
        else:
            # 数据不足
            result = {
                "new_fund_var": None,
                "combined_var": None,
                "marginal_var": None,
                "annual_vol": None,
                "exceeds_budget": False,
                "data_insufficient": True,
            }
            print(f"[VaR] {code} {name}: 净值序列不足，无法计算 VaR", file=sys.stderr)

        var_results[code] = {"code": code, "name": name, **result}

    write_var_impacts(var_results)
    print(json.dumps(var_results, ensure_ascii=False, indent=2))
    print(f"\n[INFO] 已写入 step4 ({len(var_results)} 只基金)", file=sys.stderr)


if __name__ == "__main__":
    main()
```

#### 修改：generate_recommend.py — VaR 输出适配

```python
marginal_var = var_info.get("marginal_var")
if marginal_var is None:
    var_str = "数据不足，无法计算（净值序列缺失）"
else:
    var_str = f"{marginal_var} 元"
lines.append(f"  加入 5% 仓位预计增加 VaR：{var_str}")
```

---

## P9 — 新闻正负面分类修复

### 根因

1. `NEGATIVE_WORDS` 缺少常见利空词
2. 矛盾分类时缺少显式保守原则
3. 单一新闻源，无降级链

### 修复方案

#### 修改 1：扩充 NEGATIVE_WORDS（两个 search_news.py）

```python
NEGATIVE_WORDS = [
    # 基础利空
    "下跌", "风险", "监管", "利空", "回调", "亏损",
    "警示", "暴跌", "崩盘", "退市", "违规", "处罚",
    # 趋势走弱
    "走弱", "收紧", "下滑", "承压", "下行", "衰退",
    "降温", "疲软", "低迷", "萎缩", "回落", "阴跌",
    # 资金流出
    "撤资", "减持", "抛售", "流出", "赎回", "缩水",
    # 政策/事件
    "暂停", "叫停", "整顿", "暴雷", "罚款", "调查",
    "限制", "管控", "约束", "收紧", "遏制", "打击",
]

POSITIVE_WORDS = [
    "上涨", "利好", "政策支持", "创新高", "突破",
    "增长", "复苏", "扩张", "布局", "机遇",
    "反弹", "回暖", "走强", "攀升", "大涨",
    "增持", "加仓", "流入", "申购", "扩容",
]
```

#### 修改 2：矛盾分类保守原则

```python
is_negative = any(w in text for w in NEGATIVE_WORDS)
is_positive = any(w in text for w in POSITIVE_WORDS)

# 保守原则：同时含正负面词 → 优先标为利空
if is_negative and is_positive:
    if len(results["negative"]) < 2:
        results["negative"].append(item)
elif is_negative:
    if len(results["negative"]) < 2:
        results["negative"].append(item)
elif is_positive:
    if len(results["positive"]) < 2:
        results["positive"].append(item)
```

#### 修改 3：降级新闻源

```python
def fetch_sector_news(sector):
    """获取板块新闻，带降级链"""
    # 主源：代表性个股新闻
    stock_code = SECTOR_REPRESENTATIVE_STOCKS.get(sector, "510300")
    try:
        import akshare as ak
        df = ak.stock_news_em(symbol=stock_code)
        if df is not None and not df.empty:
            result = filter_news(df, sector)
            if result["positive"] != [f"近{CUTOFF_DAYS}天无明显利多消息"] or \
               result["negative"] != [f"近{CUTOFF_DAYS}天无明显利空消息"]:
                return result
    except Exception as e:
        print(f"[WARN] 主源失败({sector}): {e}", file=sys.stderr)

    # 降级1：全市场新闻（平安银行作为代理）
    try:
        import akshare as ak
        df = ak.stock_news_em(symbol="000001")
        if df is not None and not df.empty:
            result = filter_news(df, sector)
            if result["positive"] != [f"近{CUTOFF_DAYS}天无明显利多消息"] or \
               result["negative"] != [f"近{CUTOFF_DAYS}天无明显利空消息"]:
                return result
    except Exception:
        pass

    # 降级2：百度经济新闻
    try:
        import akshare as ak
        df = ak.news_economic_baidu(category="股票")
        if df is not None and not df.empty:
            result = filter_news(df, sector)
            if result["positive"] != [f"近{CUTOFF_DAYS}天无明显利多消息"] or \
               result["negative"] != [f"近{CUTOFF_DAYS}天无明显利空消息"]:
                return result
    except Exception:
        pass

    return {
        "positive": [f"近{CUTOFF_DAYS}天无明显利多消息"],
        "negative": [f"近{CUTOFF_DAYS}天无明显利空消息"],
    }
```

---

## evals.json 追加断言

```json
{
  "id": "B7-drawdown-filter",
  "description": "P7：最大回撤超阈值的基金应被排除",
  "prompt": "运行/fund:recommend，检查报告和stderr",
  "assertions": [
    {
      "type": "not_contains",
      "value": "最大回撤：-75.55%",
      "description": "003593（回撤-75%）不应出现在推荐中"
    },
    {
      "type": "not_contains",
      "value": "最大回撤：-68.94%",
      "description": "166001（回撤-68%）不应出现在推荐中"
    },
    {
      "type": "stderr_contains",
      "value": "EXCLUDE",
      "description": "stderr应有[EXCLUDE]日志"
    },
    {
      "type": "source_contains",
      "value": "drawdown_3y",
      "description": "step3/validate_funds应产出drawdown_3y字段"
    },
    {
      "type": "source_contains",
      "value": "filter_by_drawdown",
      "description": "generate_recommend.py应包含过滤函数"
    }
  ]
},
{
  "id": "B8-var-unique",
  "description": "P8：不同基金的VaR增量不应完全相同",
  "prompt": "运行/fund:recommend，检查VaR数值",
  "assertions": [
    {
      "type": "source_contains",
      "value": "compute_annual_volatility",
      "description": "calc_var_impact.py应计算真实波动率"
    },
    {
      "type": "source_contains",
      "value": "nav_history",
      "description": "应从NAV序列读取数据"
    },
    {
      "type": "source_not_contains",
      "value": "new_fund_vol=0.15",
      "description": "不应使用固定波动率0.15"
    }
  ]
},
{
  "id": "B9-news-sentiment",
  "description": "P9：新闻正负面分类应正确",
  "prompt": "检查search_news.py源码",
  "assertions": [
    {
      "type": "source_contains",
      "value": "走弱",
      "description": "NEGATIVE_WORDS应包含走弱"
    },
    {
      "type": "source_contains",
      "value": "收紧",
      "description": "NEGATIVE_WORDS应包含收紧"
    },
    {
      "type": "source_contains",
      "value": "is_negative and is_positive",
      "description": "应有矛盾分类保守原则"
    },
    {
      "type": "source_contains",
      "value": "news_economic_baidu",
      "description": "应有降级新闻源"
    }
  ]
}
```

---

## 执行顺序

1. **rule-definitions.md** — 更新回撤阈值说明（P7）
2. **SKILL.md** — Step 3 增加双回撤字段要求（P7）
3. **generate_recommend.py** — 新增 filter_by_drawdown()（P7）
4. **calc_var_impact.py** — 完整重写真实波动率计算（P8）
5. **fund-recommend/scripts/search_news.py** — 扩充词表+保守原则+降级源（P9）
6. **fund-weekly-report/scripts/search_news.py** — 同上（P9）
7. **evals.json** — 追加 B7/B8/B9 断言
8. 运行完整流水线验证

## 验证标准

- [ ] 回撤超阈值基金被排除（stderr 有 [EXCLUDE] 日志）
- [ ] 报告中回撤数字标注"近3年"或"成立以来"
- [ ] 各基金 VaR 数值不同（或标注"数据不足"）
- [ ] 新闻利空分类正确（"走弱""收紧"不在利多）
- [ ] evals.json B1-B9 全部断言通过
