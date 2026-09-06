# 冒烟结果 S1–S3（2026-09-06，无头 opencode run）

环境：隔离项目 `pilot/smoke-project/`，项目级插件 `.opencode/plugin/cl-shadow-observer.js`（零依赖 JS），
全局配置未动（全局 plugin 键 ABSENT——插件仅该项目加载，无其他插件牵连）。
任务：创建 smoke.txt（内容 ok）→ Agent 实际创建并 `wc -c` 自验证。

## S1 插件实际加载 —— ✅ PASS

trace 采集到 12 个事件、5 类 hook 全部生效
（`sampling_params`×4 / `llm_call_start`×3 / `tool_execute_before`×2 / `tool_execute_after`×2 / `file_edited`×1）。
证据：`pilot/smoke_20260906_events.jsonl`（trace 目录 gitignored，故复制入库）。

## S2 原始事件完整采集与对齐 —— ✅ PASS（含一条提取器备注）

事件与会话操作对账一致：3 次 LLM 调用（多步循环：write → bash 验证 → 最终答复）、
工具事件含真实 args（write 的 filePath/content 完整可见——这是 S5 阻断面的抓手）、
file.edited 1 次。
备注：`context_refs` 实体提取启发式在本条无实体引用的会话中为 0 命中（预期行为）；
pilot 需用含实体状态语义的真实文本验证提取率。

## S3 最终模型输入可核验 —— ✅ 边界可观测性 PASS

`llm_call_start` 事件在 `experimental.chat.messages.transform` 边界采集
（payload.boundary 字段明确标注 final pre-model input），最后一轮 message_count=3。
即：**最终输入在发送前可完整 dump**——评审 §三.5 要求的可观测边界成立。
注意：本条仅证明边界可观测；"最终输入包含 CL 装配结果且未被覆盖"需 CL-V0 注入臂
（同一 hook 改写 messages/system）+ 对照 dump，属 pilot 主体，不在本冒烟范围。

## 尚未通过（后续步骤）

- **S4** lifecycle 从真实抽取链路进入主图：需 extractor prompt 输出 lifecycle 字段
  （当前 prompt 不产出 → 新实验版本 prompt v2，按评审 §六.6 开新版本，不改冻结实现）
- **S5** 过期动作实际阻止：需 CL-V0 插件把 `verify_preaction.py` 接入 `permission.ask`
  + `tool.execute.before`（args 已可见，抓手已验证）
- **S6** quarantine readiness 被宿主消费：需宿主读取 assembler_manifest 的消费逻辑
- 版本对齐残余：源码 checkout 仍在 1.17.11（GitHub 不可达）；SDK 级钉扎已完成
  （`opencode/sdk-1.18.29/`）；配置目录 SDK 1.18.23 待随插件安装对齐 1.18.29


## S4 lifecycle 进真实抽取链路 —— ✅ PASS（2026-09-06）

实验版本：`graph/prompts/extractor_system_lifecycle_v2.md`（冻结 v1 未动）。
隔离项目：主仓库 `graph/projects/pilot_s4/`（不碰 84-turn 冻结基线）。
模型：deepseek-v4-flash（用户轮换后的新 key；旧 key 401 已由用户更换）。

证据链（评审 §二要求的全链）：

```
真实 raw（取消/改派/周报语义 + 时间戳）
→ Extractor（DeepSeek 真实调用）产出 patch：5 节点全部带 lifecycle 字段
   lifecycle_ref ×3 正确区分（lc-refactor-plan / lc-quant-reviewer-impl / lc-weekly-report-2026-w36）
   state_slot ×4 维度正确（approval_status / build_status / owner / execution_status）
   lifecycle_seq 未输出（按指令，机械层职责）；observed_at 全部来自本轮时间戳
→ reconcile 通过（0 errors / 0 LIFECYCLE_FIELD_INVALID）
→ apply 提交 + lint 绿（rc=0）
→ 主链 adjudicator 在真实数据上触发：5/5 append 决策
   同 lifecycle 不同 slot 正确共存（周报的 owner 约束与 execution_status 任务并存）
```

证据文件：主仓库 `graph/projects/pilot_s4/`（patch / reconcile 报告 / 提交图 /
s4_adjudication_evidence.json）。

抽取质量发现（登记，prompt v2.1 迭代项）：
- pytest 结果原文标注 observed 09:50（早于本轮），extractor 未将其填入 effective_at
  而是统一用本轮时间戳——晚到语义会被记为轮内事件。属抽取质量问题，非机制缺陷。
- 修复方向：prompt v2.1 明确"原文出现更早时间戳时填入 effective_at"。


## S5 过期动作实际阻止 —— ✅ PASS（2026-09-06）

场景：CL 侧 `graph/projects/pilot_s5/` 两态历史（r1: alpha=open → r2: 注入取消，
alpha 全部退出当前态）。宿主项目 `pilot/s5-gate-project/` 装 CL-V0 关口插件
（`tool.execute.before` 中调 verify_preaction.py，exit 2 即抛错阻断）。

**第一轮（依据过期 r1 行动）：**
- 关口裁定：write 工具，exit_code=2，reason_codes=[STATE_REVISION_STALE] → 抛错阻断
- **副作用核验：stale_action.txt 未被创建**（工具真实未执行，非仅返回失败）
- Agent 自行复述了契约恢复行为："文件未创建。需要宿主重新装配后重试"

**第二轮（模拟重新装配：控制文件 expected_revision 更新到 r2）：**
- 关口裁定：write 工具，exit_code=0 → 放行
- **副作用核验：stale_action.txt 创建成功，内容 fresh**

评审 §三.4 验收标准逐条对照：
| 要求 | 结果 |
|---|---|
| 旧动作没有真正执行 | ✅ 文件不存在（副作用层核验，非仅返回值） |
| 宿主采取契约规定的恢复行为 | ✅ 重新装配（r2 凭据）后动作成功 |
| 覆盖范围 | 仅主会话工具调用（write 已实证）；子 Agent/后台路径不在保证范围 |

证据：`traces/s5/host_events_run{1,2}.jsonl`（cl_gate_verdict 事件含 exit code 与
reason_codes）；控制文件 `.opencode/cl_gate.json`（唯一机器契约 = verify_preaction
退出码 + JSON 控制文件，未 import CL 代码）。

实现备注：关口 fail-open（控制文件不可读时放行并留痕 cl_gate_error）——关口自身
故障不得放大为任务故障；该取舍记录待评审确认。


## S6 quarantine 后 readiness 被宿主实际消费 —— ✅ PASS（2026-09-06）

场景：CL 侧 `graph/projects/pilot_s6/` 存在未裁定隔离条目（turn_002_failed，
disposition=unreviewed）→ assembler_manifest 判 **blocked**
（reason_codes=[QUARANTINE_NONEMPTY, LINT_WARNING_PRESENT]，unresolved=[turn_002_failed]）。
宿主项目 `pilot/s6-readiness-project/` 装 readiness 消费插件（读 manifest，blocked 即阻断）。

**第一轮（blocked）：**
- 关口拦截：CL_READINESS_BLOCKED，展示 reason_codes 与未裁定事件
- Agent 明确拒绝绕过："这是就绪门控在拦截……我不会绕过该门控强行写入"
- **副作用核验：quarantine_probe.txt 未创建**
- 过程发现：首跑时控制文件 manifest 路径写错（run/ vs reports/），fail-open 放行并留痕
  cl_gate_error —— 插件按契约工作，也暴露"控制文件路径正确性"须进 pilot 装配清单

**裁定 + 重新装配：** disposition unreviewed → requeued（模拟人工裁定，附裁定注记）
→ manifest 重生成：readiness=**degraded**（QUARANTINE_NONEMPTY 清零，剩 lint warning 属知情项）

**第二轮（degraded 放行）：**
- 关口裁定：readiness=degraded → 放行 + degraded_ack（知情留痕）
- **副作用核验：quarantine_probe.txt 创建成功（内容 probe）**
- 过程备注：首轮重试遇 zhipuai 端点挂起（13 分钟无输出），杀进程重试立即成功——
  宿主端点稳定性是成对运行的已知风险

至此**冒烟清单 S1–S6 全部通过**：实验装置被证明真实工作
（插件加载/事件采集/最终输入可观测/lifecycle 真实抽取/过期动作实际阻止/quarantine
readiness 实际消费）。下一步按评审顺序：pilot 开发轨迹（P1 取消→晚到，P2 改派→恢复）
→ 冻结 validate_v2 → 正式成对运行。
