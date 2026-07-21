"""
Category 7: Fund Ranking (V0.2)

Tools:
  8. get_fund_ranking       - Fund performance ranking by category
"""

from __future__ import annotations

import logging

import akshare as ak
from mcp.server.fastmcp import FastMCP

from ..utils.cache import TTL_DAILY, cache
from ..utils.formatter import df_to_json, error_response, slim_df

logger = logging.getLogger("cn-mutual-fund")


def register(mcp: FastMCP):
    """Register fund ranking tools with the MCP server."""

    @mcp.tool()
    async def get_fund_ranking(fund_type: str = "全部") -> str:
        """
        获取公募基金业绩排行榜（按类型分组）。

        Args:
            fund_type: 基金类型，可选值：
                "全部"、"股票型"、"混合型"、"债券型"、"指数型"、"QDII"、"FOF"
                默认为 "全部"。

        Returns:
            基金排行榜 (JSON)，包含基金代码、名称、最新净值、日涨跌幅、
            近1周/1月/3月/6月/1年/2年/3年涨幅、今年来涨幅、成立来涨幅。
        """
        cache_key = f"fund_ranking:{fund_type}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            import time

            df = ak.fund_open_fund_rank_em(symbol=fund_type)
            if df is not None and not df.empty:
                # Rename columns for clarity
                col_map = {}
                for c in df.columns:
                    if "代码" in c:
                        col_map[c] = "基金代码"
                    elif "简称" in c or "名称" in c:
                        col_map[c] = "基金简称"
                    elif "日期" in c:
                        col_map[c] = "净值日期"
                    elif "单位净值" in c:
                        col_map[c] = "单位净值"
                    elif "累计净值" in c:
                        col_map[c] = "累计净值"
                    elif "日增长" in c:
                        col_map[c] = "日涨跌幅(%)"
                    elif "近1周" in c:
                        col_map[c] = "近1周(%)"
                    elif "近1月" in c:
                        col_map[c] = "近1月(%)"
                    elif "近3月" in c:
                        col_map[c] = "近3月(%)"
                    elif "近6月" in c:
                        col_map[c] = "近6月(%)"
                    elif "近1年" in c:
                        col_map[c] = "近1年(%)"
                    elif "近2年" in c:
                        col_map[c] = "近2年(%)"
                    elif "近3年" in c:
                        col_map[c] = "近3年(%)"
                    elif "今年来" in c:
                        col_map[c] = "今年来(%)"
                    elif "成立来" in c:
                        col_map[c] = "成立来(%)"
                    elif "手续费" in c:
                        col_map[c] = "手续费"
                if col_map:
                    df = df.rename(columns=col_map)

                result = df_to_json(slim_df(df), max_rows=50)
                cache.set(cache_key, result, TTL_DAILY)
                time.sleep(0.3)
                return result

            return error_response(
                f"获取基金排行失败 (类型: {fund_type})", "get_fund_ranking"
            )
        except Exception as e:
            return error_response(str(e), "get_fund_ranking")
