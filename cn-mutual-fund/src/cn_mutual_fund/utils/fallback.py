"""
Multi-source fallback utility.

Tries multiple AKShare data source functions in order.
If the primary fails, automatically falls back to alternatives.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

import pandas as pd

logger = logging.getLogger("cn-mutual-fund")


async def call_with_fallback(
    *sources: tuple[str, Callable, dict[str, Any]],
) -> pd.DataFrame:
    """Try multiple data source functions in order, return the first success."""
    last_error: Exception | None = None

    for name, func, kwargs in sources:
        try:
            df = func(**kwargs)
            if df is not None and not df.empty:
                logger.debug(f"[{name}] 成功, {len(df)} 行")
                return df
            logger.debug(f"[{name}] 返回空数据, 尝试下一个源")
            continue
        except Exception as e:
            last_error = e
            logger.debug(f"[{name}] 失败: {type(e).__name__}: {e}")
            continue

    if last_error:
        raise last_error
    return pd.DataFrame()


def try_sources_sync(
    *sources: tuple[str, Callable, dict[str, Any]],
) -> pd.DataFrame:
    """Synchronous version of call_with_fallback."""
    last_error: Exception | None = None

    for name, func, kwargs in sources:
        try:
            df = func(**kwargs)
            if df is not None and not df.empty:
                logger.debug(f"[{name}] 成功, {len(df)} 行")
                return df
            logger.debug(f"[{name}] 返回空数据, 尝试下一个源")
            continue
        except Exception as e:
            last_error = e
            logger.debug(f"[{name}] 失败: {type(e).__name__}: {e}")
            continue

    if last_error:
        raise last_error
    return pd.DataFrame()
