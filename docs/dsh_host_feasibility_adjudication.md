# DSH 可行性报告复核裁定书（对 docs/dsh_host_feasibility.md）

- 裁定日期：2026-10-05
- 裁定方法：把报告的全部承重结论从"README 级声明"升级到"装船产物级验证"
  （直接检查安装树内随包发布的 `lib/*.js` 与 `lib/types/*.d.ts`，D1 式 file:line 证据），
  再逐项裁定。**程序性声明：本裁定由报告同一执行者完成（自审），非独立审计；
  按项目纪律，主仓决策记录引用本裁定时应标注 self-review，spike 后补独立复核。**

## 一、装船产物级验证结果（0.2.0-rc.2，路径缩写 DSHAI = `%APPDATA%\npm\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai`）

| # | 报告承重结论 | 验证证据（file:line） | 裁定 |
|---|---|---|---|
| V1 | `tools/pre-execute` allow/deny/ask 瀑布线存在 | DSHAI\dsh-tools\lib\index.js:3225（`ctx.waterfall(carrier, "tools/pre-execute", …)` 缺省 allow） | ✅ 成立 |
| V2 | `tools/post-execute` 可检视/替换/附加上下文；`tools/result` 只读终局 | 同上 :3504（缺省 accept，accept 不可同时替换 value+content）、:3417 | ✅ 成立 |
| V3 | 管线阶段顺序与冻结有不变量伴件强制 | DSHAI\dsh-tools\lib\invariant.js:10-87（pre→execute→post→result 顺序、repeated pre 拒绝、result 冻结） | ✅ 成立（阻断权威性加分） |
| V4 | 审批面 `approval/asked`+`approval/decided` 审计对、turn 内有效、fail-closed | DSHAI\dsh-user-approval\lib\index.js:130-139；lib\invariant.js:202-214（open-turn 强制、outcome 词表校验） | ✅ 成立 |
| V5 | 压缩持久事件 `compaction/start\|summary\|end` | DSHAI\dsh-compaction-basic\lib\index.js:469、484、634 | ✅ 成立 |
| V6 | 注入 API `inject()/steer()/followup()` 存在 | DSHAI\dsh-agent\lib\types\runtime-types.d.ts:192-209 | ✅ 成立 |
| V7 | 系统提示装配面 `systemPrompt.assemble` 在 step 流程内被调用 | DSHAI\dsh-agent-loop\lib\index.js:907 | ✅ 成立 |
| V8 | 工具瀑布线按执行 Agent 的 scope 派发（`scopeTarget(this, exec.agent)`）→ 根注册监听器被子 Agent scope 继承 | DSHAI\dsh-tools\lib\index.js:3225、3504 | ✅ 成立（子 Agent 工具覆盖的结构性证据，仍需运行时 spike） |
| **V9** | **报告原述：`agent/pre-step` enter 批次"即进入该步的模型输入全量"** | DSHAI\dsh-agent-loop\lib\index.js:906-918（`messages: claimed` = inbox 本步**新领取批次**）；DSHAI\dsh-agent\lib\types\runtime-types.d.ts:92-99、304-310（`messages: UserMessage[]`） | ❌ **不成立，需修正** |

## 二、修正项（1 项，实质性）

**M1（V9）——Q1 证据面与 S3 观察面表述越权。**

- 事实：`agent/pre-step` 的 `messages` 是本步**新领取的输入批次**（新 user 消息 +
  运行时上下文投影），不是完整对话历史。完整模型输入 = loop 从持久会话日志推导的
  派生历史（`deriveMessages()`，loop 内部），无单点 transform 钩子。
- 对 Q1 的影响：判定仍为 **yes**，但证据面修正为三件组合——pre-step 新输入批次
  （结构化）+ `request/header`/`request/context` 持久日志 + **Session 派生历史读取**
  （持久日志可重建请求；loop 的 invariant 伴件本身以"从会话日志重建请求"为职责，
  说明日志即权威输入记录）。计分不变（3 分入围结论不变）。
- 对 S3 的影响：风险 **R2 升级**——不是"边界前移一格的表述降级"，而是**观察面需
  重新设计**：CL 的 `extractContextRefs`（扫全量最终消息）在 DSH 上必须改为读
  Session 派生历史/持久日志，而非单一 hook payload。spike 必须证明插件侧存在可用的
  公开读取面（Session API 或 dsh-session-query），否则 S3 判据按原样不可满足。
- 对 Q2 的影响：无（逐轮注入语义反而更干净——`inject()`/enter 批次注入的是带来源
  标识的新消息，不依赖 OpenCode 那种"变异最终数组赌管线复用对象"的脆路径）。

## 三、强化项（2 项）

- **S+1**：报告 §2 表中"DSH 管线更完整/阻断更强"的论断，现全部有 lib 级 + 不变量
  伴件级证据（V1-V4），不再依赖 README 自述。
- **S+2**：子 Agent 工具覆盖（报告 R3）从"纯推测"升级为"有结构性证据"
  （V8 scope 继承），但**运行时证明仍缺席**，R3 维持未决。

## 四、裁定

1. **总体结论维持**：DSH 替换宿主可行、按 D1 同尺 3 分入围（Q1 yes / Q2 yes /
   Q3 yes / Q4 partial→0）、架构裁决对 DSH 有利、现行 OpenCode 路径阻断属实。
   修正 M1 不改变入围与裁决方向。
2. **报告按 M1 修订后方可被主仓决策记录引用**（Q1 证据面、S3/R2 风险表述两处）。
3. **spike 门禁（先行条件，任一失败即回退）**：
   - G1 插件加载：`dsh plugin --profile dsh-pilot add` 后 patch insert 行生效，
     运行指纹含新插件且无其他新增（对映 S1）；
   - G2 采集完整：host_event.v1 JSONL 覆盖五类事件且与轮操作对账一致（对映 S2），
     其中 `context_refs` 必须来自 **Session 派生历史**读取路径；
   - G3 最终输入可核验：派生历史 dump + `request/header` 对照证据（对映 S3，
     M1 修正后的形态）；若插件侧无公开派生历史读取面 → G3 失败 → 按
     log_tail_adapter_only 同款降级逻辑处理，不得硬做。
4. **程序性要求**：本裁定为 self-review；`dsh_primary` 决策记录（若立）应引用本
   裁定并注明待独立复核；独立复核在 spike 证据产出后进行。

## 附：本次复核新增的 file:line 证据清单

DSHAI\dsh-tools\lib\index.js:3225, 3417, 3504；DSHAI\dsh-tools\lib\invariant.js:10-87；
DSHAI\dsh-user-approval\lib\index.js:130-139；DSHAI\dsh-user-approval\lib\invariant.js:202-214；
DSHAI\dsh-compaction-basic\lib\index.js:469, 484, 634；
DSHAI\dsh-agent\lib\types\runtime-types.d.ts:92-99, 192-209, 300-310；
DSHAI\dsh-agent-loop\lib\index.js:902-925（preStep 全函数）, :907（systemPrompt.assemble 调用）。
