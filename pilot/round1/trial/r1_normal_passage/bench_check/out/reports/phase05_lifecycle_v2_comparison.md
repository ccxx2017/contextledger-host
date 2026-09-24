# phase0_current v1 vs v2（lifecycle / state_slot 语义）对照

> eval-v2 分支（score_phase05 v2，2026-09-24）。
> v1 = 实体级 LWW、全量取代（validate_v2 上 0TP/6FP/2FN 的旧语义）；
> v2 = 主链 lifecycle 语义：同 (归属键, 槽位) 才取代、跨槽位共存（契约 09 §4.1/§9）、晚到不取代。
> v2 的归属键/槽位/时间判定直接调用 lifecycle_fields 真实函数，评分器不自造语义。

| 基线 | 失效判定 | 失效 P | 失效 R | 活跃集 Set-F1 | must_include R |
|---|---|---|---|---|---|
| v1 phase0_current | TP=0 / FP=1 / FN=0 | 0.0 | 1.0 | 0.0 | 1.0 |
| v2 phase0_current_lifecycle | TP=0 / FP=0 / FN=0 | 1.0 | 1.0 | 0.0 | 1.0 |

## 逐轨迹失效事件对照

| 轨迹 | v1 TP/FP/FN | v2 TP/FP/FN |
|---|---|---|
| r1np_clv0_trial | 0/1/0 | 0/0/0 |

## v2 残余 FP / FN 明细（测量局限披露）


> 残余差异的已知来源：实体键为"首 mention + pending_merge 归并"的仿真口径（无共享 mention 且登记簿无映射 → FN）；同一表面 mention 槽位内并列条目（P01/P02 类）无法从 mention/dimension 机械区分 → FP。二者均为仿真层测量局限，须在基线报告中与主链真实行为区分归因。