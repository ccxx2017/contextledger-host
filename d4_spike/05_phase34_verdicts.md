# 阶段 3/4：S1–S6 终判、G4/G5 判定、差异与未验证清单

日期：2026-10-09。钉扎 DSH 0.2.0-rc.2。判据原文（pilot_design.md L23-28）不改动；判定按 DSH 实测映射，不降低标准。

## S1–S6 终判

| 判据（原文要点） | 判定 | 证据与说明 |
|---|---|---|
| S1 实际插件加载，无其他新增插件 | ✅ 通过 | 真实 Loader + 真实 profile（`--dump-config` 合成树含 `# == @contextledger/dsh-host-seam`）；运行时激活（旁证事件落盘）。pilot profile 新增插件仅本 seam（dsh-headless 为 boot 必需 app 插件，非本工作包引入的观察插件） |
| S2 事件完整采集与对齐（llm_call_start/tool/file.edited/压缩） | 🟡 部分 | llm_call_start（仅 provider/model 已解析的真派发）✅；tool_execute_before/after 按 call_id 成对 ✅；session_compacted ✅；**file.edited 未覆盖**——阶段 0/1 未定位到公开的文件变化事件时点，标**差异+未验证**；对账：各 run 事件数与操作数逐 run 核对（见 evidence/） |
| S3 最终模型输入可核验（请求前可观测边界的 dump 证据） | ✅ 通过（DSH 强项） | `llm/stream` 只读观测 `GenerateOptions.messages`（="exactly as the provider sees them"，types.d.ts L496-501）：run1/V2/送达 run 三次实测 `supply_msg_present=true` + msgId 与供给提议精确一致；**非推断** |
| S4 lifecycle 从真实抽取链路进入主图 | ❌ 未通过 | 抽取链路跑通（turn_086 → slice → extractor → patch_086 → resolver → 裁定 → apply → 发布 rev 0086:f77325d8e8cc），**但** patch 节点未带 lifecycle 字段（lifecycle_ref/state_slot/seq），主链 lifecycle_adjudicator 未触发。不降低判据；修复属抽取器质量改进（见差异清单） |
| S5 过期动作被实际阻止 | ⏸ 未验证 | 依赖 CL 工具阻断关口（本轮按硬边界全程关闭）。陈旧值识别素材已产出（V1 场景 alpha/beta），阻止行为本身未测 |
| S6 quarantine 后 readiness 被宿主实际消费 | ⏸ 未验证 | 送达 run 的发布 readiness=**degraded**（STATE_REVISION_STALE + lint 缺失）已如实入账与旁证，但"宿主行为改变（等待/升级）"的构造性场景未测；且当前供给文本未携带 readiness/reason_codes（改进项） |

## G4 判定：🟡 部分通过（抽取链路通；抽取质量有实质缺口）

六项核对：指代落地 ✅ / 工具调用未误当成功 ✅ / 短暂讨论未升格 ✅ / 约束未扩大 ✅ / **状态变更未入账 ❌**（owner=agentB→agent-zhao 的核心状态变化未形成带 entity_ref+state 的条目；"以该文件为准"新约束被抽成 OpenTask）/ **依赖边无来源 ❌**（new_edges 无 basis/confidence/raw 引用）。
**来源混淆发现**：DSH 运行时政策被抽成用户 Constraint（n_0206）、技能目录说明被抽成 Fact（n_0210）——系统注入内容混入任务事实。
抽取质量缺口属抽取器（deepseek-flash + prompt）质量范畴，按任务纪律**不归咎 DSH**，也不以宿主通过替代 G4 通过。

## G5 判定：✅ 通过（闭环成立，含如实降级）

25 条裁定全部落账（24 coexist + 1 alias，`resolved_by: user_adjudication`，`resolved_at_turn: 86`）；patch_086.resolved 应用入主图（快照 graph_state.turn_086.json）；发布 rev `0086:f77325d8e8cc`（**readiness=degraded 如实标注**，reason: STATE_REVISION_STALE + lint 证据缺失）；新会话送达：模型复述 revision + 条目名 ✅。
遗留：历史积压裁定仅覆盖逾期集；entity_resolver 假阳性率 24/24（token 相似度阈值过松）进质量报告。

## 差异与未验证清单（累计，不悄悄缩小）

1. file.edited 事件未覆盖（S2 部分）；
2. S4 lifecycle 字段缺失、adjudicator 未触发；
3. S5/S6 未验证（关口关闭/构造场景未做）；
4. 压缩后供给真实场景（mock 已覆盖状态转换）；
5. v4 zstd 归档对账（projcache/derived 证据已足够强，归档解压对账未做）；
6. 子 Agent、外部桥接、后台路径（§3.5）；
7. 提交级持久化：run2 derived 已证（0442bc48 在恢复会话 derived 中）→ **升格为已验证**；v4 归档对账保留为次要未验证；
8. `admittedCalls` 命名（实为尝试计数）待改；
9. entity_resolver 假阳性率 100%（24/24）——CL 侧质量改进建议；
10. 凭据轮换（用户动作）。
