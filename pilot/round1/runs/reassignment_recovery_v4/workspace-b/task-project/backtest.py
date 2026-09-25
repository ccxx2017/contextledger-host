"""backtest.py —— 回测模块（方案 A 重构后：向量化 + 结果缓存）。

对外 API 与基线完全一致：
    run_backtest(prices) -> {"final_value": float, "trades": int}
其中 trades 为期末剩余持仓数（沿用基线语义，本次重构不做"修复"）。
改造要点与基准数据见 notes.md。
"""

from array import array
from collections import OrderedDict
from typing import Sequence

import numpy as np

_INITIAL_CASH = 10000.0

# 结果缓存：bytes 键 + 按键总字节数限额的 LRU。
# 不用 lru_cache(tuple)：长序列下 tuple 的构造/哈希/逐元素比较是主要开销，
# 且 lru_cache 只能按条数限额，无法约束内存。
_CACHE_MAX_BYTES = 64 * 1024 * 1024
_cache: "OrderedDict[bytes, tuple]" = OrderedDict()
_cache_bytes = 0


def run_backtest(prices: Sequence[float]) -> dict:
    """对价格序列跑一遍简单回测，返回汇总指标（相同输入直接命中缓存）。"""
    global _cache_bytes
    if isinstance(prices, np.ndarray):
        arr = np.asarray(prices, dtype=np.float64)
    else:
        # array('d') 的 C 级转换比 np.asarray(list) 快约一半，且生成器也能安全消费
        arr = np.frombuffer(array("d", prices), dtype=np.float64)
    key = arr.tobytes()
    result = _cache.get(key)
    if result is None:
        result = _run_vectorized(arr)
        if len(key) <= _CACHE_MAX_BYTES:
            _cache[key] = result
            _cache_bytes += len(key)
            while _cache_bytes > _CACHE_MAX_BYTES:
                oldest_key, _ = _cache.popitem(last=False)
                _cache_bytes -= len(oldest_key)
    return {"final_value": result[0], "trades": result[1]}


def _run_vectorized(p: np.ndarray) -> tuple:
    """向量化回测核心，返回 (final_value, trades)。

    策略的向量化等价刻画：连续上涨段内逐日各买入 1 份；某段被其后首个
    非上涨日终止时当日全部清仓；延伸到序列末尾的段留到期末、按最后价计值。
    现金流按时间顺序与初始资金一起做 np.cumsum（顺序累加），与基线循环的
    浮点运算顺序逐位一致，因此结果与改造前完全相同，而非仅近似相等。
    """
    n = p.size
    if n < 2:
        return _INITIAL_CASH + 0 * (p[-1] if n else 0.0), 0

    up = p[1:] > p[:-1]
    m = up.size

    padded = np.concatenate(([False], up, [False]))
    starts = np.flatnonzero(padded[1:] & ~padded[:-1])
    ends = np.flatnonzero(padded[:-1] & ~padded[1:]) - 1
    sizes = ends - starts + 1

    flows = np.zeros(n)
    buy_idx = np.flatnonzero(up) + 1
    flows[buy_idx] -= p[buy_idx]

    terminated = ends < m - 1
    sell_idx = ends[terminated] + 2
    flows[sell_idx] += p[sell_idx] * sizes[terminated]

    # 首日必无交易（买入自 idx>=1、清仓自 idx>=2），可借用 flows[0] 放初始资金，
    # 原地 cumsum 省去一次长度 n 的拼接拷贝，浮点运算顺序与前置初始资金完全一致
    flows[0] = _INITIAL_CASH
    np.cumsum(flows, out=flows)
    cash = float(flows[-1])
    leftover = int(sizes[~terminated].sum())
    return cash + leftover * float(p[-1]), leftover
