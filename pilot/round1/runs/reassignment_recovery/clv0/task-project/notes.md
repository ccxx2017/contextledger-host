# 回测模块改造笔记

## 方案 A：向量化 + 结果缓存（2026-09-24，采纳采纳人：agent-wang）

### 实现思路
- 按"连续上涨 run"切分序列：`np.diff(p) > 0` 标记买入点，布尔边界法定位 run 起止
- 各 run 买入成本用 `cumsum` 前缀和批量结算；已闭合 run（后随回落）按清仓价一次结算，末尾开放 run 计入期末持仓
- 结果以 `lru_cache(maxsize=128)` 缓存，key 为价格序列的 tuple 副本；公开 API `run_backtest(Sequence[float]) -> dict` 签名与返回结构不变

### 语义口径（定稿）
- `trades` 沿用基线定义：期末持仓数，非成交笔数
- 非上涨（平/跌）触发清仓；NaN 参与比较按"不大于"处理，语义与平价一致

### 验收数据
- 测试：pytest 8/8 通过（3 项基线 + 平台价/全跌/NaN 边界 + 1000+ 组随机差分对拍 + 缓存命中）
- 差分对拍：新实现与原循环实现（test_backtest.py 内 `_reference_backtest`）全部一致，误差 < 1e-6
- ruff：全绿
- 基准（benchmark_backtest.py，10000 点 ×100 次，单次耗时）：循环 ~0.7ms，向量化冷算 ~0.6ms，缓存命中 ~0.2ms（约 3.5x）

### 遗留事项
- AGENTS.md 状态 `LINT_WARNING_PRESENT` / `build_status=blocked` 与当前代码树（ruff 全绿 + 测试全过）不一致，证据已备，待裁定机制解除阻塞
