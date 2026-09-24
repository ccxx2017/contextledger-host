"""backtest.py 方案 A 重构的验证测试。

test_empty_prices / test_rising_prices / test_single_price 为历史用例
（依据 .pytest_cache 记录恢复）；其余为重构等价性与缓存行为测试。
"""

import math
import random

import numpy as np
import pytest

from backtest import _backtest_cached, run_backtest


def _reference_loop(prices):
    """改造前基线实现，作为等价性验证的参照。"""
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
    assert run_backtest([5.0]) == {"final_value": 10000.0, "trades": 0}


def test_rising_prices():
    result = run_backtest([1.0, 2.0, 3.0])
    assert result["trades"] == 2
    assert result["final_value"] == pytest.approx(10001.0)


def test_falling_prices_flat():
    result = run_backtest([3.0, 2.0, 1.0])
    assert result == {"final_value": 10000.0, "trades": 0}


def test_matches_reference_random():
    rng = random.Random(42)
    for _ in range(500):
        length = rng.randrange(0, 60)
        prices = [rng.uniform(1.0, 100.0) for _ in range(length)]
        expected = _reference_loop(prices)
        actual = run_backtest(prices)
        assert actual["trades"] == expected["trades"], prices
        assert actual["final_value"] == pytest.approx(
            expected["final_value"], rel=1e-9, abs=1e-9
        ), prices


def test_matches_reference_random_ints():
    rng = random.Random(7)
    for _ in range(300):
        length = rng.randrange(0, 40)
        prices = [rng.randint(1, 50) for _ in range(length)]
        expected = _reference_loop(prices)
        actual = run_backtest(prices)
        assert actual["trades"] == expected["trades"], prices
        assert actual["final_value"] == pytest.approx(
            expected["final_value"], rel=1e-9, abs=1e-9
        ), prices


def test_cache_hit_on_same_input():
    prices = [3.0, 1.0, 4.0, 1.5, 5.0]
    _backtest_cached.cache_clear()
    first = run_backtest(prices)
    second = run_backtest(prices)
    assert first == second
    info = _backtest_cached.cache_info()
    assert info.hits >= 1 and info.misses == 1


def test_cache_result_is_defensive_copy():
    prices = [3.0, 1.0, 4.0]
    result = run_backtest(prices)
    result["final_value"] = -999.0
    result["trades"] = -999
    assert run_backtest(prices) == _reference_loop(prices)


# ---------- NaN 输入（接手核实补强） ----------


def test_nan_does_not_trigger_buy():
    assert run_backtest([1.0, float("nan"), 1.0]) == {
        "final_value": 10000.0,
        "trades": 0,
    }


def test_nan_propagates_when_position_opened():
    prices = [1.0, 2.0, 3.0, float("nan"), 4.0]
    expected = _reference_loop(prices)
    actual = run_backtest(prices)
    assert actual["trades"] == expected["trades"] == 0
    assert math.isnan(expected["final_value"])
    assert math.isnan(actual["final_value"])


def test_nan_propagates_after_flat_close():
    prices = [1.0, 2.0, 1.0, float("nan")]
    expected = _reference_loop(prices)
    actual = run_backtest(prices)
    assert actual["trades"] == expected["trades"] == 0
    assert math.isnan(expected["final_value"])
    assert math.isnan(actual["final_value"])


def test_nan_before_first_buy_does_not_pollute_cash():
    prices = [1.0, float("nan"), 1.0, 2.0]
    expected = _reference_loop(prices)
    actual = run_backtest(prices)
    assert actual["trades"] == expected["trades"] == 1
    assert actual["final_value"] == pytest.approx(
        expected["final_value"], rel=1e-9, abs=1e-9
    )


def test_random_nan_series_matches_reference():
    rng = random.Random(99)
    for _ in range(200):
        length = rng.randrange(0, 50)
        prices = [rng.uniform(1.0, 100.0) for _ in range(length)]
        for _ in range(rng.randrange(0, 4)):
            if prices:
                prices[rng.randrange(length)] = float("nan")
        expected = _reference_loop(prices)
        actual = run_backtest(prices)
        assert actual["trades"] == expected["trades"], prices
        if math.isnan(expected["final_value"]):
            assert math.isnan(actual["final_value"]), prices
        else:
            assert actual["final_value"] == pytest.approx(
                expected["final_value"], rel=1e-9, abs=1e-9
            ), prices


@pytest.mark.parametrize(
    "prices",
    [
        [float("nan")],
        [float("nan"), float("nan")],
        [5.0, float("nan")],
    ],
)
def test_zero_position_nan_terminal_matches_baseline(prices):
    expected = _reference_loop(prices)
    actual = run_backtest(prices)
    assert actual["trades"] == expected["trades"]
    assert math.isnan(expected["final_value"])
    assert math.isnan(actual["final_value"])


# ---------- ndarray 输入快路径 ----------


def test_ndarray_input_matches_reference():
    rng = random.Random(123)
    for _ in range(100):
        length = rng.randrange(0, 60)
        prices = [rng.uniform(1.0, 100.0) for _ in range(length)]
        expected = _reference_loop(prices)
        from_list = run_backtest(prices)
        from_ndarray = run_backtest(np.asarray(prices))
        assert from_ndarray["trades"] == expected["trades"]
        assert from_ndarray["final_value"] == pytest.approx(
            expected["final_value"], rel=1e-9, abs=1e-9
        )
        assert from_ndarray == from_list


def test_ndarray_dtypes():
    for arr in (
        np.array([1, 2, 3], dtype=np.int64),
        np.array([1, 2, 3], dtype=np.float32),
        np.array([1.0, 2.0, 3.0], dtype=np.float64),
    ):
        result = run_backtest(arr)
        assert result["trades"] == 2
        assert result["final_value"] == pytest.approx(10001.0)


def test_cache_key_shared_across_input_types():
    prices = [3.0, 1.0, 4.0, 1.5, 5.0]
    _backtest_cached.cache_clear()
    from_list = run_backtest(prices)
    from_ndarray = run_backtest(np.asarray(prices))
    assert from_list == from_ndarray
    info = _backtest_cached.cache_info()
    assert info.misses == 1
    assert info.hits >= 1
