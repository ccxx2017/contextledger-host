"""test_backtest.py —— 回测模块单元测试。

前 3 项为改造前基线测试；其余为方案 A 新增：向量化等价性、缓存命中、
结果快照隔离。
"""

import math
import random

from backtest import _backtest_cached, _backtest_loop, run_backtest


def test_empty_prices():
    assert run_backtest([]) == {"final_value": 10000.0, "trades": 0}


def test_single_price():
    assert run_backtest([10.0])["final_value"] == 10000.0


def test_rising_prices():
    result = run_backtest([1.0, 2.0, 3.0])
    assert result["trades"] == 2


def test_vectorized_matches_baseline_random():
    rng = random.Random(42)
    for _ in range(200):
        n = rng.randint(0, 60)
        prices = [round(rng.uniform(1.0, 100.0), 2) for _ in range(n)]
        base = _backtest_loop(prices)
        vec = run_backtest(prices)
        assert vec["trades"] == base["trades"]
        assert math.isclose(
            vec["final_value"], base["final_value"], rel_tol=1e-12, abs_tol=1e-9
        )


def test_cache_hit_on_repeat_call():
    prices = [3.0, 2.0, 2.5, 2.4, 2.8, 2.7, 3.1]
    _backtest_cached.cache_clear()
    run_backtest(prices)
    misses_after_first = _backtest_cached.cache_info().misses
    run_backtest(prices)
    info = _backtest_cached.cache_info()
    assert misses_after_first == 1
    assert info.hits >= 1


def test_result_snapshot_isolated_from_cache():
    prices = [1.0, 2.0, 3.0]
    result = run_backtest(prices)
    result["trades"] = 999
    assert run_backtest(prices) == {"final_value": 10001.0, "trades": 2}
