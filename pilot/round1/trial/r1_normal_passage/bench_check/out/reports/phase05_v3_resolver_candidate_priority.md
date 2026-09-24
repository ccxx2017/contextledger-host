# Phase 0.5 v3 Resolver Candidate Priority

本报告用于给 batch-resolve 收敛提供优先级清单（仅针对 benchmark 覆盖到的 tracked 项）。

## 优先级规则

- `P0`：match_confidence >= 0.90
- `P1`：0.80 <= match_confidence < 0.90
- `P2`：0.70 <= match_confidence < 0.80
- `P3`：其余

## 候选清单

| priority | raw_entity_ref | canonical_entity_ref | match_confidence | remediation_status |
|---|---|---|---:|---|

## 重点建议

- 先处理 `P0/P1`：这些项最可能直接改变 resolver 的有效实体映射。
- 当前 benchmark 覆盖范围内已无高优先级 tracked 候选。
