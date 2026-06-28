"""
基金筛选器 v2.0 - 基于 akshare 的全市场选基工具
数据来源：天天基金网 (fund.eastmoney.com)，与支付宝销售的基金一致

依赖安装:
  pip install akshare pandas openpyxl

使用方法:
  1. 直接运行查看默认筛选结果: python fund_selector.py
  2. 修改 main() 中的筛选条件自定义
  3. 输出结果保存为 Excel 文件（每个筛选条件一个 sheet）
"""

import akshare as ak
import pandas as pd
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')


# ============================================================
# 第一部分: 数据获取
# ============================================================

def fetch_open_fund_ranking(fund_type="全部"):
    """
    获取开放式基金排行
    fund_type: "全部", "股票型", "混合型", "债券型", "指数型", "QDII", "LOF", "FOF"
    """
    print(f"  正在获取 {fund_type} 开放式基金排行...")
    try:
        df = ak.fund_open_fund_rank_em(symbol=fund_type)
        print(f"    获取到 {len(df)} 只基金")
        return df
    except Exception as e:
        print(f"    获取失败: {e}")
        return pd.DataFrame()


def fetch_etf_ranking():
    """获取场内 ETF 排行"""
    print("  正在获取场内 ETF 排行...")
    try:
        df = ak.fund_exchange_rank_em()
        print(f"    获取到 {len(df)} 只 ETF")
        return df
    except Exception as e:
        print(f"    获取失败: {e}")
        return pd.DataFrame()


def fetch_money_fund_ranking():
    """获取货币基金排行"""
    print("  正在获取货币基金排行...")
    try:
        df = ak.fund_money_rank_em()
        print(f"    获取到 {len(df)} 只货币基金")
        return df
    except Exception as e:
        print(f"    获取失败: {e}")
        return pd.DataFrame()


def fetch_etf_hist(fund_code, period="daily", start_date=None, end_date=None):
    """获取基金/ETF 历史净值"""
    try:
        df = ak.fund_etf_hist_em(fund=fund_code, period=period,
                                  start_date=start_date, end_date=end_date, adjust="qfq")
        return df
    except Exception:
        return pd.DataFrame()


# ============================================================
# 第二部分: 筛选器
# ============================================================

def filter_funds(df, conditions):
    """
    按条件筛选基金

    conditions 字典支持:
      - min_return_1m / max_return_1m: 近1月收益率范围(%)
      - min_return_3m / max_return_3m: 近3月收益率范围(%)
      - min_return_6m / max_return_6m: 近6月收益率范围(%)
      - min_return_1y / max_return_1y: 近1年收益率范围(%)
      - min_scale / max_scale: 规模范围(亿元)
      - fund_name_contains: 基金名称包含关键词
      - exclude_name: 排除名称关键词
    """
    if df.empty:
        return df

    filtered = df.copy()

    # 按收益率筛选 — 自动匹配列名
    for period_key, col_names in [
        ('return_1m', ['近1月收益率', '近1月', '近1月涨跌幅']),
        ('return_3m', ['近3月收益率', '近3月', '近3月涨跌幅']),
        ('return_6m', ['近6月收益率', '近6月', '近6月涨跌幅']),
        ('return_1y', ['近1年收益率', '近1年', '近1年涨跌幅']),
    ]:
        actual_col = None
        for col in col_names:
            if col in filtered.columns:
                actual_col = col
                break
        if actual_col is None:
            continue

        filtered[actual_col] = pd.to_numeric(filtered[actual_col], errors='coerce')

        min_key = f'min_{period_key}'
        max_key = f'max_{period_key}'
        if min_key in conditions and conditions[min_key] is not None:
            filtered = filtered[filtered[actual_col] >= conditions[min_key]]
        if max_key in conditions and conditions[max_key] is not None:
            filtered = filtered[filtered[actual_col] <= conditions[max_key]]

    # 按规模筛选
    if 'min_scale' in conditions or 'max_scale' in conditions:
        scale_col = None
        for col in ['规模', '规模(亿元)', '基金规模']:
            if col in filtered.columns:
                scale_col = col
                break
        if scale_col:
            filtered[scale_col] = pd.to_numeric(filtered[scale_col], errors='coerce')
            # 统一转为亿元
            if filtered[scale_col].mean() > 100000:
                filtered[scale_col] = filtered[scale_col] / 100000000
            if 'min_scale' in conditions:
                filtered = filtered[filtered[scale_col] >= conditions['min_scale']]
            if 'max_scale' in conditions:
                filtered = filtered[filtered[scale_col] <= conditions['max_scale']]

    # 按名称关键词筛选
    name_col = None
    for col in ['基金简称', '基金名称', 'name']:
        if col in filtered.columns:
            name_col = col
            break

    if name_col:
        if 'fund_name_contains' in conditions:
            filtered = filtered[filtered[name_col].str.contains(conditions['fund_name_contains'], na=False)]
        if 'exclude_name' in conditions:
            filtered = filtered[~filtered[name_col].str.contains(conditions['exclude_name'], na=False)]

    return filtered


# ============================================================
# 第三部分: 输出
# ============================================================

def export_to_excel(data_dict, filename=None):
    """导出多个 DataFrame 到 Excel"""
    if filename is None:
        filename = f"fund_screening_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        for sheet_name, df in data_dict.items():
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    print(f"\n结果已保存到: {filename}")
    return filename


def print_summary(df, title, max_rows=15):
    """打印摘要"""
    print(f"\n{'='*70}")
    print(f" {title} (共 {len(df)} 只)")
    print(f"{'='*70}")
    if df.empty:
        print("  无数据")
        return
    # 只打印关键列
    key_cols = [c for c in df.columns if any(k in c for k in ['代码', '简称', '名称', '近', '年', '规模', '净值', '收益'])]
    if not key_cols:
        key_cols = list(df.columns[:8])
    print(df[key_cols].head(max_rows).to_string(index=False))


# ============================================================
# 第四部分: 主流程
# ============================================================

def main():
    print("=" * 70)
    print(" 基金筛选器 v2.0")
    print(f" 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = {}

    # ----------------------------------------------------------
    # Step 1: 获取全市场基金排行
    # ----------------------------------------------------------
    print("\n[Step 1] 获取全市场基金数据...")

    all_open = fetch_open_fund_ranking("全部")
    stock = fetch_open_fund_ranking("股票型")
    index = fetch_open_fund_ranking("指数型")
    qdii = fetch_open_fund_ranking("QDII")
    bond = fetch_open_fund_ranking("债券型")
    etf = fetch_etf_ranking()

    results["01_全市场排行"] = all_open
    results["02_股票型排行"] = stock
    results["03_指数型排行"] = index
    results["04_QDII排行"] = qdii
    results["05_债券型排行"] = bond
    results["06_ETF排行"] = etf

    # ----------------------------------------------------------
    # Step 2: 按条件筛选
    # ----------------------------------------------------------
    print("\n[Step 2] 按条件筛选...")

    # 筛选 A: 近 6 月涨幅 10%~50% 的股票型（规模 >5 亿，排除 ETF 联接）
    if not stock.empty:
        fa = filter_funds(stock, {
            'min_return_6m': 10, 'max_return_6m': 50,
            'min_scale': 5,
            'exclude_name': 'ETF联接',
        })
        results["07_A_近6月10-50pct股票型"] = fa
        print_summary(fa, "A: 近6月涨幅10%-50% 股票型(规模>5亿,排除ETF联接)")

    # 筛选 B: 近 1 年正收益 QDII（规模 >3 亿）
    if not qdii.empty:
        fb = filter_funds(qdii, {
            'min_return_1y': 0, 'max_return_1y': 100,
            'min_scale': 3,
        })
        results["08_B_近1年正收益QDII"] = fb
        print_summary(fb, "B: 近1年正收益 QDII(规模>3亿)")

    # 筛选 C: 近 3 月涨幅 >5% 的指数型（规模 >10 亿）
    if not index.empty:
        fc = filter_funds(index, {
            'min_return_3m': 5, 'max_return_3m': 100,
            'min_scale': 10,
        })
        results["09_C_近3月涨幅5pct指数型"] = fc
        print_summary(fc, "C: 近3月涨幅>5% 指数型(规模>10亿)")

    # 筛选 D: 近 1 年 2%~15% 的债券型（防守型）
    if not bond.empty:
        fd = filter_funds(bond, {
            'min_return_1y': 2, 'max_return_1y': 15,
            'min_scale': 10,
        })
        results["10_D_近1年2-15pct债券型"] = fd
        print_summary(fd, "D: 近1年收益2%-15% 债券型(规模>10亿)")

    # ----------------------------------------------------------
    # Step 3: 针对你的持仓做互补推荐
    # ----------------------------------------------------------
    print("\n[Step 3] 针对你的持仓做互补推荐...")

    if not all_open.empty:
        # 红利低波（与你 40% 科技持仓互补）
        fr1 = filter_funds(all_open, {
            'fund_name_contains': '红利',
            'min_return_6m': 0,
            'min_scale': 5,
        })
        results["11_推荐_红利低波"] = fr1
        print_summary(fr1, "推荐: 红利低波基金(与科技持仓互补)")

        # 医药主题
        fr2 = filter_funds(all_open, {
            'fund_name_contains': '医药',
            'min_return_6m': -5, 'max_return_6m': 30,
            'min_scale': 5,
        })
        results["12_推荐_医药主题"] = fr2
        print_summary(fr2, "推荐: 医药主题基金(与科技低相关)")

        # 消费主题
        fr3 = filter_funds(all_open, {
            'fund_name_contains': '消费',
            'min_return_6m': -5, 'max_return_6m': 30,
            'min_scale': 5,
        })
        results["13_推荐_消费主题"] = fr3
        print_summary(fr3, "推荐: 消费主题基金(防守+成长)")

    # ----------------------------------------------------------
    # Step 4: 导出 Excel
    # ----------------------------------------------------------
    print("\n[Step 4] 导出结果...")
    export_to_excel(results)

    print("\n" + "=" * 70)
    print(" 筛选完成！")
    print(" Excel 文件中每个 sheet 对应一个筛选条件，可翻页查看完整数据。")
    print("=" * 70)


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    main()
