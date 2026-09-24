"""benchmark_backtest.py —— 方案 A 性能验收基准。

对比三项：原循环基线、向量化（每次清缓存后冷算）、向量化+缓存命中。
"""

import timeit

from backtest import _run_backtest_cached, run_backtest


def _reference_backtest(prices):
    cash = 10000.0
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


def _cold_run(prices):
    _run_backtest_cached.cache_clear()
    return run_backtest(prices)


def main():
    prices = [float((i * 37) % 101) for i in range(10000)]
    rounds = 100
    run_backtest(prices)
    t_loop = timeit.timeit(lambda: _reference_backtest(prices), number=rounds)
    t_cold = timeit.timeit(lambda: _cold_run(prices), number=rounds)
    t_warm = timeit.timeit(lambda: run_backtest(prices), number=rounds)
    print(f"n=10000 x{rounds}:  loop={t_loop * 10:.1f}ms  vectorized(cold)={t_cold * 10:.1f}ms  cached(warm)={t_warm * 10:.1f}ms")


if __name__ == "__main__":
    main()
