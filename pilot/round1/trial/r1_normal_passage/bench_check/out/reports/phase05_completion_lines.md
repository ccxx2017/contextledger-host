# Phase 0.5 Completion Lines

本文件记录 Phase 0.5 封板后的完成线写法。
原则：按形态分别定，不用单一全局阈值拍板。

## Invalidation

- full：基线水位为 P/R=`1.000/NA`，Phase 1 不能回退。
- partial：当前 P/R=`1.000/NA`，完成线写法为“从 0 到非零”，即 precision 与 recall 都必须首次高于 0。
- conditional：当前 P/R=`1.000/NA`，完成线写法为“从 0 到非零”，即 precision 与 recall 都必须首次高于 0。
- revival：当前 P/R=`1.000/NA`，完成线写法为“至少把 revival 事件从 full replace 中分离出来”，即 precision 与 recall 均需高于当前水位。
- provenance_conflict：当前 P/R=`1.000/NA`，完成线是保守性门禁，按本基准可操作化为“false_positive_count = 0”，也即 provenance 冲突不得再被误判为失效事件。
- non_invalidation_decoy：当前 P/R=`1.000/NA`，完成线是保守性门禁，按本基准可操作化为“false_positive_count = 0”，也即 decoy 子集上不得再咬出任何失效事件。
- out_of_order_late：当前 P/R=`1.000/NA`，完成线写法为“保持 recall 不回退，同时提升 precision”，也即迟到旧观测不再误触发多余失效。
- alias_trap：该形态在 invalidation 维度当前无事件，P/R=`1.000/NA` 仅表示 pred/gold=`0/0`；封板不为其单设 invalidation 阈值，交由实体解析的 false-merge / false-split 维度约束。

## Valid-Time

- valid-time-present：这不是常规阈值项。当前 observed_at 在场=`0/0`，完成线写法是“从 0/4 变为非零即算 Phase 1 达标起点”。
- valid-time fallback：当前缺失 observed_at 时回退到达序=`0/0`，完成线是不得回退。

## Retrieval Waterline

- active-set Set-F1：当前水位=`0.000`，先记作基线水位，等待 Phase 1 再看是否与朴素基线拉开分离。
- must_include recall：当前水位=`1.000`，同样先记作基线水位，不在 Phase 0.5 封板时强行拔高。
