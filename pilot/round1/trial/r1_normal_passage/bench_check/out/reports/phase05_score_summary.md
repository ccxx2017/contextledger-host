# Phase 0.5 评分摘要

## 两条基线

- phase0_current: invalidation P/R=`0.000/1.000`，active-set Set-F1=`0.000`，must_include recall=`1.000`，valid-time=`1.000`
- phase0_current.valid_time_breakdown: observed_at 在场=`0/0`，缺失回退=`0/0`
- flat_rag: invalidation P/R=`1.000/1.000`，active-set Set-F1=`0.000`，must_include recall=`1.000`，valid-time=`1.000`
- flat_rag.valid_time_breakdown: observed_at 在场=`0/0`，缺失回退=`0/0`

## 初版结论

- Phase 0.5 已进入封板并完成封板动作：先拆 invalidation P/R，再定完成线，最后把必要性弱证与 valid-time 从零起步写实。
- active-set / must_include 仍打平：phase0_current 相较 Flat RAG 在 active-set Set-F1 上提升 `0.000`，在 must_include recall 上提升 `0.000`。
- invalidation P/R 已补回：phase0_current 相较 flat_rag 的 precision 差值=`-1.000`，recall 差值=`0.000`；这是当前唯一明确发生分离的指标族。
- decoy 检查结果：false_positive_count=`0` / overall_false_positive_count=`1` (share=`0.000`)；phase0 在 non_invalidation_decoy 上同样出现过度失效，但 precision 损失并不只集中在 decoy；partial / conditional / revival / provenance 也共同贡献了大量假阳性。这说明 §3.3 的问题不只是 decoy 咬钩，而是当前失效裁定整体偏激进，Phase 1 仍须默认保守。
- valid-time-present 已写实：phase0 == flat_rag，差值=`0.000`；observed_at 在场=`0/0`，这表示能力缺失，列为 Phase 1 硬目标，不记作 Phase 0.5 失败。
- valid-time fallback 可工作：缺失 observed_at 时回退到达序=`0/0`。
- 必要性结论保持诚实：当前是弱证成立。唯一分离的 invalidation P/R 里，flat_rag 的静默覆盖不计为失效事件，因此真正的能力分离仍要等 Phase 1 把 partial / conditional / valid-time 做出来。
- alias 策略对比：保守合并 false_split=`0.000` / false_merge=`0.000`；激进合并 false_split=`0.000` / false_merge=`0.000`。
- 加权代价：equal_cost 偏向 `tie`，split_is_2x 偏向 `tie`，merge_is_5x 偏向 `tie`。
- 结论不是“保守永远更优”，而是“是否更优必须看 false-split 与 false-merge 的真实代价比”。
