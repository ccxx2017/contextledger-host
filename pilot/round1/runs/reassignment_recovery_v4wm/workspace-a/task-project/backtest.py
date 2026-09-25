"""backtest.py —— 回测模块（方案 A 重构后：向量化 + 结果缓存）。

策略语义与基线实现保持一致：
- 逐日观察价格，若当日价格高于前一日则买入 1 份；
- 否则若持有仓位则全部卖出；
- 收盘时剩余持仓按最后价格估值。

重构点：
1. 向量化：用 numpy 布尔掩码一次性提取所有买入价，
   再按"连续上涨段"批量计算卖出收益，替代逐日 Python 循环；
2. 结果缓存：相同价格序列的重复调用命中 lru_cache，
   键为不可变的价格元组，返回值每次重建为新 dict，避免缓存被调用方污染。

输入约定：
- prices 为任意数值序列（int/float 均可）；
- 非有限值沿用基线语义：NaN 参与比较恒为 False，即被视作"非上涨日"
  （会触发清仓），且 NaN 会传播进 final_value。调用方应自行保证数据清洁，
  模块不做显式拒绝，以保持与基线契约一致。
"""

from functools import lru_cache
from typing import Sequence

import numpy as np

_CACHE_SIZE = 256


@lru_cache(maxsize=_CACHE_SIZE)
def _run_backtest_cached(prices: tuple) -> tuple:
    """对不可变的价格元组做向量化回测，返回 (final_value, open_position)。

    float 求和顺序与基线逐日累加存在最后一位舍入差异，
    以单元测试中的参照实现等价性校验为准。
    """
    p = np.asarray(prices, dtype=float)
    n = p.size
    if n == 0:
        return 10000.0, 0

    cash = 10000.0

    # 买入：所有上涨日各买 1 份，买价即当日收盘价。
    rising = p[1:] > p[:-1]
    cash -= float(p[1:][rising].sum())

    # 卖出：每个极大连续上涨段（坐标 s..e，段长 L）在段后首个
    # 非上涨日（价格下标 e+2）一次性清仓 L 份；若上涨段一直延伸
    # 到序列末尾则不触发卖出，剩余持仓按最后价格估值。
    steps = np.flatnonzero(rising)
    position = 0
    if steps.size:
        breaks = np.flatnonzero(np.diff(steps) > 1)
        starts = np.concatenate(([0], breaks + 1))
        ends = np.concatenate((breaks, [steps.size - 1]))
        run_lens = ends - starts + 1
        run_end_coords = steps[ends]
        sell_coords = run_end_coords + 1  # 卖出日在 rising 数组中的坐标
        sellable = sell_coords <= n - 2
        if sellable.any():
            proceeds = p[sell_coords[sellable] + 1] * run_lens[sellable]
            cash += float(proceeds.sum())
        position = int(run_lens[~sellable].sum())

    final = cash + position * float(p[-1])
    return final, position


def run_backtest(prices: Sequence[float]) -> dict:
    """对价格序列跑一遍简单回测，返回汇总指标（结果缓存见模块 docstring）。"""
    final, position = _run_backtest_cached(tuple(prices))
    return {"final_value": final, "trades": position}
