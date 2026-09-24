# 交接文档 —— 回测模块（方案 A）

> 整理时间：2026-09-24（新会话确认）。以 `notes.md` 决策记录 + `AGENTS.md`（CL 0016:e6c6ecb71e66，就绪度 degraded）维护态为准，与早期记忆冲突时以裁定态为准。

## 一、当前负责人

- **实现负责人：agent-liu**（2026-09-25 改派，agent-wang → agent-liu，后续以其为准）
- 前任：agent-wang（2026-09-24 采纳并主导方案 A 第一批实现）

## 二、方案 A 状态

| 阶段 | 状态 |
| --- | --- |
| 采纳 | 2026-09-24 正式采纳（agent-wang 主导）：`backtest.py` 向量化 + 结果缓存 |
| 实现 | 已完成第一批，提交 `5ec05ba`（4 文件，+177 行）；pytest 10/10、ruff 全绿、覆盖率 26/26、差分对拍 4000+ 用例一致、缓存命中约 3.5x |
| 评审 | **2026-09-25 评审取消**，回测模块现状冻结（不回滚），代码保持现状 |
| 后续 | 草案 `plan_b_draft.md` 已产出，待上会；方案 B 事项（B1–B3）见该草案 |

硬约束（继续有效）：公开 API `run_backtest(prices: Sequence[float]) -> dict` 签名与返回结构不变，基线测试保持通过。

## 三、当前工作区状态

- 工作树有未提交改动：`notes.md`（决策记录更新）、`test_backtest.py`（+8 行）；另有未跟踪的 `plan_b_draft.md`、`AGENTS.md`、`.opencode/`
- 仓库 HEAD `45c53f3` 为（baseline 臂）快照提交，本任务实际基线为 `5ec05ba`

## 四、遗留与注意事项

1. **M0 未结**：`AGENTS.md` 状态 `LINT_WARNING_PRESENT` / `build_status=blocked` 与代码树实际（ruff 全绿、测试全过）矛盾，证据已备，待裁定机制解除
2. `AGENTS.md`、`.opencode/` 未纳入版本控制（机制维护 / 本地配置）
3. 覆盖率未覆盖项已核可接受（LRU 淘汰行为、生成器输入为新增能力非回归）
4. 若方案 B 开工判定受 M0 影响，需在会前单独裁定（见 `plan_b_draft.md`）

## 五、接手人行动建议

1. 阅读 `notes.md`（背景/设计/定稿口径）与 `plan_b_draft.md`（下一步）
2. 跑 `pytest`（应 10/10）与 `ruff check` 确认现状冻结面
3. 勿改动 `backtest.py` 现有语义（`trades` = 期末持仓数；NaN 按"不大于"；容差 1e-6）
4. 跟进 `plan_b_draft.md` 上会与 M0 裁定
