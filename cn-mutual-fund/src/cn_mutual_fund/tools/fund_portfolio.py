"""
Category 4: Fund Portfolio / Holdings (V0.2)

Tools:
  5. get_fund_portfolio     - Fund holdings: top stocks, bonds, industry allocation
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
    """Register fund portfolio tools with the MCP server."""

    @mcp.tool()
    async def get_fund_portfolio(fund_code: str, date: str = "") -> str:
        """
        获取基金季报披露的持仓信息（十大重仓股、债券配置、行业配置）。
        用于穿透分析基金实际投向。

        Args:
            fund_code: 6位基金代码，如 "110011"
            date: 报告年份，如 "2024"。为空则返回最新一期。

        Returns:
            基金持仓信息 (JSON)，包含：
            - stock_holdings: 股票持仓（代码、名称、占净值比例、持股数、市值）
            - bond_holdings: 债券持仓（代码、名称、占净值比例、市值）
            - industry_allocation: 行业配置（行业类别、占净值比例、市值）
        """
        cache_key = f"fund_portfolio:{fund_code}:{date}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            if not date:
                date = str(pd.Timestamp.now().year)

            result = {"fund_code": fund_code, "report_date": date}

            # Stock holdings
            try:
                import time
                df_stock = ak.fund_portfolio_hold_em(symbol=fund_code, date=date)
                if df_stock is not None and not df_stock.empty:
                    # Rename columns for clarity
                    col_map = {}
                    for c in df_stock.columns:
                        if "代码" in c and "股票" not in c:
                            col_map[c] = "股票代码"
                        elif "名称" in c and "股票" not in c:
                            col_map[c] = "股票名称"
                        elif "占净值" in c or "比例" in c:
                            col_map[c] = "占净值比例(%)"
                        elif "持股数" in c:
                            col_map[c] = "持股数"
                        elif "市值" in c:
                            col_map[c] = "持仓市值"
                    if col_map:
                        df_stock = df_stock.rename(columns=col_map)
                    result["stock_holdings"] = slim_df(df_stock).to_dict("records")
            except Exception as e:
                logger.debug(f"[股票持仓] 失败: {e}")
                result["stock_holdings"] = []

            time.sleep(0.3)  # Rate limit

            # Bond holdings
            try:
                df_bond = ak.fund_portfolio_bond_hold_em(symbol=fund_code, date=date)
                if df_bond is not None and not df_bond.empty:
                    col_map = {}
                    for c in df_bond.columns:
                        if "代码" in c:
                            col_map[c] = "债券代码"
                        elif "名称" in c:
                            col_map[c] = "债券名称"
                        elif "占净值" in c or "比例" in c:
                            col_map[c] = "占净值比例(%)"
                        elif "市值" in c:
                            col_map[c] = "持仓市值"
                    if col_map:
                        df_bond = df_bond.rename(columns=col_map)
                    result["bond_holdings"] = slim_df(df_bond).to_dict("records")
            except Exception as e:
                logger.debug(f"[债券持仓] 失败: {e}")
                result["bond_holdings"] = []

            time.sleep(0.3)  # Rate limit

            # Industry allocation
            try:
                df_industry = ak.fund_portfolio_industry_allocation_em(symbol=fund_code, date=date)
                if df_industry is not None and not df_industry.empty:
                    col_map = {}
                    for c in df_industry.columns:
                        if "行业" in c or "类别" in c:
                            col_map[c] = "行业类别"
                        elif "占净值" in c or "比例" in c:
                            col_map[c] = "占净值比例(%)"
                        elif "市值" in c:
                            col_map[c] = "配置市值"
                    if col_map:
                        df_industry = df_industry.rename(columns=col_map)
                    result["industry_allocation"] = slim_df(df_industry).to_dict("records")
            except Exception as e:
                logger.debug(f"[行业配置] 失败: {e}")
                result["industry_allocation"] = []

            output = dict_to_json(result)
            cache.set(cache_key, output, TTL_CONFIG)
            return output
        except Exception as e:
            return error_response(str(e), "get_fund_portfolio")
