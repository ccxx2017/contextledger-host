# D4-spike 阶段 0：接口核对表（钉扎 0.2.0-rc.2）

- 日期：2026-10-05
- 钉扎物：`@deepseek-ai/dsh@0.2.0-rc.2`（本机 `lib/bin.js --version` 实证）
- 路径缩写 **DSHAI** = `C:\Users\Lenovo\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\`
- 核对方法：**只读随包 `lib/*.js` 与 `lib/types/*.d.ts`**（§3.6 允许阅读核对；
  运行接入只用公开接口）。所有结论附 file:line。

## 0.1 §五.阶段0 第 2 项逐条

| # | 核对项 | 结论 | file:line 证据（DSHAI 下相对路径） |
|---|---|---|---|
| I1 | `agent/pre-step` | 瀑布线存在；载荷 = **本步新领取输入批次** `messages: UserMessage[]` + `turn/step/signal`；决策 = reject 或 enter{messages, startsRequestSeries?}。**不是全量最终输入**（M1 已裁） | dsh-agent-loop/lib/index.js:911-918（`messages: claimed`）；dsh-agent/lib/types/runtime-types.d.ts:92-99、304-310 |
| I2 | 请求组装、派生与冻结位置 | 组装链：`prepareRequest()` 1162-1200（`agent/request` 瀑布线取 provider/model/reasoningEffort/maxTokens：1180；`ctx.llm.prepareCall()`：1189）→ `buildRequest()` 1201-1277（`request/header` 持久化：1214-1228；工具增删 `developer/message`：1240-1247；`request/context`：1259；**`session.deriveMessages()`：1262**；逐消息 deepFreeze：1263-1267；`toolHistory`：1272；`tools: header.tools`：1273；`sessionId`：1274；整体 `Object.freeze` 并打 `markAgentLoopRequest`：1269-1276） | dsh-agent-loop/lib/index.js:1162-1277 |
| I3 | Session 派生历史公开读取面 | **`deriveMessages(): Message[]`**（缓存深冻投影，每次返新数组）；`requestHeader(): EpochHeader \| undefined`；`toolHistory(): ToolHistory`；`get surface(): SessionSurface`。派生历史**已含系统提示**（README:174："系统提示词仍属于 deriveMessages()；请求头事件不添加消息或提示词副本"） | dsh-session/lib/types/index.d.ts:303、259、278、110；dsh-session/README.md:42、116、174 |
| I4 | 系统提示、模型路由、请求关联标识取得方式 | 系统提示：`ctx.systemPrompt.assemble(context)` 于 pre-step 阶段调用（lib:907），公开服务 `SystemPrompt`（section/variable/assemble/getSectionOrder/getContextOrder/suppressRuntimeContext）；路由：`agent/request` 瀑布线 + prepareCall；关联标识：`sessionId`（lib:1274）+ `session.append(..., {surfaceOp})` 的持久 seq + `request/header` 的 headerSeq。`agent/request` 缺省 seed 为持久头部投影（lib:1174） | dsh-system-prompt/lib/types/index.d.ts:27、239、245、251、282、292；dsh-agent-loop/lib/index.js:907、1179-1184、1274 |
| I5 | `tools/pre-execute` 组合顺序 | 固定管线：`tools/pre-execate`（可扩展 allow/deny/ask）→ 单调 guards → `tools/execute`（环绕）→ `tools/post-execute`（accept/block + additionalContexts）→ `finalizeContent` → `tools/result`（只读）。不变量伴件强制顺序与冻结 | dsh-tools/lib/index.js:3225、3504、3417；dsh-tools/lib/invariant.js:10-87 |
| I6 | pre-execute 与 `ctx.tools.guard()` 的保证差别 | 瀑布线按序决策（后拍可覆盖先拍，但 deny 一旦给出不可翻盘——README:85 语义装在 Guide：实际 lib 内 `guard` 在 waterfall 之后同步执行，单调：guard 拒绝后无监听器可翻）；`pre-execate` 可 deny/ask/allow，**不可改参数**（:230 有意设计）；`guard` 是同步单调补强，不经 ask | dsh-tools/lib/index.js:2912（guard 注册于 pre-execute 之后）、3225；dsh-tools/README.md:85、138、230 |
| I7 | `ctx.approval` | 服务键 `approval`；`request(req)` 只在 open turn 内有效；answerer = `approval/request` 瀑布线，缺省解析 `unavailable`（fail-closed）；`setPolicy(agent, policy)` 切换并广播；审计对 `approval/asked`+`approval/decined` 持久化且不变量校验配对 | dsh-user-approval/lib/index.js:72-75、130-139、176；lib/types/index.d.ts:105-135；lib/invariant.js:202-214 |
| I8 | Loader / profile / 补丁作用域 / 隔离机制 | Profile = pnpm workspace 根（`package.json` 的 `dsh.profile.bundles` 列 bundle 层 + `cordis.patch.yml` 用户补丁层 + `cordis.yml` 空基座）；CLI 安装入口 `dsh plugin --profile <name> add <package>`（CLI 报错信息实证）；补丁新增必须 `insert:` 且不写 id；DshHome 级数据根 `%USERPROFILE%\.dsh`（profiles/sessions/skills/storages/logs/attachments） | ~/.dsh/profiles/web/{package.json,cordis.patch.yml,cordis.yml}；本机 dsh CLI 报错文案；宿主仓既有 web profile 实际文件 |
| I9 | 服务键名（插件 inject 可用） | `agents`、`sessions`、`llm`、`tools`、`systemPrompt`、`approval`、`sessionProjections`、`invariants`、`shell`。以各包 `static inject` 为权威 | dsh-agent-loop/lib/index.js:1524-1531；dsh-tools/lib/index.js:2664；dsh-user-approal/lib/invariant.js:199 |

## 0.2 "完整请求依据"证据范围（§五.0.3）—— S3 在 DSH 的正解

**结论：公开接口可取到与实际发出的每次请求完整对应的依据，无需私有接口、无需宿主补丁。**

一次实际模型调用 = 以下四件的确定组合，且均在插件公开可达面：

1. **消息历史（含系统提示）**：`Session.deriveMessages()`（I3）—— loop 在派发前夕对同一数组逐消息 deepFreeze 并整体 freeze 后交给 llm
   （lib:1262-1276）。插件在同一 turn/step 的 `agent/pre-step`→emit 后即可调 `session.deriveMessages()` 取当次依据；
2. **请求配置/模型路由**：`Session.requestHeader()`（I3）+ `agent/request` 瀑布线 payload（provider/model/reasoningEffort/maxTokens，lib:1180）+ prepareCall 派生（adapterDefaults/systemPromptUpdate，lib:1189）；
3. **工具面**：`Session.toolHistory()`（I3，lib:1272 即用此值）；
4. **关联标识**：`sessionId`（lib:1274）+ turn/step + 持久事件 seq（插件侧 append 的旁证事件可与之并排）。

**关联方法（spike 取证设计）**：shadow 插件在 `agent/pre-step`（本步新输入）与 `agent/request`（该次请求配置解析）两个时点各记一条旁证事件，载荷含 turn/step/sessionId + `requestHeader()` 快照 + `deriveMessages()` 的**长度+sha256+逐条 role/id 摘要**（不落全量正文，控成本）；因 derive 是确定性投影（缓存深冻），实际请求发出后的日志重建可与旁证逐字节对齐。

**S3 对"最终输入"的适配器层差异（显式列出，§五.0.3 要求）**：

| 差异 | OpenCode 1.18.29 | DSH 0.2.0-rc.2 | 对等处理 |
|---|---|---|---|
| 单点 transform | `experimental.chat.messages.transform` 见最终 messages 数组 | **无单点 transform**；`agent/pre-step` 只见新领取批次 | 用 deriveMessages() 取全量；pre-step 仅作时点标记 |
| 系统提示载体 | `experimental.chat.system.transform` 的 output.system 数组 | 系统提示是 deriveMessages() 中的 system 节点（表面消息），非 wire 字段 | dump 时按 role=system 节点提取并单独标注 |
| CL 注入位置变异 | 追加/就地震写 user part（脆弱，曾被丢弃） | 注入 = 以 `agent.inject()` 或 pre-step enter 批次追加带来源 `UserMessage`（一等公民） | 注入即新消息，不复写历史；版本以消息来源标识 |
| 请求冻结证明 | 无（插件侧无法证明 wire 冻结） | loop 对 derive 数组 + 消息逐条 deepFreeze 后才 dispatch（lib:1262-1276） | dump 侧无需自证；日志重建对齐 |

## 0.3 停止条件结论（§五.0 末）

- 公开接口**满足**原 S3（经由 0.2 四件组合），**不触发**停止条件；
- 无任何一项承重结论依赖私有接口或宿主补丁；
- 遗留核对项（不阻塞阶段 1，但进 spike 取证）：`deriveMessages()` 在**多变体消息/替换**后的缓存失效语义是否与 loop 所见严格一致（同源同函数，理论自洽；运行时以"旁证摘要 vs 日志重建摘要"对账证明）。

## 0.4 勘误（2026-10-08，依据阶段 1 运行时证据 + 安装物复核）

以下三条阶段 0 表述经运行时证据证伪或修正：

1. **L29-30 "pre-step→emit 后即可调 deriveMessages() 取当次依据"** —— 不成立。
   实测（on 模式注入 run，session-58b6d403，step-2）：pre-step 领取批次含被注入记忆
   （premise 旁证 context_refs/批次摘要可证），但随后 `agent/request` 时点的
   `deriveMessages()` **不含该刚领取消息**（derived=5 无记忆消息）。
   修正：`deriveMessages()` 在瀑布时点是"会话已提交视图"，**不含本步刚领取的收件箱消息**；
   完整请求依据 = **派生摘要 + 本步领取批次（premise 旁证）两份合并**。
2. **L35 "日志重建可与旁证逐字节对齐"** —— 限定收窄：对齐仅对"派生部分"成立；
   领取批次部分由 premise 旁证单独承载，两份不得互相替代，也不能预设二者相加即完整
   （需在验证 run 中以消息 ID/指纹对账，见 04_supply_design_v3.md §4）。
3. **L41 "用 deriveMessages() 取全量；pre-step 仅作时点标记"** —— 修正为：
   pre-step 的领取批次记录（premise 旁证）是请求依据的**必要组成**，非仅时点标记。

另：`systemPromptUpdate` 经复核为**模型能力声明**（`dsh-llm/lib/types/types.d.ts:365`，
`type SystemPromptUpdate = 'in-history'`，见 `LlmResolvedModelInfo` L385"Declared mid-conversation
system prompt handling"），**不是内容更新接口**——阶段 0 未将其列为供给通道，此处正式记笔，
防止后续误用。
