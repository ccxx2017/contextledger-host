"""test_backtest.py —— 回测模块单元测试（基线 3 项 + 方案 A 加固用例）。"""

import random

import pytest

from backtest import _run_backtest_cached, run_backtest


def _reference(prices):
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


def test_mixed_prices():
    assert run_backtest([5.0, 6.0, 4.0, 7.0, 8.0, 8.0, 1.0]) == {
        "final_value": 9999.0,
        "trades": 0,
    }


def test_falling_prices():
    assert run_backtest([3.0, 2.0, 1.0]) == {"final_value": 10000.0, "trades": 0}


def test_flat_prices():
    assert run_backtest([5.0, 5.0, 5.0]) == {"final_value": 10000.0, "trades": 0}


def test_tie_then_rise():
    assert run_backtest([1.0, 2.0, 2.0, 3.0]) == {"final_value": 10000.0, "trades": 1}


def test_sequence_types_consistent():
    assert run_backtest((1.0, 2.0, 3.0)) == run_backtest([1.0, 2.0, 3.0])


def test_equivalence_with_reference():
    random.seed(7)
    cases = [[], [10.0], [1.0, 2.0, 3.0]]
    for _ in range(200):
        cases.append(
            [round(random.uniform(1, 100), 2) for _ in range(random.randint(0, 50))]
        )
    for prices in cases:
        expected = _reference(prices)
        actual = run_backtest(prices)
        assert actual["trades"] == expected["trades"]
        assert actual["final_value"] == pytest.approx(
            expected["final_value"], rel=1e-12, abs=1e-9
        )


def test_cache_hit_on_repeat():
    _run_backtest_cached.cache_clear()
    run_backtest([1.5, 2.5, 3.5])
    run_backtest([1.5, 2.5, 3.5])
    assert _run_backtest_cached.cache_info().hits >= 1


def test_result_copy_isolated():
    first = run_backtest([1.0, 2.0])
    first["final_value"] = -1.0
    second = run_backtest([1.0, 2.0])
    assert second["final_value"] == pytest.approx(10000.0)
