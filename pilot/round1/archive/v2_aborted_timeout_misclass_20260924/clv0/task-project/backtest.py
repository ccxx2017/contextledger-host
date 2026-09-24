"""backtest.py —— 回测模块（方案 A：向量化 + 结果缓存）。

公共 API 与改造前基线完全一致：
    run_backtest(prices) -> {"final_value": float, "trades": int}

策略语义（与基线逐日循环严格等价）：
    - 当日价格高于前一日则买入 1 份；
    - 否则若持仓 > 0 则一次性全部卖出；
    - 期末剩余持仓按最后一天价格估值。

改造内容：
    1. 向量化：逐日循环改为 numpy 数组运算（涨跌判断、连续上涨段计数、
       买卖现金流一次性计算），基线循环保留为 _backtest_loop 参照实现，
       供等价性验证使用；
    2. 结果缓存：相同价格序列的重复调用命中 lru_cache（以 tuple 为键），
       返回字典副本，调用方修改结果不会污染缓存。
"""

from functools import lru_cache
from typing import Sequence

import numpy as np

_INITIAL_CASH = 10000.0
_CACHE_SIZE = 256


def _backtest_loop(prices: Sequence[float]) -> dict:
    """基线参照实现（改造前逐日循环），仅用于等价性验证。"""
    cash = _INITIAL_CASH
    position = 0
    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            position += 1
            cash -= prices[i]
        elif position > 0:
            cash += prices[i] * position
            position = 0
    final = cash + position * (prices[-1] if prices else 0.0)
    return {"final_value": final, "trades": position}


def _backtest_vectorized(prices: tuple) -> dict:
    arr = np.asarray(prices, dtype=np.float64)
    if arr.size < 2:
        return {"final_value": _INITIAL_CASH, "trades": 0}

    up = arr[1:] > arr[:-1]
    if not up.any():
        return {"final_value": _INITIAL_CASH, "trades": 0}

    starts_mask = up.copy()
    starts_mask[1:] &= ~up[:-1]
    starts = np.flatnonzero(starts_mask)
    ends_mask = up.copy()
    ends_mask[:-1] &= ~up[1:]
    ends = np.flatnonzero(ends_mask)
    run_len = ends - starts + 1
    held = ends == up.size - 1

    buys = np.dot(arr[1:], up)
    sells = np.dot(arr[ends[~held] + 2], run_len[~held])
    position = int(run_len[-1]) if held[-1] else 0

    cash = _INITIAL_CASH - float(buys) + float(sells)
    return {"final_value": cash + position * float(arr[-1]), "trades": position}


@lru_cache(maxsize=_CACHE_SIZE)
def _backtest_cached(prices: tuple) -> dict:
    return _backtest_vectorized(prices)


def run_backtest(prices: Sequence[float]) -> dict:
    """对价格序列跑一遍回测，返回汇总指标（相同输入直接命中缓存）。"""
    return dict(_backtest_cached(tuple(prices)))
