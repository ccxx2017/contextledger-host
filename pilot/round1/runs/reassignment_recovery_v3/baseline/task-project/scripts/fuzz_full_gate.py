"""fuzz_full_gate.py —— 方案 A 全量等价性 fuzz Gate（一键复跑）。

用法：python scripts/fuzz_full_gate.py   （退出码 0=通过，1=存在不匹配）

协议（与 v1 验证及恢复 Gate 一致）：
- 2808 用例：固定边角（空/单点/上涨/下跌/平台）+ 随机生成（随机游走、
  整型序列、平台行情、单边行情，n∈{2..1000}），固定种子 20260924；
- 判据：trades 与基线完全一致；final_value 相对误差 ≤ 1e-9；
- 基线实现 `_baseline_backtest` 为语义契约（与 test_backtest.py 中一致）。

Gate 记录：
- 2026-09-24（恢复当日）：2808 用例，0 不匹配 —— PASS
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backtest import run_backtest

SEED = 20260924
N_CASES = 2808
REL_TOL = 1e-9


def _baseline_backtest(prices):
    """改造前基线实现，作为语义契约的参照。"""
    cash, pos = 10000.0, 0
    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            pos += 1
            cash -= prices[i]
        elif pos > 0:
            cash += prices[i] * pos
            pos = 0
    final = cash + pos * (prices[-1] if prices else 0.0)
    return final, pos


def build_cases(rng):
    cases = [[], [10.0], [1.0, 2.0, 3.0], [3.0, 2.0, 1.0], [2.0, 2.0, 2.0], [5.0, 4.9]]
    while len(cases) < N_CASES:
        n = int(rng.integers(2, 1001))
        kind = int(rng.integers(0, 4))
        if kind == 0:
            cases.append((100.0 + np.cumsum(rng.standard_normal(n))).tolist())
        elif kind == 1:
            cases.append(rng.integers(1, 20, n).tolist())
        elif kind == 2:
            cases.append(np.full(n, float(rng.integers(1, 50))).tolist())
        else:
            step = float(rng.uniform(0.5, 2.0))
            seq = rng.uniform(1.0, 100.0) + step * np.arange(n)
            if int(rng.integers(0, 2)):
                seq = seq[::-1]
            cases.append(seq.tolist())
    return cases


def main():
    mismatch = 0
    for prices in build_cases(np.random.default_rng(SEED)):
        exp_final, exp_trades = _baseline_backtest(prices)
        res = run_backtest(prices)
        if res["trades"] != exp_trades or abs(
            res["final_value"] - exp_final
        ) > REL_TOL * max(1.0, abs(exp_final)):
            mismatch += 1
            if mismatch <= 3:
                print("MISMATCH:", prices[:12])
    print(f"cases={N_CASES} mismatch={mismatch}")
    return 1 if mismatch else 0


if __name__ == "__main__":
    sys.exit(main())
