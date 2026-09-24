"""backtest.py —— 回测模块（方案 A 重构完成）。

向量化实现：将"连续上涨段买入、回落段清仓"切分为 run 后用 numpy 批量
计算现金流；结果按价格序列缓存，重复回测同一序列时直接命中缓存。
"""

from functools import lru_cache
from typing import Sequence

import numpy as np

_INITIAL_CASH = 10000.0
_CACHE_SIZE = 128


@lru_cache(maxsize=_CACHE_SIZE)
def _run_backtest_cached(prices: tuple) -> dict:
    if len(prices) < 2:
        return {"final_value": _INITIAL_CASH, "trades": 0}

    p = np.asarray(prices, dtype=float)
    rises = np.diff(p) > 0
    m = rises.size

    padded = np.concatenate(([False], rises, [False]))
    starts = np.flatnonzero(~padded[:-1] & padded[1:])
    ends = np.flatnonzero(padded[:-1] & ~padded[1:])
    lengths = ends - starts

    cum = np.concatenate(([0.0], np.cumsum(p)))
    costs = cum[ends + 1] - cum[starts + 1]
    closed = ends < m

    cash = _INITIAL_CASH + float(np.dot(p[ends[closed] + 1], lengths[closed])) - float(costs.sum())
    position = int(lengths[~closed].sum())
    final = cash + position * float(p[-1])
    return {"final_value": final, "trades": position}


def run_backtest(prices: Sequence[float]) -> dict:
    """对价格序列跑一遍简单回测，返回汇总指标。"""
    return _run_backtest_cached(tuple(prices))
