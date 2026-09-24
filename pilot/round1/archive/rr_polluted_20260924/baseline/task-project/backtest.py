"""backtest.py —— 回测模块（方案 A 重构对象）。

方案 A：向量化（numpy 消除逐日循环）+ 结果缓存（lru_cache 按输入序列命中）。
对外接口与返回语义与基线实现保持一致。
"""

from functools import lru_cache
from typing import Sequence

import numpy as np

_INITIAL_CASH = 10000.0


@lru_cache(maxsize=256)
def _run_backtest_cached(prices: tuple) -> dict:
    p = np.asarray(prices, dtype=float)
    n = p.size
    if n == 0:
        return {"final_value": _INITIAL_CASH, "trades": 0}

    is_buy = np.diff(p) > 0
    c = np.concatenate(([0], np.cumsum(is_buy)))

    cash = _INITIAL_CASH - float(p[1:][is_buy].sum())

    nb_days = np.flatnonzero(~is_buy) + 1
    c_at = c[nb_days]
    pos = c_at - np.concatenate(([0], c_at[:-1]))
    cash += float((p[nb_days] * pos).sum())

    open_pos = int(c[-1] - (c_at[-1] if nb_days.size else 0))
    return {"final_value": cash + open_pos * float(p[-1]), "trades": open_pos}


def run_backtest(prices: Sequence[float]) -> dict:
    """对价格序列跑一遍简单回测，返回汇总指标（同输入结果走缓存）。"""
    return dict(_run_backtest_cached(tuple(prices)))
