"""test_backtest.py —— 回测模块单元测试。

前 3 项为改造前基线测试（须保持通过）；
其余为方案 A 重构新增：向量化结果与参照循环实现等价、边界行为、缓存行为。
"""

import random

import pytest

from backtest import run_backtest


def _reference_backtest(prices):
    """基线逐日循环实现，作为向量化的参照。"""
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


def test_equivalence_with_reference():
    cases = [
        [3.0, 2.0, 1.0],
        [1.0, 3.0, 2.0, 4.0, 5.0, 3.0],
        [1.0, 1.0, 1.0],
        [2.0, 2.0, 3.0, 3.0, 1.0],
        [1.0, 2.0],
        [2.0, 1.0],
        [5.0, 4.0, 5.0, 6.0, 7.0, 6.0, 7.0, 8.0, 9.0],
    ]
    rng = random.Random(42)
    cases += [[rng.uniform(1.0, 100.0) for _ in range(rng.randint(1, 300))]
              for _ in range(200)]
    for prices in cases:
        result = run_backtest(prices)
        expected = _reference_backtest(prices)
        # 向量化批量求和与逐日累加存在最后一位舍入差异，用紧容差校验。
        assert result["final_value"] == pytest.approx(
            expected["final_value"], rel=1e-12, abs=1e-9
        ), prices
        assert result["trades"] == expected["trades"], prices


def test_trailing_rising_run_valued_at_last_price():
    result = run_backtest([1.0, 2.0, 3.0])
    assert result["final_value"] == 9995.0 + 2 * 3.0
    assert result["trades"] == 2


def test_tuple_input_matches_list_input():
    assert run_backtest((1.0, 2.0, 3.0)) == run_backtest([1.0, 2.0, 3.0])


def test_cache_not_polluted_by_caller_mutation():
    prices = [1.0, 2.0, 3.0]
    first = run_backtest(prices)
    first["final_value"] = -1.0
    first["trades"] = 999
    second = run_backtest(prices)
    assert second == {"final_value": 9995.0 + 2 * 3.0, "trades": 2}


def test_non_finite_inputs_follow_reference():
    """NaN 视作非上涨日（触发清仓）且传播进 final_value；与参照实现一致。"""
    cases = [
        [1.0, float("nan"), 2.0, float("nan"), 3.0],
        [float("inf"), 1.0, float("inf"), 2.0],
        [1.0, 2.0, float("inf")],
        [float("nan")],
    ]
    for prices in cases:
        result = run_backtest(prices)
        expected = _reference_backtest(prices)
        assert result["final_value"] == pytest.approx(
            expected["final_value"], rel=1e-12, abs=1e-9, nan_ok=True
        ), prices
        assert result["trades"] == expected["trades"], prices


def test_int_prices_accepted():
    assert run_backtest([1, 2, 3]) == run_backtest([1.0, 2.0, 3.0])


def test_cache_hit_returns_identical_results():
    prices = [3.0, 1.0, 4.0, 1.0, 5.0]
    assert run_backtest(prices) == run_backtest(prices) == _reference_backtest(prices)
