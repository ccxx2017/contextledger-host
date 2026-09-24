# Phase 0.5 v3 Resolver Reconciliation

本报告用于验证 benchmark harness 中的内联 resolver 是否与 `pending_merge_register` 的真实决策一致。

## 总览

- benchmark mentions 数量：`3`
- 覆盖到的 pending_merge 项数：`0`
- 已 resolved 项数：`0`
- 仍 tracked 项数：`0`
- 对账 mismatch 数量：`0`

## 对账结论

- 对账通过：所有已 resolved 的 pending_merge 决策都被内联 resolver 正确复现。

## 已 Resolved 决策

| raw_entity_ref | canonical_entity_ref | resolution | resolution_note |
|---|---|---|---|

## 仍 Tracked 的候选项

这些项在真实图里尚未形成最终 batch 决策，因此本次 harness 不强行 merge，只保留原实体键。

| raw_entity_ref | canonical_entity_ref | match_confidence | remediation_status |
|---|---|---:|---|
