"""test_backtest.py —— 回测模块单元测试（基线 3 项 + 方案 A 新增项）。"""

import random

from backtest import cache_info, run_backtest


def _reference_backtest(prices):
    """循环参考实现（与改造前基线逐行一致），用于向量化等价性验证。"""
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


def test_matches_loop_reference_on_random_walks():
    rng = random.Random(42)
    for _ in range(50):
        prices = []
        x = 100.0
        for _ in range(rng.randrange(0, 200)):
            x = max(0.01, x * rng.uniform(0.95, 1.05))
            prices.append(x)
        expected = _reference_backtest(prices)
        actual = run_backtest(prices)
        assert actual["trades"] == expected["trades"]
        assert abs(actual["final_value"] - expected["final_value"]) <= 1e-6


def test_cache_reuses_result_and_resists_mutation():
    first = run_backtest([1.0, 2.0, 3.0])
    before = cache_info()["hits"]
    second = run_backtest([1.0, 2.0, 3.0])
    assert cache_info()["hits"] == before + 1
    assert second == first
    second["trades"] = 999
    assert run_backtest([1.0, 2.0, 3.0])["trades"] == 2


def test_list_and_tuple_share_cache_entry():
    baseline = run_backtest([5.0, 6.0, 5.0])
    before = cache_info()["hits"]
    from_tuple = run_backtest((5.0, 6.0, 5.0))
    assert cache_info()["hits"] == before + 1
    assert from_tuple == baseline


def test_all_falling_prices_no_trades():
    result = run_backtest([5.0, 4.0, 3.0, 2.0])
    assert result == {"final_value": 10000.0, "trades": 0}


def test_all_rising_prices_hold_to_end():
    result = run_backtest([1.0, 2.0, 3.0, 4.0])
    assert result["trades"] == 3
    assert abs(result["final_value"] - 10003.0) < 1e-9


def test_equal_price_day_triggers_liquidation():
    prices = [1.0, 2.0, 2.0, 1.0]
    result = run_backtest(prices)
    assert result == _reference_backtest(prices)
    assert result["trades"] == 0


def test_cliff_drop_liquidates_at_crash_price():
    prices = [1.0, 2.0, 3.0, 0.5]
    result = run_backtest(prices)
    assert result == _reference_backtest(prices)
    assert abs(result["final_value"] - 9996.0) < 1e-9


def test_matches_loop_reference_on_plateaus_and_cliffs():
    rng = random.Random(99)
    for _ in range(50):
        prices = [
            rng.choice([1.0, 1.5, 2.0, 2.5])
            for _ in range(rng.randrange(0, 60))
        ]
        expected = _reference_backtest(prices)
        actual = run_backtest(prices)
        assert actual["trades"] == expected["trades"]
        assert abs(actual["final_value"] - expected["final_value"]) <= 1e-9


def test_long_sequence_matches_reference_within_tolerance():
    rng = random.Random(7)
    prices = []
    x = 50.0
    for _ in range(5000):
        x = max(0.01, x * rng.uniform(0.98, 1.02))
        prices.append(x)
    expected = _reference_backtest(prices)
    actual = run_backtest(prices)
    assert actual["trades"] == expected["trades"]
    assert abs(actual["final_value"] - expected["final_value"]) <= 1e-6
