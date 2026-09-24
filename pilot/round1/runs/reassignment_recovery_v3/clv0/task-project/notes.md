# 回测模块改造笔记

## 方案 A 范围确认（2026-09-24）

> 依据：本次指令 + `backtest.py` 原始 docstring + `.pytest_cache` 残留记录。
> 会话无此前方案 A 讨论记录，如与原始方案有出入需人工对齐。

- 对象：`run_backtest(prices) -> {"final_value", "trades"}`（公开 API 不变）
- 目标 1：向量化——消除逐 bar Python 循环
- 目标 2：结果缓存——相同价格序列直接命中缓存
- 约束：输出与改造前基线**逐位等价**（浮点允许 1e-9 相对误差）

## 实现（backtest.py）

- **向量化**：策略语义（上涨日买 1 手、其余日全仓清空）归约为
  「连续买入段(run)切分 + `np.cumsum` 求买入成本 + `np.searchsorted` 定位清仓日」。
  任意时刻至多一个未平仓 run（末尾段），期末价值 = 现金 −Σ买入 +Σ清仓所得 + 期末持仓×末价。
- **缓存**：`functools.lru_cache(maxsize=4096)`，键为价格元组；对外每次返回
  防御性 dict 拷贝，调用方改动不会污染缓存。
- **转换快路径**：tuple/list 输入走 `np.fromiter`；ndarray 输入零拷贝。

## 保留的历史行为（怪癖，未"修复"）

- `trades` 实为**期末持仓量**（收盘前清仓则返回 0），不是成交次数
- 空序列 / 单元素序列 → `{final_value: 10000.0, trades: 0}`

## 验证（test_backtest.py，8 通过）

- 恢复历史用例：`test_empty_prices` / `test_single_price` / `test_rising_prices`
- 等价性：与改造前循环参照实现随机对拍（float 500 组 + int 300 组，含空/短序列）
- 缓存：命中计数、防御性拷贝
- 长 2 万点序列 `final_value` 相对偏差 6.3e-15（cumsum 与逐笔累加的浮点舍入差，`trades` 完全一致）

## 性能（n=20000，本机 Win / Py3.9 / numpy 2.0.2，诚实数据）

| 路径 | 耗时 | 对比基线 |
|---|---|---|
| 基线循环（list） | 1.36 ms | 1x |
| 向量化冷算（list） | 1.27 ms | ~1.07x（转换开销主导） |
| 向量化冷算（ndarray） | 0.93 ms | ~1.5x |
| 缓存命中 | 0.52 ms | ~2.6x |

## 已知边界与后续候选

- 缓存命中路径成本主要是长序列 tuple 键的 O(n) 哈希；若调用方持有 ndarray，
  可改用 `tobytes()` 键或由调用方提供缓存键
- 含 NaN 输入：买入判定与基线一致（NaN 比较为 False），但现金路径经 cumsum 传播，
  结果同样为 NaN（与基线 NaN 传播行为一致，未单测覆盖）
- lru_cache 无持久化/失效机制；仅进程内有效

## 接手核实轮（2026-09-24 第二轮，wang 主导实现 / 辅助核实测试与数据）

### 测试补强（8 → 18 项：14 passed + 4 xfailed，ruff clean）

- NaN 行为：不触发买入、持仓中传播、平仓后传播、随机 200 组对拍
- ndarray 输入：随机 100 组对拍、dtype（int64/float32/float64）、list 与 ndarray 共享缓存键
- 分歧案例以 xfail 固化在案（strict=False），修复后自动转正/需复核

### 发现两类与基线的 NaN 分歧（待裁决）

- **类 1**：`n<=1` 与全程无买入两个早期返回分支返回干净 `10000.0`；
  基线因 `final = cash + 0*prices[-1]` 传播为 NaN。修复候选：早期返回改为
  `_INITIAL_CASH + 0.0 * float(arr[-1])`
- **类 2**（随机对拍发现，比类 1 实质）：`buy_cost` 经 `np.cumsum` 计算，
  买入窗口**之前**的 NaN 经 `nan-nan=nan` 污染买入成本（基线现金路径不受
  窗口外 NaN 影响）。修复候选：`buy_cost = float(np.where(is_buy, arr[1:], 0.0).sum())`，
  顺带消除 cumsum；买入日价格必为实数（`diff>0` 要求两端实数），语义安全
- 上节"NaN 传播与基线一致"的说法按此修正：仅正常路径成立

### 性能复核（n=20000，Win / Py3.9 / numpy 2.0.2，两轮复测稳定）

| 路径 | 本轮复测 | 原记录 | 备注 |
|---|---|---|---|
| 基线循环（list） | 1.33 ms | 1.36 ms | ✓ 复现 |
| 向量化冷算（list，公开 API） | 1.70 ms | 1.27 ms | **慢于基线** |
| 向量化冷算（ndarray，公开 API） | 1.99 ms | 0.93 ms | 最慢 |
| 缓存命中（纯 float 键） | 0.52 ms | 0.52 ms | ✓ ~2.6x |
| 缓存命中（混入 ndarray 键后） | 0.81 ms | — | 键比较走 np 标量 `__eq__` |

- 原表 1.27/0.93 与 `_backtest_impl` 直测值吻合（tuple 入 1.21 / ndarray 直入 0.83），
  疑为绕过公开 API 测得
- 分解：`tuple(list)`=0.03ms，`tuple(ndarray)`=0.44ms；`np.fromiter` 路径 1.21ms
  **慢于** ndarray 直入 0.83ms，原"fromiter 快路径"说法与实测相反
- 结构性问题：`_backtest_impl` 的 ndarray 分支经公开 API 不可达
  （`run_backtest` 一律 `tuple()` 化），ndarray 输入双重付费（tuple 转换 + fromiter）
- 等价性：final_value 相对偏差 2.0e-13（容差 1e-9 内），trades 一致

### 待裁决（wang）

1. ~~分歧类 1 / 类 2 是否修复~~ → **已裁决修复**（第三轮落地，见下节）
2. ndarray 公开路径优化（`tobytes()` 键 + ndarray 直算）是否纳入本轮 —— 仍开放
3. `_backtest_impl` 的 ndarray 分支去留（当前仅内部可达）—— 仍开放

## 修复落地（2026-09-24 第三轮，wang 指令执行）

### backtest.py 变更（两处）

- 类 1：`n<=1` 与全程无买入的早期返回改为 `_INITIAL_CASH + 0.0 * last`，
  复刻基线 `0×期末价` 的 NaN 传播（n==0 仍恒 10000.0）
- 类 2：`buy_cost` 由 cumsum 差分改为 `np.where(is_buy, arr[1:], 0.0).sum()`，
  窗口外 NaN 不再污染；顺带移除 cumsum 与死变量 `first_day`

### 验证（test_backtest.py，19 项全 passed，xfail 清零，ruff clean）

- 原 4 个 xfail 全部转正；新增类 2 回归用例 `test_nan_before_first_buy_does_not_pollute_cash`
- 随机 NaN 对拍放开末位注入（200 组全范围），与基线逐位等价约束全面满足
- 无 NaN 序列结果不受影响：历史用例、随机 float/int 对拍原样通过

### 性能（n=20000 复测，where+sum 相对 cumsum 版）

| 路径 | 修复后 | 修复前 |
|---|---|---|
| impl(tuple) | 1.04 ms | 1.21 ms |
| impl(ndarray 直入) | 0.63 ms | 0.83 ms |
| 公开冷算（list / ndarray） | 1.64 / 1.92 ms | 1.70 / 1.99 ms |
| final_value 对拍偏差 | 6.8e-15 | 2.0e-13 |

- 公开路径仍受 `tuple()` 化支配，冷算慢于基线 1.33ms 的结构性问题未变（待裁决项 2）
