"""
Category 8: Fund Dividend (V0.2)

Tools:
  9. get_fund_dividend       - Fund dividend / split history
"""

from __future__ import annotations

import logging

import akshare as ak
import pandas as pd
from mcp.server.fastmcp import FastMCP

from ..utils.cache import TTL_CONFIG, cache
from ..utils.formatter import dict_to_json, df_to_json, error_response, slim_df

logger = logging.getLogger("cn-mutual-fund")


def register(mcp: FastMCP):
    """Register fund dividend tools with the MCP server."""

    @mcp.tool()
    async def get_fund_dividend(fund_code: str) -> str:
        """
        获取基金历史分红记录（权益登记日、除息日、分红金额）。

        Args:
            fund_code: 6位基金代码，如 "110011"

        Returns:
            基金分红历史 (JSON)，包含基金代码、名称、权益登记日、
            除息日期、每份分红金额、分红发放日。
        """
        cache_key = f"fund_dividend:{fund_code}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            import time

            # Get all dividends for recent years and filter
            current_year = pd.Timestamp.now().year
            all_dividends = []

            for year in range(current_year, current_year - 5, -1):
                try:
                    df = ak.fund_fh_em(year=str(year))
                    if df is not None and not df.empty:
                        # Find code column
                        for c in df.columns:
                            if "代码" in str(c):
                                mask = df[c].astype(str).str.strip() == fund_code
                                matched = df[mask]
                                if not matched.empty:
                                    all_dividends.append(matched)
                                break
                    time.sleep(0.3)
                except Exception:
                    continue

            if all_dividends:
                import pandas as pd
                df_result = pd.concat(all_dividends, ignore_index=True)

                # Rename columns
                col_map = {}
                for c in df_result.columns:
                    if "代码" in c:
                        col_map[c] = "基金代码"
                    elif "简称" in c or "名称" in c:
                        col_map[c] = "基金简称"
                    elif "登记" in c:
                        col_map[c] = "权益登记日"
                    elif "除息" in c:
                        col_map[c] = "除息日期"
                    elif "分红" in c or "每份" in c:
                        col_map[c] = "每份分红"
                    elif "发放" in c:
                        col_map[c] = "分红发放日"
                if col_map:
                    df_result = df_result.rename(columns=col_map)

                result = {
                    "fund_code": fund_code,
                    "dividend_history": slim_df(df_result).to_dict("records"),
                }
                output = dict_to_json(result)
                cache.set(cache_key, output, TTL_CONFIG)
                return output

            return dict_to_json({
                "fund_code": fund_code,
                "dividend_history": [],
                "note": "该基金近5年无分红记录",
            })
        except Exception as e:
            return error_response(str(e), "get_fund_dividend")
