"""test_backtest.py —— 回测模块单元测试（含确定性 fuzz 等价性回归）。"""

import numpy as np

from backtest import run_backtest


def test_empty_prices():
    assert run_backtest([]) == {"final_value": 10000.0, "trades": 0}


def test_single_price():
    assert run_backtest([10.0])["final_value"] == 10000.0


def test_rising_prices():
    result = run_backtest([1.0, 2.0, 3.0])
    assert result["trades"] == 2


def test_liquidation_on_dip():
    assert run_backtest([3.0, 2.0, 1.0, 2.0, 1.0]) == {
        "final_value": 9999.0,
        "trades": 0,
    }


def test_repeated_calls_cached():
    prices = [1.0, 2.0, 1.5, 2.5]
    first = run_backtest(prices)
    assert run_backtest(tuple(prices)) == first


def _baseline_backtest(prices):
    """改造前基线实现，作为语义契约的参照。"""
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


def test_fuzz_equivalence_with_baseline():
    rng = np.random.default_rng(42)
    cases = [[], [10.0], [1.0, 2.0, 3.0], [3.0, 2.0, 1.0], [2.0, 2.0, 2.0]]
    for _ in range(300):
        n = int(rng.integers(2, 200))
        cases.append((100.0 + np.cumsum(rng.standard_normal(n))).tolist())
        cases.append(rng.integers(1, 20, n).tolist())

    for prices in cases:
        expected = _baseline_backtest(prices)
        result = run_backtest(prices)
        assert result["trades"] == expected["trades"], prices[:12]
        assert (
            abs(result["final_value"] - expected["final_value"])
            <= 1e-9 * max(1.0, abs(expected["final_value"]))
        ), prices[:12]
