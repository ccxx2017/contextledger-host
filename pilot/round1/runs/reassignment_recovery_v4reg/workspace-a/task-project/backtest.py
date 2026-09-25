"""backtest.py —— 回测模块（方案 A 重构版：向量化 + 结果缓存）。

策略语义与基线实现一致：价格较前一日上涨则买入 1 份，
未上涨且有持仓则一次性清仓，期末持仓按最后一日价格估值。
"""

from functools import lru_cache
from typing import Sequence, Tuple

import numpy as np

_INITIAL_CASH = 10000.0
_CACHE_MAXSIZE = 256


@lru_cache(maxsize=_CACHE_MAXSIZE)
def _backtest_core(prices: Tuple[float, ...]) -> dict:
    p = np.asarray(prices, dtype=float)
    n = p.size
    if n < 2:
        return {"final_value": _INITIAL_CASH, "trades": 0}
    p1 = p[1:]
    up = p1 > p[:-1]
    m = up.size
    sell_pos = np.flatnonzero(~up)
    buy_cash = float(p1[up].sum())
    if sell_pos.size:
        run_lens = np.diff(np.concatenate(([-1], sell_pos))) - 1
        sell_cash = float(np.dot(run_lens, p1[sell_pos]))
        position = (m - 1) - int(sell_pos[-1])
    else:
        sell_cash = 0.0
        position = m
    final = _INITIAL_CASH - buy_cash + sell_cash + position * float(p[-1])
    return {"final_value": final, "trades": position}


def run_backtest(prices: Sequence[float]) -> dict:
    """对价格序列跑一遍回测，返回汇总指标；相同序列命中结果缓存。"""
    return dict(_backtest_core(tuple(prices)))


def cache_info() -> dict:
    """返回结果缓存命中统计（hits/misses/maxsize/currsize）。"""
    info = _backtest_core.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "maxsize": info.maxsize,
        "currsize": info.currsize,
    }
