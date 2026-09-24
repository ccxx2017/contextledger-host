"""test_backtest.py —— 回测模块单元测试（3 项基线 + 方案 A 回归资产）。"""

import random

from backtest import run_backtest


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


def test_empty_prices():
    assert run_backtest([]) == {"final_value": 10000.0, "trades": 0}


def test_single_price():
    assert run_backtest([10.0])["final_value"] == 10000.0


def test_rising_prices():
    result = run_backtest([1.0, 2.0, 3.0])
    assert result["trades"] == 2


def test_plateau_prices():
    assert run_backtest([5.0] * 10) == {"final_value": 10000.0, "trades": 0}


def test_all_falling_prices():
    assert run_backtest([5.0, 4.0, 3.0]) == {"final_value": 10000.0, "trades": 0}


def test_nan_breaks_rising_run():
    assert run_backtest([1.0, float("nan"), 2.0]) == {"final_value": 10000.0, "trades": 0}


def test_differential_against_reference():
    rng = random.Random(42)
    cases = [
        [],
        [10.0],
        [1.0, 2.0, 3.0],
        [5.0] * 10,
        list(range(100, 0, -1)),
        [1.0, 1.0, 2.0, 2.0, 1.0, 3.0, 3.0],
    ]
    for _ in range(500):
        n = rng.randrange(0, 60)
        cases.append([rng.choice([1.0, 1.5, 2.0, 2.5]) for _ in range(n)])
    for _ in range(500):
        n = rng.randrange(0, 500)
        cases.append([round(rng.uniform(0, 100), 2) for _ in range(n)])
    for prices in cases:
        expected = _reference_backtest(prices)
        actual = run_backtest(prices)
        assert actual["trades"] == expected["trades"], prices
        assert abs(actual["final_value"] - expected["final_value"]) < 1e-6, prices


def test_result_cached_for_identical_sequence():
    prices = [1.0, 2.0, 3.0, 2.0, 4.0]
    assert run_backtest(prices) is run_backtest(prices)
    assert run_backtest(tuple(prices)) is run_backtest(prices)
