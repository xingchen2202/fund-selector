"""
Category 6: Fund Money Flow / Share Changes (V0.2)

Tools:
  7. get_fund_money_flow    - Fund subscription/redemption / share changes
"""

from __future__ import annotations

import logging

import akshare as ak
import pandas as pd
from mcp.server.fastmcp import FastMCP

from ..utils.cache import TTL_DAILY, cache
from ..utils.formatter import dict_to_json, df_to_json, error_response, slim_df

logger = logging.getLogger("cn-mutual-fund")


def register(mcp: FastMCP):
    """Register fund money flow tools with the MCP server."""

    @mcp.tool()
    async def get_fund_money_flow(fund_code: str = "") -> str:
        """
        获取基金近期申赎情况（份额变化、申购赎回数据）。
        如不提供基金代码，则返回全市场基金规模变动汇总。

        Args:
            fund_code: 6位基金代码，如 "110011"。为空则返回市场汇总数据。

        Returns:
            基金资金流数据 (JSON)，包含期间申购、期间赎回、期末总份额、期末净资产。
        """
        cache_key = f"fund_flow:{fund_code or 'market'}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            import time

            result = {}

            # Get aggregate scale changes
            try:
                df_scale = ak.fund_scale_change_em()
                if df_scale is not None and not df_scale.empty:
                    col_map = {}
                    for c in df_scale.columns:
                        if "截止日期" in c or "日期" in c:
                            col_map[c] = "截止日期"
                        elif "申购" in c:
                            col_map[c] = "期间申购"
                        elif "赎回" in c:
                            col_map[c] = "期间赎回"
                        elif "总份额" in c:
                            col_map[c] = "期末总份额"
                        elif "净资产" in c or "净值" in c:
                            col_map[c] = "期末净资产"
                    if col_map:
                        df_scale = df_scale.rename(columns=col_map)
                    result["market_scale_changes"] = slim_df(df_scale).to_dict("records")
            except Exception as e:
                logger.debug(f"[规模变动] 失败: {e}")

            time.sleep(0.3)

            # Get holder structure
            try:
                df_hold = ak.fund_hold_structure_em()
                if df_hold is not None and not df_hold.empty:
                    col_map = {}
                    for c in df_hold.columns:
                        if "截止日期" in c or "日期" in c:
                            col_map[c] = "截止日期"
                        elif "机构" in c:
                            col_map[c] = "机构持有比例(%)"
                        elif "个人" in c:
                            col_map[c] = "个人持有比例(%)"
                        elif "内部" in c:
                            col_map[c] = "内部持有比例(%)"
                        elif "总份额" in c:
                            col_map[c] = "总份额"
                    if col_map:
                        df_hold = df_hold.rename(columns=col_map)
                    result["holder_structure"] = slim_df(df_hold).to_dict("records")
            except Exception as e:
                logger.debug(f"[持有人结构] 失败: {e}")

            # If fund_code provided, try to get specific fund scale history
            if fund_code:
                try:
                    # Try Shenzhen exchange scale data (last 6 months)
                    from datetime import datetime, timedelta
                    end = datetime.now()
                    start = end - timedelta(days=180)
                    df_szse = ak.fund_scale_daily_szse(
                        start_date=start.strftime("%Y%m%d"),
                        end_date=end.strftime("%Y%m%d"),
                        symbol="ETF",
                    )
                    if df_szse is not None and not df_szse.empty:
                        # Filter by fund code
                        for c in df_szse.columns:
                            if "代码" in str(c):
                                mask = df_szse[c].astype(str).str.strip() == fund_code
                                matched = df_szse[mask]
                                if not matched.empty:
                                    result["fund_scale_history"] = slim_df(matched).to_dict("records")
                                break
                except Exception as e:
                    logger.debug(f"[ETF规模] 失败: {e}")

            output = dict_to_json(result)
            cache.set(cache_key, output, TTL_DAILY)
            return output
        except Exception as e:
            return error_response(str(e), "get_fund_money_flow")
