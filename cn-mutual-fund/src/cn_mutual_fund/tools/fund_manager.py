"""
Category 3: Fund Manager Info (V0.1)

Tools:
  4. get_fund_manager_info   - Manager profile: tenure, products, returns
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
    """Register fund manager tools with the MCP server."""

    @mcp.tool()
    async def get_fund_manager_info(manager_name: str = "", fund_code: str = "") -> str:
        """
        获取基金经理信息（从业年限、管理产品、历史业绩）。
        可通过基金经理姓名或基金代码查询。

        Args:
            manager_name: 基金经理姓名，如 "张坤"、"葛兰"。与 fund_code 二选一。
            fund_code: 6位基金代码，如 "110011"。自动查找该基金的基金经理。

        Returns:
            基金经理信息 (JSON)，包含姓名、所属公司、累计从业时间、
            现任基金列表（代码、名称、年化回报）、管理总规模、最佳回报。
        """
        if not manager_name and not fund_code:
            return error_response("请提供 manager_name 或 fund_code", "get_fund_manager_info")

        cache_key = f"fund_manager:{manager_name or fund_code}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            import time

            # If fund_code provided, first get manager name from fund info
            if fund_code and not manager_name:
                try:
                    df_info = ak.fund_individual_basic_info_xq(symbol=fund_code)
                    if df_info is not None and not df_info.empty:
                        for _, row in df_info.iterrows():
                            item = str(row.get("item", ""))
                            if "基金经理" in item:
                                manager_name = str(row.get("value", ""))
                                break
                except Exception:
                    pass

                if not manager_name:
                    return error_response(
                        f"无法获取基金经理信息 ({fund_code})", "get_fund_manager_info"
                    )

            # Get all managers and filter
            cache_key_all = "all_managers"
            df_managers = cache.get(cache_key_all)

            if df_managers is None:
                df_managers = ak.fund_manager_em()
                cache.set(cache_key_all, df_managers, TTL_CONFIG)
                time.sleep(0.3)  # Rate limit protection

            if df_managers is not None and not df_managers.empty:
                # Filter by manager name
                mask = df_managers.apply(
                    lambda row: any(
                        manager_name.lower() in str(v).lower()
                        for v in row.values
                        if pd.notna(v)
                    ),
                    axis=1,
                )
                matched = df_managers[mask]

                if not matched.empty:
                    # Extract manager profile
                    manager_data = {
                        "manager_name": manager_name,
                        "records": slim_df(matched).to_dict("records"),
                    }

                    # Try to extract structured info
                    first = matched.iloc[0]
                    for col in matched.columns:
                        col_lower = str(col).lower()
                        if any(k in col_lower for k in ["姓名", "name"]):
                            manager_data["name"] = str(first[col])
                        elif any(k in col_lower for k in ["公司", "company", "基金"]):
                            manager_data["company"] = str(first[col])
                        elif any(k in col_lower for k in ["年限", "年", "tenure"]):
                            manager_data["tenure"] = str(first[col])
                        elif any(k in col_lower for k in ["规模", "规模", "aum"]):
                            manager_data["aum"] = str(first[col])
                        elif any(k in col_lower for k in ["回报", "收益", "return"]):
                            manager_data["best_return"] = str(first[col])

                    result = dict_to_json(manager_data)
                    cache.set(cache_key, result, TTL_CONFIG)
                    return result

            return error_response(
                f"未找到基金经理: {manager_name}", "get_fund_manager_info"
            )
        except Exception as e:
            return error_response(str(e), "get_fund_manager_info")
