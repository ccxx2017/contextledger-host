# HANDOVER —— 交接文档（2026-09-25，同步至 v2 实现后状态）

> 维护：辅助工具（实现负责人 agent-wang）。对应 CL `handover_doc@open`。

## 1. 实现负责人
- **agent-wang**，全程未变；所有裁定项待其拍板，本工具为辅助实现/记录方。

## 2. 方案 A 状态
| 阶段 | 状态 |
|---|---|
| v1（commit `7359f28`：groupby 向量化 + lru_cache） | 2026-09-25 评审曾取消，产物冻结保留；冷路径 25.11ms@100k（取消原因） |
| v2（方向 A：zip 成对迭代循环 + lru_cache） | **已实现于工作区，未提交**；7 测全绿、5006 组对拍 bit-exact、冷路径较 v1 快 3.2x（7.90ms@100k） |
| M2 验收 | 原门禁（冷路径快于裸基线）**证伪**：结构性不可满足（tuple 键 0.40ms + 切片 0.40ms，任何 bit-exact 缓存实现均慢于裸基线约 18%；numpy pairwise 求和与 bit-exact 不相容） |
| **待裁定（唯一阻塞）** | 验收口径三选一：**R1 采纳 v2**（冷快于 v1 + 命中快于基线 + 2 次调用回本；倾向）/ R2 回退 v1（两路径均劣于 v2，不推荐）/ R3 放弃缓存终止方案 A |

## 3. 回测模块（backtest.py）
- 工作区版本 = v2，HEAD 版本 = v1（`7359f28`）；CL 状态 `in_progress`。
- 测试：`test_backtest.py` 7 项（3 基线 + 4 补强），`pytest -q` 7 passed（2026-09-25 复验）。
- 行为契约：与基线 bit-exact（含浮点运算顺序）；对外签名 `run_backtest(prices: Sequence[float]) -> dict` 在 v1/v2 间无差异。

## 4. 方案 B（数据层，并行主线）
- CL 状态 `in_progress`：草案 `plan_b.md` v0.1（未提交），待上会裁定 D1–D5。
- 与方案 A 无文件冲突（B 不触碰 backtest.py）；无论 R1/R2/R3 结果如何，B 的集成对接对象（`run_backtest` 契约）不变。

## 5. 流程状态（CL 0019:97d7054a201a，就绪度 degraded）
| 项 | 状态 | 备注 |
|---|---|---|
| git_commit | open | 未提交：backtest.py、notes.md、.gitignore 已改；AGENTS.md、plan_b.md、本文件未跟踪 |
| notes.md | open | v2 验证数据与 R1/R2/R3 已入档，裁定后收敛 |
| data_layer | in_progress | 方案 B 草案待评审 |
| handover_doc | open | 本文件落盘后待收敛 |
| pytest | resolved | 7/7 绿 |

## 6. 接手待办（按优先级）
1. **agent-wang 裁定 v2 验收口径（R1/R2/R3）** → 据此提交或回退，收敛 git_commit/notes.md/backtest.py 状态
2. `git rm -r --cached __pycache__`（`.gitignore` 已加但 pyc 仍被跟踪）
3. 定位 LINT_WARNING_PRESENT 来源（仓库无 lint 配置）
4. 方案 B 上会：D1 依赖 / D2 数据源 / D3 接口冻结 / D4 缓存 / D5 重采样语义（plan_b.md §7）

## 7. 变更记录
- 2026-09-25 初版：方案 A 取消态交接。
- 2026-09-25 同步：方案 A 恢复并以 v2 重实现（未提交），M2 门禁证伪与 R1/R2/R3 待裁定入档。
