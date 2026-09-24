"""backtest.py —— 回测模块（方案 A：向量化 + 结果缓存）。

重构后实现：
- 向量化：numpy 按"连续上涨段"批量计算买入成本与清仓收益，去除逐 bar Python 循环；
- 缓存：相同价格序列（按 tuple 归一化）的重复回测命中 lru_cache；
- 语义与基线完全一致：连续上涨步逐 bar 买入 1 单位（按当根价成交），
  任一非上涨步且持仓 > 0 时全仓清仓，期末持仓按最后一根价估值。
"""

from functools import lru_cache
from typing import Sequence, Tuple

import numpy as np

_INITIAL_CASH = 10000.0
_CACHE_MAXSIZE = 256


@lru_cache(maxsize=_CACHE_MAXSIZE)
def _run_backtest_cached(prices: Tuple[float, ...]) -> Tuple[float, int]:
    p = np.asarray(prices, dtype=float)
    n = p.size
    if n == 0:
        return _INITIAL_CASH, 0

    # up[j] 为 True 表示第 j+1 根 bar 相对前一根上涨，即在 bar j+1 买入 1 单位
    up = np.diff(p) > 0
    buys = np.flatnonzero(up)
    if buys.size == 0:
        return _INITIAL_CASH, 0

    # 将买入 bar 按"连续上涨段"分段，段内成本/期末清仓收益可整段计算
    boundaries = np.concatenate(([True], np.diff(buys) != 1))
    starts = buys[boundaries]
    ends = buys[np.concatenate((boundaries[1:], [True]))]

    cost = float(p[buys + 1].sum())
    open_runs = ends < n - 2
    liquidation_bars = ends[open_runs] + 2
    revenue = float(
        (p[liquidation_bars] * (ends[open_runs] - starts[open_runs] + 1)).sum()
    )
    held_units = int((ends - starts + 1)[ends == n - 2].sum())

    final = _INITIAL_CASH - cost + revenue + held_units * float(p[-1])
    return final, held_units


def run_backtest(prices: Sequence[float]) -> dict:
    """对价格序列跑一遍回测，返回汇总指标（结果与改造前基线一致）。"""
    final, trades = _run_backtest_cached(tuple(prices))
    return {"final_value": final, "trades": trades}
