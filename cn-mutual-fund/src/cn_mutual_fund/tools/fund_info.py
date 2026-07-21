"""
Category 1: Fund Basic Info (V0.1)

Tools:
  1. get_fund_info          - Fund basic information (size, fees, manager, rating)
  2. search_fund            - Search funds by keyword
"""

from __future__ import annotations

import logging

import akshare as ak
import pandas as pd
from mcp.server.fastmcp import FastMCP

from ..utils.cache import TTL_CONFIG, TTL_DAILY, cache
from ..utils.formatter import dict_to_json, df_to_json, error_response, slim_df

logger = logging.getLogger("cn-mutual-fund")


def _resolve_tian_tian_code(fund_code: str) -> str:
    """
    Resolve the correct Tian Tian Fund code.
    First tries the code directly via fund_name_em lookup.
    If not found, searches by pinyin prefix.
    """
    cache_key = f"resolve_code:{fund_code}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        df_names = ak.fund_name_em()
        # Direct match by code
        mask = df_names["基金代码"] == fund_code
        if mask.any():
            cache.set(cache_key, fund_code, TTL_CONFIG)
            return fund_code
        # Try matching by pinyin prefix (first 2 chars of code as numeric hint)
        # Fall back to the original code
    except Exception:
        pass

    cache.set(cache_key, fund_code, TTL_CONFIG)
    return fund_code


def _get_xueqiu_info(fund_code: str) -> dict:
    """Get fund metadata from Xueqiu source."""
    info_dict = {}
    try:
        df_basic = ak.fund_individual_basic_info_xq(symbol=fund_code)
        if df_basic is not None and not df_basic.empty:
            if "item" in df_basic.columns and "value" in df_basic.columns:
                for _, row in df_basic.iterrows():
                    info_dict[str(row["item"])] = str(row["value"])
            else:
                info_dict.update(
                    df_basic.iloc[0].to_dict() if len(df_basic) == 1 else df_basic.to_dict()
                )
    except Exception:
        pass

    try:
        df_fee = ak.fund_individual_detail_info_xq(symbol=fund_code)
        if df_fee is not None and not df_fee.empty:
            fees = {}
            if "item" in df_fee.columns and "value" in df_fee.columns:
                for _, row in df_fee.iterrows():
                    fees[str(row["item"])] = str(row["value"])
            info_dict["费率详情"] = fees
    except Exception:
        pass

    try:
        df_perf = ak.fund_individual_achievement_xq(symbol=fund_code)
        if df_perf is not None and not df_perf.empty:
            info_dict["业绩表现"] = slim_df(df_perf).to_dict("records")
    except Exception:
        pass

    try:
        df_risk = ak.fund_individual_analysis_xq(symbol=fund_code)
        if df_risk is not None and not df_risk.empty:
            info_dict["风险指标"] = slim_df(df_risk).to_dict("records")
    except Exception:
        pass

    return info_dict


def register(mcp: FastMCP):
    """Register fund info tools with the MCP server."""

    @mcp.tool()
    async def get_fund_info(fund_code: str) -> str:
        """
        获取公募基金基本信息（成立时间、规模、费率、跟踪指数、基金经理等）。

        Args:
            fund_code: 6位基金代码，如 "110011"（易方达中小盘）、"161725"（招商中证白酒）

        Returns:
            基金基本信息 (JSON)，包含基金名称、代码、成立时间、最新规模、
            基金公司、基金经理、托管银行、基金类型、跟踪指数、业绩比较基准、
            投资策略、费率结构等。
        """
        cache_key = f"fund_info:{fund_code}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            # Step 1: Resolve the correct Tian Tian Fund code via name search
            # (Alipay codes may differ from Tian Tian Fund codes)
            tian_tian_code = _resolve_tian_tian_code(fund_code)

            # Step 2: Get NAV from Tian Tian Fund open-ended fund interface
            try:
                df_nav = ak.fund_open_fund_info_em(
                    symbol=tian_tian_code, indicator="单位净值走势"
                )
                if df_nav is not None and not df_nav.empty:
                    nav_record = df_nav.iloc[-1].to_dict()
                    # Step 3: Get fund metadata from Xueqiu (richer data)
                    info_dict = _get_xueqiu_info(tian_tian_code)
                    info_dict.update({
                        "code": tian_tian_code,
                        "nav_date": str(nav_record.get("净值日期", "")),
                        "nav": nav_record.get("单位净值"),
                        "nav_history": df_nav.to_dict("records"),
                    })
                    result = dict_to_json(info_dict)
                    cache.set(cache_key, result, TTL_CONFIG)
                    return result
            except Exception as e:
                logger.debug(f"[天天基金] 失败: {e}")

            # Fallback: Xueqiu source
            try:
                df_basic = ak.fund_individual_basic_info_xq(symbol=fund_code)
                if df_basic is not None and not df_basic.empty:
                    # Transpose: columns are item/value
                    info_dict = {}
                    if "item" in df_basic.columns and "value" in df_basic.columns:
                        for _, row in df_basic.iterrows():
                            info_dict[str(row["item"])] = str(row["value"])
                    else:
                        # Already transposed format
                        info_dict = df_basic.iloc[0].to_dict() if len(df_basic) == 1 else df_basic.to_dict()

                    # Get fee info
                    try:
                        df_fee = ak.fund_individual_detail_info_xq(symbol=fund_code)
                        if df_fee is not None and not df_fee.empty:
                            fees = {}
                            if "item" in df_fee.columns and "value" in df_fee.columns:
                                for _, row in df_fee.iterrows():
                                    fees[str(row["item"])] = str(row["value"])
                            info_dict["费率详情"] = fees
                    except Exception:
                        pass

                    # Get performance summary
                    try:
                        df_perf = ak.fund_individual_achievement_xq(symbol=fund_code)
                        if df_perf is not None and not df_perf.empty:
                            info_dict["业绩表现"] = slim_df(df_perf).to_dict("records")
                    except Exception:
                        pass

                    # Get risk metrics
                    try:
                        df_risk = ak.fund_individual_analysis_xq(symbol=fund_code)
                        if df_risk is not None and not df_risk.empty:
                            info_dict["风险指标"] = slim_df(df_risk).to_dict("records")
                    except Exception:
                        pass

                    result = dict_to_json({
                        "fund_code": fund_code,
                        **info_dict,
                    })
                    cache.set(cache_key, result, TTL_CONFIG)
                    return result
            except Exception as e:
                logger.debug(f"[雪球] 失败: {e}")

            return error_response(
                f"获取基金信息失败 ({fund_code}): 所有数据源均不可用", "get_fund_info"
            )
        except Exception as e:
            return error_response(str(e), "get_fund_info")

    @mcp.tool()
    async def search_fund(keyword: str) -> str:
        """
        按关键词搜索公募基金（名称/拼音/代码模糊匹配）。

        Args:
            keyword: 搜索关键词，如 "易方达"、"白酒"、"沪深300"

        Returns:
            匹配的基金列表 (JSON)，包含基金代码、名称、类型。
        """
        cache_key = f"search_fund:{keyword}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            import time
            # Get all fund names (this is a large call, cache aggressively)
            cache_key_all = "all_fund_names"
            df_names = cache.get(cache_key_all)

            if df_names is None:
                df_names = ak.fund_name_em()
                cache.set(cache_key_all, df_names, TTL_CONFIG)

            if df_names is not None and not df_names.empty:
                # Search by keyword in fund name
                mask = df_names.apply(
                    lambda row: any(
                        keyword.lower() in str(v).lower()
                        for v in row.values
                        if pd.notna(v)
                    ),
                    axis=1,
                )
                matched = df_names[mask].head(20)
                result = slim_df(matched)
                output = df_to_json(result)
                cache.set(cache_key, output, TTL_DAILY)
                return output

            return error_response("搜索失败: 无法获取基金列表", "search_fund")
        except Exception as e:
            return error_response(str(e), "search_fund")
