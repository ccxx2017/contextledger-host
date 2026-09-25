"""test_backtest.py —— 回测模块单元测试（基线 3 项 + 方案 A 等价性/缓存/边界项）。"""

import math
import random
import threading

import numpy as np

from backtest import run_backtest


def _reference_backtest(prices):
    """改造前的基线循环实现，作为重构等价性参照。"""
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


def test_empty_prices():
    assert run_backtest([]) == {"final_value": 10000.0, "trades": 0}


def test_single_price():
    assert run_backtest([10.0])["final_value"] == 10000.0


def test_rising_prices():
    result = run_backtest([1.0, 2.0, 3.0])
    assert result["trades"] == 2


def test_flat_prices_no_trades():
    assert run_backtest([5.0, 5.0, 5.0]) == {"final_value": 10000.0, "trades": 0}


def test_falling_prices_no_trades():
    assert run_backtest([5.0, 4.0, 3.0]) == {"final_value": 10000.0, "trades": 0}


def test_matches_baseline_reference():
    rng = random.Random(42)
    for _ in range(200):
        length = rng.randint(0, 60)
        prices = [float(rng.randint(1, 50)) for _ in range(length)]
        assert run_backtest(prices) == _reference_backtest(prices)


def test_cache_hit_returns_same_result_and_fresh_dict():
    prices = [1.0, 2.0, 3.0, 2.0, 3.0]
    first = run_backtest(prices)
    second = run_backtest(prices)
    assert first == second
    first["trades"] = 999
    assert run_backtest(prices)["trades"] != 999


def _assert_same_as_reference(prices):
    result = run_backtest(prices)
    reference = _reference_backtest(prices)
    assert result["trades"] == reference["trades"]
    final, ref_final = result["final_value"], reference["final_value"]
    if math.isnan(final) or math.isnan(ref_final):
        assert math.isnan(final) and math.isnan(ref_final)
    else:
        assert final == ref_final


def test_nan_and_inf_match_baseline_reference():
    _assert_same_as_reference([1.0, float("nan"), 3.0, float("inf"), 2.0, float("nan"), 4.0])
    _assert_same_as_reference([1.0, 2.0, float("nan")])
    _assert_same_as_reference([float("inf"), float("inf"), float("inf")])


def test_numpy_array_input():
    arr = np.array([1.0, 2.0, 3.0, 2.0])
    assert run_backtest(arr) == run_backtest([1.0, 2.0, 3.0, 2.0])
    assert run_backtest(np.array([])) == {"final_value": 10000.0, "trades": 0}


def test_threaded_calls_consistent():
    prices = [1.0, 3.0, 2.0, 5.0, 4.0]
    expected = run_backtest(prices)
    results = []

    def worker():
        results.append(run_backtest(prices))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(r == expected for r in results)


def test_generator_input():
    gen = (x for x in [1.0, 2.0, 3.0, 2.0])
    assert run_backtest(gen) == run_backtest([1.0, 2.0, 3.0, 2.0])


def test_int_prices_match_baseline_reference():
    _assert_same_as_reference([1, 2, 3, 2, 3])


def test_cache_eviction_and_oversize_key(monkeypatch):
    import backtest

    monkeypatch.setattr(backtest, "_CACHE_MAX_BYTES", 100)
    backtest._cache.clear()
    backtest._cache_bytes = 0

    # 键超过单条预算：不入缓存，但结果必须正确
    big = [float(i % 7 + 1) for i in range(20)]
    assert run_backtest(big)["final_value"] == _reference_backtest(big)["final_value"]
    assert not backtest._cache

    # 预算 100 字节只装得下约 4 条 24 字节键，继续插入应触发 LRU 逐出
    seqs = [[1.0, 2.0, 1.0 + k] for k in range(6)]
    for s in seqs:
        run_backtest(s)
    assert len(backtest._cache) <= 4
    assert backtest._cache_bytes <= 100
    for s in seqs:
        assert run_backtest(s) == _reference_backtest(s)
