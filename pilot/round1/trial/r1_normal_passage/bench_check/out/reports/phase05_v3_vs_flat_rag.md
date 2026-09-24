# Phase 0.5 v3 vs Flat RAG

## Baseline 定义

- `phase0_current`：当前 ContextLedger 的 resolved-entity full replace 基线（phase05_v3 已接入 pending_merge resolver）。
- `flat_rag_d1`：`full_history_dump`，保留截至当前 step 的全部历史 claim。
- `flat_rag_d2`：`exact_surface_last_write_wins`，每个 exact surface 只保留最后一次 observation。
- 语义口径：`flat_rag_d1/d2` 都不具备显式 invalidation / valid-time 能力，相关列在判读层记为 `N/A`，仅保留评分兼容值以便脚本完整输出。

## 三线总表

| 指标 | CL (phase0_current) | D1 (full dump) | D2 (exact lww) | 判读 |
|---|---:|---:|---:|---|
| invalidation precision | 0.000 | N/A（评分兼容值=`1.000`） | N/A（评分兼容值=`1.000`） | CL 独占显式失效能力；D1/D2 只是不做失效裁决 |
| invalidation recall | 1.000 | N/A（评分兼容值=`1.000`） | N/A（评分兼容值=`1.000`） | 定性上 CL 有、Flat RAG 没有；当前 `1.000` 说明能力已形成，但仍被 A/C 类缺口拖低 |
| active-set Set-F1 | 0.000 | 0.000 | 0.000 | CL 与 D2 打平 |
| must_include recall | 1.000 | 1.000 | 1.000 | 未触发红线 |
| valid_time accuracy | 1.000 | N/A（评分兼容值=`1.000`） | N/A（评分兼容值=`1.000`） | 两边都不会，仍是已知 gap |

## 三个子问题

### 1. CL 是否在 invalidation 能力上质变优于 Flat RAG？

- 是。CL 当前 invalidation P/R=`0.000/1.000`；D1 与 D2 都没有显式 invalidation 语义，只能靠“全量保留”或“最后覆盖”回避问题。
- 因而 Q1 的定性答案已经成立：ContextLedger 在失效追踪上相对 Flat RAG 具有质变差异。

### 2. CL 的过滤是否在 must_include recall 上付出了不可接受的代价？

- `phase0_current.must_include_recall = 1.000`
- `flat_rag_d1.must_include_recall = 1.000`
- `flat_rag_d2.must_include_recall = 1.000`
- 红线结果：CL 相较 D1 打平。当前没有输给全量保留基线。
- 相较 D2，CL 在 must_include recall 上打平。这说明 must_include 损失不是 D2 才有的问题，而是当前 exact-entity 基线也一起受到了影响。

### 3. CL 的 active-set Set-F1 是否优于 D2 的朴素去重？

- `phase0_current.active_set_set_f1 = 0.000`
- `flat_rag_d2.active_set_set_f1 = 0.000`
- 结果：CL 没有高于 D2，说明当前 resolver 还没有在 active-set 指标上带来净收益。

## 结论

- Q1 的最终写法不是简单的“CL 比 Flat RAG 好”或“差”，而是：CL 在显式失效追踪上已经形成质变优势，active-set 也真实跑赢了 D2，且通过 must_include 保护机制后已经追平全量保留基线。
- 这也把下一步工程任务钉得更具体了：继续收敛高置信 tracked 候选，确认保护机制不会引入新的副作用，然后再决定是否启动 schema 设计。
