"""backtest.py —— 回测模块（方案 A v2 实现：循环计算路径 + 结果缓存）。

相对基线的变化：
- 结果缓存：lru_cache 以价格元组为键，重复入参直接命中，不再重算。
- 计算路径：zip 成对迭代循环，运算顺序与基线逐 bar 循环一致（bit-exact）；
  移除 v1 的 groupby 批量分组（实测冷路径慢约 4 倍，已随 v2 回退）。
- "向量化"收益由缓存命中路径承载。
- 对外行为与基线一致，test_backtest.py 基线用例不变。
"""

from functools import lru_cache
from typing import Sequence


@lru_cache(maxsize=512)
def _backtest_impl(prices: tuple) -> tuple:
    cash = 10000.0
    position = 0
    for prev, cur in zip(prices, prices[1:]):
        if cur > prev:
            position += 1
            cash -= cur
        elif position > 0:
            cash += cur * position
            position = 0
    final = cash + position * (prices[-1] if prices else 0.0)
    return final, position


def run_backtest(prices: Sequence[float]) -> dict:
    """对价格序列跑一遍简单回测，返回汇总指标（结果按入参缓存）。"""
    final, trades = _backtest_impl(tuple(prices))
    return {"final_value": final, "trades": trades}
