"""
Category 2: Fund NAV History (V0.1)

Tools:
  3. get_fund_nav_history   - Historical NAV (unit/cumulative) for return & drawdown calc
"""

from __future__ import annotations

import logging

import akshare as ak
import pandas as pd
from mcp.server.fastmcp import FastMCP

from ..utils.cache import TTL_DAILY, cache
from ..utils.formatter import df_to_json, error_response, slim_df

logger = logging.getLogger("cn-mutual-fund")


def register(mcp: FastMCP):
    """Register NAV history tools with the MCP server."""

    @mcp.tool()
    async def get_fund_nav_history(
        fund_code: str,
        start_date: str = "",
        end_date: str = "",
        adjust: str = "",
    ) -> str:
        """
        获取基金历史复权净值数据（用于计算最大回撤、夏普比率、卡玛比率等）。

        Args:
            fund_code: 6位基金代码，如 "110011"
            start_date: 开始日期，格式 "YYYYMMDD"，如 "20230101"。为空则返回近1年。
            end_date: 结束日期，格式 "YYYYMMDD"，如 "20241231"。为空则返回到最新。
            adjust: 复权类型，"qfq"(前复权)、"hfq"(后复权)、""(不复权)。默认不复权。

        Returns:
            历史净值数据 (JSON)，每条记录包含净值日期、单位净值、累计净值、日涨跌幅。
            数据按日期升序排列。
        """
        cache_key = f"fund_nav:{fund_code}:{start_date}:{end_date}:{adjust}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            # Default date range: past 1 year
            if not start_date:
                from datetime import datetime, timedelta
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")

            # Try open-end fund NAV
            try:
                df = ak.fund_open_fund_info_em(
                    symbol=fund_code,
                    indicator="单位净值走势",
                    period="成立来",
                )
                if df is not None and not df.empty:
                    # Filter date range
                    if "净值日期" in df.columns:
                        df["净值日期"] = pd.to_datetime(df["净值日期"], errors="coerce")
                        start_dt = pd.to_datetime(start_date, errors="coerce")
                        end_dt = pd.to_datetime(end_date, errors="coerce")
                        if start_dt is not pd.NaT:
                            df = df[df["净值日期"] >= start_dt]
                        if end_dt is not pd.NaT:
                            df = df[df["净值日期"] <= end_dt]
                        df["净值日期"] = df["净值日期"].dt.strftime("%Y-%m-%d")

                    # Rename columns for clarity
                    col_map = {}
                    for c in df.columns:
                        if "净值日期" in c:
                            col_map[c] = "净值日期"
                        elif "单位净值" in c:
                            col_map[c] = "单位净值"
                        elif "累计净值" in c:
                            col_map[c] = "累计净值"
                        elif "日增长" in c:
                            col_map[c] = "日涨跌幅(%)"
                    if col_map:
                        df = df.rename(columns=col_map)

                    result = df_to_json(slim_df(df))
                    cache.set(cache_key, result, TTL_DAILY)
                    return result
            except Exception as e:
                logger.debug(f"[开放基金净值] 失败: {e}, 尝试ETF净值")

            # Fallback: ETF fund NAV
            try:
                df = ak.fund_etf_fund_info_em(
                    fund=fund_code,
                    start_date=start_date,
                    end_date=end_date,
                )
                if df is not None and not df.empty:
                    # Rename columns
                    col_map = {}
                    for c in df.columns:
                        if "净值日期" in c or "日期" in c:
                            col_map[c] = "净值日期"
                        elif "单位净值" in c:
                            col_map[c] = "单位净值"
                        elif "累计净值" in c:
                            col_map[c] = "累计净值"
                        elif "日增长" in c:
                            col_map[c] = "日涨跌幅(%)"
                    if col_map:
                        df = df.rename(columns=col_map)

                    result = df_to_json(slim_df(df))
                    cache.set(cache_key, result, TTL_DAILY)
                    return result
            except Exception as e:
                logger.debug(f"[ETF净值] 失败: {e}")

            # Fallback: LOF fund hist
            try:
                df = ak.fund_lof_hist_em(
                    symbol=fund_code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
                if df is not None and not df.empty:
                    result = df_to_json(slim_df(df))
                    cache.set(cache_key, result, TTL_DAILY)
                    return result
            except Exception:
                pass

            return error_response(
                f"获取净值历史失败 ({fund_code}): 所有数据源均不可用。"
                "请确认代码正确（开放基金/ETF/LOF均支持）。",
                "get_fund_nav_history",
            )
        except Exception as e:
            return error_response(str(e), "get_fund_nav_history")
