"""
Category 5: Fund Rating (V0.2)

Tools:
  6. get_fund_rating        - Third-party ratings (Morningstar, Shanghai Securities, etc.)
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
    """Register fund rating tools with the MCP server."""

    @mcp.tool()
    async def get_fund_rating(fund_code: str) -> str:
        """
        获取基金第三方评级数据（晨星、上海证券、招商证券、济安金信等）。

        Args:
            fund_code: 6位基金代码，如 "110011"

        Returns:
            基金评级数据 (JSON)，包含各机构评级（3年/5年）、综合评级、基金经理、基金公司等。
        """
        cache_key = f"fund_rating:{fund_code}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            import time

            # Get all ratings and filter
            cache_key_all = "all_fund_ratings"
            df_ratings = cache.get(cache_key_all)

            if df_ratings is None:
                df_ratings = ak.fund_rating_all()
                cache.set(cache_key_all, df_ratings, TTL_CONFIG)
                time.sleep(0.5)  # Rate limit

            if df_ratings is not None and not df_ratings.empty:
                # Find code column
                code_col = None
                for c in df_ratings.columns:
                    if "代码" in str(c) or "code" in str(c).lower():
                        code_col = c
                        break

                if code_col:
                    mask = df_ratings[code_col].astype(str).str.strip() == fund_code
                    matched = df_ratings[mask]
                    if not matched.empty:
                        result = {
                            "fund_code": fund_code,
                            "ratings": slim_df(matched).to_dict("records"),
                        }
                        output = dict_to_json(result)
                        cache.set(cache_key, output, TTL_CONFIG)
                        return output

            # If not found in all ratings, try specific agency ratings
            # Try Morningstar (晨星)
            try:
                df_sh = ak.fund_rating_sh(date="20240630")
                if df_sh is not None and not df_sh.empty:
                    for c in df_sh.columns:
                        if "代码" in str(c):
                            mask = df_sh[c].astype(str).str.strip() == fund_code
                            matched = df_sh[mask]
                            if not matched.empty:
                                result = {
                                    "fund_code": fund_code,
                                    "source": "上海证券",
                                    "ratings": slim_df(matched).to_dict("records"),
                                }
                                output = dict_to_json(result)
                                cache.set(cache_key, output, TTL_CONFIG)
                                return output
                            break
            except Exception:
                pass

            return error_response(
                f"未找到基金评级数据 ({fund_code})。可能该基金成立不足3年或无评级。",
                "get_fund_rating",
            )
        except Exception as e:
            return error_response(str(e), "get_fund_rating")
