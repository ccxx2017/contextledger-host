"""backtest.py —— 回测模块（方案 A 重构版）。

方案 A 范围：
1. 向量化：用 NumPy 消除逐 bar Python 循环（上涨日买入 1 手、其余日清仓）；
2. 结果缓存：相同价格序列的重复回测直接命中缓存。

输出口径与改造前基线完全一致，包括历史约定：`trades` 返回期末持仓量
（若收盘前已清仓则为 0），并非成交次数。
"""

from functools import lru_cache
from typing import Sequence, Tuple

import numpy as np

_INITIAL_CASH = 10000.0
_CACHE_SIZE = 4096


def _backtest_impl(prices) -> dict:
    if isinstance(prices, np.ndarray):
        arr = prices.astype(float, copy=False)
    else:
        arr = np.fromiter(prices, dtype=float, count=len(prices))
    n = arr.size
    if n <= 1:
        last = float(arr[-1]) if n == 1 else 0.0
        return {"final_value": _INITIAL_CASH + 0.0 * last, "trades": 0}

    diff = np.diff(arr)
    is_buy = diff > 0
    day = np.arange(1, n)

    buy_pos = np.flatnonzero(is_buy)
    if buy_pos.size == 0:
        return {"final_value": _INITIAL_CASH + 0.0 * float(arr[-1]), "trades": 0}

    breaks = np.flatnonzero(np.diff(buy_pos) > 1)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks, [buy_pos.size - 1]))
    last_day = day[buy_pos[ends]]
    run_len = ends - starts + 1

    buy_cost = float(np.where(is_buy, arr[1:], 0.0).sum())

    closed = np.zeros(run_len.size, dtype=bool)
    nonbuy_days = day[~is_buy]
    if nonbuy_days.size:
        ins = np.searchsorted(nonbuy_days, last_day, side="right")
        closed = ins < nonbuy_days.size
        sell_day = nonbuy_days[np.minimum(ins, nonbuy_days.size - 1)]
        proceeds = float(np.where(closed, arr[sell_day] * run_len, 0.0).sum())
    else:
        proceeds = 0.0

    open_pos = 0 if closed[-1] else int(run_len[-1])
    final = _INITIAL_CASH - buy_cost + proceeds + open_pos * float(arr[-1])
    return {"final_value": float(final), "trades": open_pos}


@lru_cache(maxsize=_CACHE_SIZE)
def _backtest_cached(prices: Tuple[float, ...]) -> dict:
    return _backtest_impl(prices)


def run_backtest(prices: Sequence[float]) -> dict:
    """对价格序列跑一遍回测，返回汇总指标（相同输入命中缓存）。"""
    return dict(_backtest_cached(tuple(prices)))
