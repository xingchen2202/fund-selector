"""
Data formatting utilities for converting pandas DataFrames to JSON responses.

All MCP tool responses are returned as JSON strings for Claude to parse.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


def slim_df(df: pd.DataFrame) -> pd.DataFrame:
    """General-purpose cleanup: drop all-null columns and internal junk."""
    if df is None or df.empty:
        return df

    df = df.dropna(axis=1, how="all")

    _JUNK_EXACT = {
        "SECUCODE", "SECURITY_CODE", "SECURITY_NAME_ABBR",
        "ORG_CODE", "ORG_TYPE", "SECURITY_TYPE_CODE",
        "NOTICE_DATE", "UPDATE_DATE", "CURRENCY",
    }
    drop_exact = [c for c in df.columns if c.upper() in _JUNK_EXACT]
    drop_qoq = [c for c in df.columns if c.upper().endswith("_QOQ")]
    all_drop = set(drop_exact + drop_qoq)
    if all_drop:
        df = df.drop(columns=list(all_drop), errors="ignore")

    return df


def df_to_json(
    df: pd.DataFrame,
    orient: str = "records",
    max_rows: int | None = None,
    date_format: str = "iso",
) -> str:
    """Convert a pandas DataFrame to a JSON string."""
    if df is None or df.empty:
        return json.dumps([], ensure_ascii=False)

    df = df.dropna(axis=1, how="all")

    if max_rows is not None and len(df) > max_rows:
        df = df.head(max_rows)

    for col in df.select_dtypes(include=["datetime64", "datetimetz"]).columns:
        df[col] = df[col].astype(str)

    return df.to_json(orient=orient, force_ascii=False, date_format=date_format)


def dict_to_json(data: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Convert a dict or list of dicts to a JSON string."""
    return json.dumps(data, ensure_ascii=False, default=str)


def error_response(message: str, tool_name: str = "") -> str:
    """Create a standardized error response JSON string."""
    return json.dumps(
        {
            "error": True,
            "message": message,
            "tool": tool_name,
        },
        ensure_ascii=False,
    )
