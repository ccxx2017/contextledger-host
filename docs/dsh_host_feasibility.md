# DSH 替换宿主可行性调查（工作包 D4 评审输入）

权威记录仍是 CL 主仓库 `graph/projects/abu_modern/host_integration/host_seam_decision.json`；
本文件是宿主侧的人工可读调查报告，不改动任何决策。两处不一致时以主仓库 JSON 为准。

- 调查日期：2026-10-05
- 裁定状态：已复核（self-review），见
  [dsh_host_feasibility_adjudication.md](dsh_host_feasibility_adjudication.md)——
  总体结论维持；M1 修正（Q1 证据面 / S3 观察面）已回写本文（§2 表、§3 Q1、§6 R2/R3）
- 调查对象：DeepSeek Harness（DSH）**已安装运行版 0.2.0-rc.2**
  （`@deepseek-ai/dsh`，本机 `lib/bin.js --version` 实证；官方仓库
  `github.com/deepseek-ai/deepseek-harness`，见包 manifest `repository` 字段）
- 结论一句话：**可行，且按 D1 同尺评分入围（≥3），架构裁决对 DSH 有利；
  现行 OpenCode 路径实际处于阻断态（GitHub 不可达 → 版本钉扎不可能闭合），
  DSH 路径无同类网络阻断。**

---

## 1. 为什么值得换：现行 OpenCode 路径的阻断点

`host_seam_decision.json` 的 `decision_status: pinned_sdk_pending_smoke`，其
`pinning_update_2026_09_06` 记录：

- 源码 checkout 停在 1.17.11+128 commits（dfeb1b50，2026-06-27），运行二进制 1.18.29；
- **版本对齐"源码级开放"**：GitHub 不可达（443 超时 / SSH 无公钥 / 无代理），
  本地无 1.18.29 对应标签——SDK 精确版本钉扎只是等效验证；
- load-bearing 接缝全部带 `experimental.` 前缀（官方自声明不稳定），无 CHANGELOG 可考。

更硬的实证在宿主侧代码里：`opencode/plugin/cl-v0-inject.js:89-108` 的注释与分支
"策略二（system.transform 变异被丢弃后的降级尝试）"——**experimental 接缝的注入
变异在真实管线中被丢弃过**，cl_v0 臂只能降级为"就地向最后一条 user 消息追加文本
部件、赌管线复用同一对象"。D1 方法要求"缺版本钉扎的结论一律作废"，而钉扎的
网络前提在本机不可恢复。

DSH 侧对照：npm 官方包本地已安装、版本可精确钉扎（锁文件）、每个接缝包都随
发布物附带 package-reference 级合同文档（含 Known Limitations 自合同），
无 GitHub 依赖即可完成全部逐签名复核。

---

## 2. DSH 接缝面 vs OpenCode 插件面（逐项映射，证据 = 安装树内官方 README）

现行宿主插件消费的四个面（`cl-shadow-observer.ts` / `cl-v0-inject.js`）与
DSH 的对应关系：

| OpenCode 插件面（1.18.29 SDK） | DSH 对应接缝 | 性质对比 | 证据（安装树内 README） |
|---|---|---|---|
| `chat.params`（采样参数快照） | `agent/request` 瀑布线 + `ctx.llm.prepareCall()` + `request/header`/`request/context` 日志事件 | 对等（DSH  additionally 记录持久日志） | dsh-agent-loop README「Request headers and adapter defaults」 |
| `experimental.chat.messages.transform`（最终输入快照/注入） | `agent/pre-step`：PreStepDecision = `{kind:'reject'}` 或 `{kind:'enter', messages, startsRequestSeries?}`——**注意（M1 修正）：`messages` 是本步新领取的输入批次（`UserMessage[]`），不是全量对话历史**；全量最终输入 = 持久会话日志的派生历史（无单点 transform 钩子，需经 Session 读取面重建）；另有 `agent.inject()`/`steer()` 与 `ctx.systemPrompt.section()/variable()` | **注入对等且更干净**（带来源标识的新消息，不依赖变异最终数组）；**全量观察面需重新设计**（见 R2，lib 级证据：dsh-agent-loop/lib/index.js:906-918、dsh-agent/lib/types/runtime-types.d.ts:92-99） | dsh-agent README:65-67「Intercept or observe work in flight」；dsh-agent-loop README「Step admission」；dsh-system-prompt README:56-70 |
| `tool.execute.before` / `tool.execute.after` | `tools/pre-execute`（allow/deny/ask 决策瀑布线）→ `ctx.tools.guard()`（单调 guard）→ `tools/execute`（包裹派发）→ `tools/post-execute`（检视/替换结果/附加上下文）→ `tools/result`（终局只读观察） | **DSH 管线更完整**：五段固定管线，事件成对持久化 | dsh-tools README:83-88「Enforce policy on calls」、:102-105「Design concept」 |
| `permission.ask`（output.status ∈ ask\|deny\|allow） | `tools/pre-execute` 的 ask 决策 + `ctx.approval`：`ask` 策略路由到 answerer 瀑布线（人或机器），`never` 确定性拒绝；`approval/asked`/`approval/decided` 审计事件 | **对等且更强**：拒绝是单调的（"no later listener can turn that denial back into permission」），且自带持久审计 | dsh-user-approval README:11-12、:28-36、:84-87 |
| `event` 总线：`file.edited` / `session.compacted` | `workspace/changes` 会话事件（git 快照 diff + 文件工具全量捕获，逐 turn）/ `compaction/start`/`compaction/summary`/`compaction/end`/`compaction/summary-error` 持久事件 | 对等，且均为可重放的持久会话日志 | dsh-workspace-changes README Summary；dsh-compaction-basic README「The region transaction」 |
| （OpenCode 插件明示不保证的子 Agent/后台路径） | `dsh-subagent`：in-process spawn/fork 子 Agent 与根同进程同 scope 继承（`ctx.tools.restrict` 的 "the global tools one agent inherits"）；另有 ACP/SDK/Codex/Claude Code 外部桥子 Agent | **机会项**：in-process 支路有全覆盖可能，须 spike 证明；外部桥支路是另一条路径 | dsh-subagent README Summary；dsh-agent README:61-64「Scope registrations」 |

DSH 拦截扩展点的权威映射另有官方佐证：`dsh-hooks-codex` README「Hook point
mapping」一节逐条列出 Codex 五钩子宿主内落点——`UserPromptSubmit→agent/pre-step`、
`PreToolUse→tools/pre-execute`、`PostToolUse→tools/post-execute`、
`Stop→agent/turn-stopping`、`SessionStart→agent/created` 初始化。同节明确：
"bespoke behavior belongs in a native plugin on the same extension points"
（原生 Cordis 插件拥有完整 harness API，无需 hook 协议中介）——CL 应写原生插件，
不碰 Codex/Claude Code 桥。

---

## 3. Q1-Q4 同尺评分（按 decision.json 的 scoring_rule）

| 项 | 判定 | 依据 |
|---|---|---|
| Q1 LLM 调用前钩子 + 结构化 payload | **yes** | 三件组合：`agent/pre-step` 新输入批次（结构化，lib 级 dsh-agent-loop/lib/index.js:911）+ `agent/request`/`prepareCall`/`request/header` 模型路由结构化面 + **Session 派生历史**（持久日志可重建请求，loop 不变量伴件以此为职责）。（M1 修正：非单点全量 transform，见 R2） |
| Q2 注入无需 fork | **yes** | `agent/pre-step` enter 可**替换**进入本步的消息；`agent.inject()`；`steer()`；`ctx.systemPrompt.section()/variable()`；`tools/post-execute` 附加上下文——全部官方插件 API |
| Q3 工具调用前阻断 | **yes** | `tools/pre-execute` allow/deny/ask + 单调拒绝 + `ctx.approval`（ask/never、fail-closed）。（args 改写缺失见 §6-R5，对 CL 关口需求非 load-bearing） |
| Q4 跨版本稳定 | **partial→按 D1 尺记 0** | 本地精确版本 0.2.0-rc.2 + 官方包随附完整合同文档；但 DSH 自述 preview 软件，rc 间契约有变动史（0.1.1-rc.2→0.2.0-rc.2 的脚手架合同即被要求重新推导），无传统 CHANGELOG |
| **score_Q1_Q4** | **3** | 与两台现行宿主同分，**入选**（≥3） |

**架构裁决**（D1 tie-break：Q2+Q3 双是者进入）：评审首场景是长程编码任务
（方案取消 k / 改派 k+3 / 旧工具结果晚到 k+6 / 恢复 k+9，见
`scenarios/reassignment_recovery.json`），需要编码 Agent 的 session/tool 循环。
**DSH 即编码 Agent harness 本体**（`dsh-agent-loop` 驱动 turn/step/工具循环 +
`dsh-subagent` 子 Agent 树 + 持久会话 + 沙箱 + 审批），不是消息网关，也不需要
"平手按架构分胜负"——DSH 在该维度直接胜出。叠加 §1 的阻断点现实：
现行 OpenCode 路径无法闭合 D1 硬前置，DSH 路径无同类阻断。

---

## 4. 机器契约兼容性（宿主可插拔的结构性证明）

CL 宿主集成从设计上契约中立（`README.md` 边界规则 1-2）：

- 宿主绝不 import CL 主仓库代码；唯一机器契约 = `verify_preaction.py` CLI
  退出码（0=前提成立 / 2=前提失效）+ 双方约定的 JSON 格式
  （`assembler_manifest.v1`、`shadow_diff_report.v1`、场景定义）；
- `host_event.v1` 事件模型（llm_call_start / tool_execute_before /
  tool_execute_after / file_edited / session_compacted + context_refs
  {entity, state, source}）是宿主中立的——OpenCode 插件只是它的一个发射器；
- `opencode/adapter/observe.py` 只吃 JSONL/场景，不碰宿主代码；CL 侧
  `pilot_turn_driver.py` / `assembler_manifest.py` / `verify_preaction.py`
  与宿主选择完全解耦。

**因此替换宿主 = 换发射器 + 换 runner 的宿主调用行，CL 侧与证据链零改动。**

---

## 5. 迁移面清单

### 新写（DSH 侧）

1. 外部 Bundle 包（宿主仓 `dsh/` 目录起，包名建议
   `@contextledger/dsh-host-seam`），原生 Cordis 插件根（named `apply`
   命名空间或默认导出函数），**root-scope** 注册：
   - `agent/pre-step`：只读发射 `llm_call_start`（enter 批次即宿主上下文快照）
     +（cl_v0 臂）enter 决策阶段替换消息注入 CL 任务记忆；
   - `tools/pre-execute`：cl_v0 关口——readiness=blocked 或
     `verify_preaction.py` 退出码 2 时返回 deny（模型可见 reason）；
   - `tools/post-execute`：附加上下文（注入的受控通道，替代 OpenCode 的
     "就地 user part 追加减辣策略"）；
   - `tools/result` + 会话事件观察者（`compaction/*`、`approval/*`、
     `workspace/changes`、`hook/*`）：发射 tool_execute_before/after、
     file_edited、session_compacted；
   - 落 `host_event.v1` JSONL 路径由 `CL_SHADOW_TRACE` 环境变量或
     profile config 决定，格式与 OpenCode 发射器逐字节同构。
2. pilot profile（建议 `dsh-pilot`，基于 headless bundle）：`dsh plugin
   --profile dsh-pilot add <package>` 安装本包，`cordis.patch.yml` 以
   `insert:` 行纳入，模型路由/maxParallelToolCalls 显式配置，保证冒烟可复现。
3. 控制文件协议沿用：`.opencode/cl_v0.json` → profile/workspace 约定路径
   （内容仍是 `cl_common.refresh_control()` 产出的同一 JSON）。

### 改写（宿主仓现有工具链）

4. `tools/cl_turn.py`：`OPENCODE_BIN run [-c]` → `dsh --profile dsh-pilot`
   （headless 单发退出，`--session-id <id>` 对映 `-c` 续会话，
   `CL_SHADOW_TRACE` 环境变量透传不变）。
5. `tools/cl_install.py` / `cl_disable.py` / `cl_recover.py`：安装面从
   "拷贝 js 到 `.opencode/plugin/`" 改为 "profile 安装 + patch insert"，
   指纹重采逻辑对齐（loaded_plugins / 全量 sha256 / 启动命令 / 有效配置）。
6. `tools/smoke_cl_v0_inject.mjs`：改为挂载真实 Bundle 包走 Loader
   （技能要求"stub {name, inject, apply} 不能证明包加载"）。

### 不动

7. `opencode/adapter/observe.py`、`scenarios/*.json`、`traces/` 纪律；
8. CL 主仓库全部脚本（pilot_turn_driver / assembler_manifest /
   verify_preaction）、`shadow_diff_report.v1` 产出、成对运行双臂协议、
   S1-S6 判据本身（需对 DSH 重跑，判据不改）；
9. `host_seam_decision.json` 原记录（新决策走主仓库新记录，不覆写）。

---

## 6. 风险与未决项（诚实清单）

- **R1 rc 波动**：0.2.0-rc.2 为 preview 版；技能 fast-path 脚手架合同只审计到
  0.1.1-rc.2。需在 0.2.0-rc.2 上重新推导全部钉扎项：提交锁文件 + 对随包
  `lib/*.js`（src 未随发布物）做 D1 式逐签名复核，至少覆盖 `agent/pre-step`、
  `tools/pre-execute`、`ctx.approval.request`、装配瀑布线的签名与调用点。
- **R2 S3"最终模型输入可核验"边界（M1 修正后升级）**：DSH **无单点 messages.transform**；
  `agent/pre-step` 的 `messages` 仅为本步新领取输入批次（lib 级证据：
  dsh-agent-loop/lib/index.js:906-918 `messages: claimed`；runtime-types.d.ts:92-99）。
  全量最终输入 = 持久会话日志派生历史，`extractContextRefs` 类全量扫描必须改为读
  Session 派生历史/持久日志。spike 必须证明插件侧存在公开的派生历史读取面
  （Session API 或 dsh-session-query）；若无 → S3 按原判据不可满足 → 按
  log_tail_adapter_only 同款降级逻辑处理，不得硬做。
- **R3 子 Agent 覆盖未证**：in-process spawn/fork 与根同进程、scope 继承——已有
  lib 级结构性证据（dsh-tools/lib/index.js:3225、3504 的 `scopeTarget(this,
  exec.agent)`：工具瀑布线按执行 Agent 的 scope 派发，根注册监听器被子 scope
  继承）；ACP/SDK/Codex/Claude Code 外部桥子 Agent 不在同一 Cordis 进程。
  OpenCode 插件本就明示不覆盖子 Agent；DSH 是缩小该缺口的机会，但运行时
  spike 证明仍缺席，不得在验证前宣称。
- **R4 approval fail-closed**：headless pilot 无终端 answerer 时 ask 解析为
  `unavailable` 直接失败；pilot 必须自组 terminal answerer（CL 决策插件可充当
  machine answerer）。注意审批请求仅在 open turn 内有效、只有 one-shot grant、
  请求不带工具参数（answerer 只见 tool name/reason/call id）。
- **R5 工具参数改写缺失**：`tools/pre-execute` 有意不支持改写 `exec.arguments`
  （官方 deferred design）。OpenCode 的 `permission.ask` 同样不可改写（改写在
  `tool.execute.before`）；CL 关口只需"阻断 + 注入"，此项记录在案、非阻断项。
- **R6 会话/工作区隔离语义差异**：DSH 会话持久化在 DSH_HOME（session-id 续
  会话），workspace cwd 由 agent 配置决定；pilot 双隔离纪律（工作目录/会话/缓存
  物理隔离）需按 DSH 形态重新落一次设计，不能照抄 `.opencode/` 项目目录方案。
- **R7 工作量与门禁**：Bundle 包需走完整交付门（单测 → Cordis Context 实测 →
  真实 Loader/`cordis.patch.yml` → typecheck/tests/build → `validate_plugin.mjs
  --built` → `accept_plugin.mjs`）> pilot profile 重装 > S1-S6 重跑 > 指纹 v3
  重采；且 2026-09-25 收口裁定"关口默认关闭"的 reasoning 在 DSH 更强的阻断
  原语（单调 deny + 审批审计）下需要重新审议。

---

## 7. 建议路径（不改决策，仅供 D4 评审参考）

1. **先 spike 后决策**：按 pilot_design.md「第零步」纪律，做一个最小只读
   观察 Bundle 装进 `dsh-pilot` headless profile，跑
   `reassignment_recovery.json` 场景 → 对照 S1/S2/S3 取证据；
2. spike 通过则更新主仓库决策记录为 `dsh_primary`（或并列宿主），
   **OpenCode 归档为降级路径**（其 SDK 钉扎快照与插件代码保留）；
3. spike 暴露 R2/R3 不可接受项则回退：DSH 仅作影子宿主
   （log_tail_adapter_only 同款降级逻辑），不硬做成对运行；
4. 全程遵守边界规则：本调查与后续 DSH 插件都在宿主仓，CL 主仓只新增
   指针/场景/指标记录。

## 附：本调查引用的安装树内证据路径（版本 0.2.0-rc.2）

`%APPDATA%\npm\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\` 下：
`dsh-agent`（:65-67, :84-87）、`dsh-agent-loop`（:73-76, :119-121）、
`dsh-tools`（:83-88, :102-105, :230）、`dsh-user-approval`（:11-12, :28-36,
:84-87）、`dsh-compaction-basic`（region transaction 段）、
`dsh-workspace-changes`（Summary 段）、`dsh-system-prompt`（:56-70, :96-97）、
`dsh-hook-protocol`（:32-41）、`dsh-hooks-codex`（:78-83, :89-103）、
`dsh-subagent`（Summary 段）。Profile 形态实证：
`%USERPROFILE%\.dsh\profiles\web\cordis.patch.yml`（insert 行）+
`package.json`（`dsh.profile.bundles`）+ `cordis.yml`（补丁合成说明）。
