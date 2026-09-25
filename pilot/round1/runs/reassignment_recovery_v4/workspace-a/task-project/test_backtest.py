"""test_backtest.py —— 回测模块单元测试（3 项基线 + 方案 A 补强用例）。"""

from backtest import _backtest_impl, run_backtest


def test_empty_prices():
    assert run_backtest([]) == {"final_value": 10000.0, "trades": 0}


def test_single_price():
    assert run_backtest([10.0])["final_value"] == 10000.0


def test_rising_prices():
    result = run_backtest([1.0, 2.0, 3.0])
    assert result["trades"] == 2


def test_cache_hit_on_repeat_calls():
    run_backtest([1.0, 2.0, 1.0])
    hits = _backtest_impl.cache_info().hits
    run_backtest([1.0, 2.0, 1.0])
    assert _backtest_impl.cache_info().hits == hits + 1


def test_list_and_tuple_inputs_equivalent():
    assert run_backtest([3.0, 1.0, 4.0]) == run_backtest((3.0, 1.0, 4.0))


def test_returned_dict_not_shared():
    first = run_backtest([2.0, 3.0, 2.0])
    second = run_backtest([2.0, 3.0, 2.0])
    assert first == second and first is not second
    first["final_value"] = -1.0
    assert run_backtest([2.0, 3.0, 2.0]) == second


def test_long_mixed_sequence():
    prices = [10.0, 11.0, 10.5, 10.0, 9.5, 10.0, 12.0, 11.0, 12.5]
    assert run_backtest(prices) == {"final_value": 9999.5, "trades": 1}
