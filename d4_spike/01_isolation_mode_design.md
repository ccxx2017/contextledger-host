# D4-spike 阶段 0：隔离与模式最小设计（§四.4.2）

- 日期：2026-10-05
- 前置：`00_interface_audit.md`（公开接口满足 S3，无停止条件）
- 本节只做设计 + 已核事实声明；实施证据留待阶段 1。

## 2.1 隔离维度逐项核对（钉扎版实际机制）

| 维度 | 机制事实（file:line / 实测） | 测试 profile 用法 | 残留共享与风险 |
|---|---|---|---|
| DshHome 数据根 | `%USERPROFILE%\.dsh`：`profiles/ sessions/ skills/ storages/ logs/ attachments/ llm-deepseek/`（本机实测列举）。日常 `web` profile 同根 | **无法按 profile 分根**：CLI 无 `--home` 开关实证。测试 profile 与日常 Web 同 home | sessions/storages/logs 在 home 层共享：测试会话若复用日常 sessionId 可串味；**对策：测试专用 session-id 前缀 + 独立 cwd + 采用前校验偏好** |
| profile 配置 | 每 profile 独立 pnpm workspace：`package.json`（bundles 层）+ `cordis.patch.yml`（用户补丁层）+ `cordis.yml`（[] 基座） | `dsh-pilot` profile 全新创建（`dsh plugin --profile dsh-pilot add <pkg>` 触发创建）；补丁只 `insert:` 不覆写 id | 日常 profile 文件零接触；**不修改 home 级任何补丁**（§3.8） |
| 补丁作用域 | 补丁在该 profile 组合内生效；bundle 层先于用户层 | 测试插件只在 dsh-pilot 的 cordis.patch.yml 出现 | 无跨 profile 泄漏通道 |
| session-id | headless：每次调用默认 fresh `session-<uuid>`；`--session-id` 采用时**拒绝**：无持久日志、跨 cwd、subagent/forked、预设不匹配、进程内已活（dsh-headless/README.md:54,145） | 测试会话用 `--session-id d4s-<n>`；日常会话 id 空间不重叠（前缀+不同 cwd 双保险） | cwd 是机器级隔离维度之一（见下） |
| workspace cwd | 工作目录经挂载 fs provider 解析（`fs.resolve('.')`/`fs.processPath()`），新会话记录该目录；采用时比对记录 cwd 不符即拒（同上 :54） | 测试专属目录 `<宿主仓>\pilot\dshtest\`（gitignored），绝不在日常工作目录跑测试 | AGENTS.md：测试项目自有 AGENTS.md 写入仅限测试目录（§3.8） |
| 缓存/日志/控制文件 | 会话日志 = DshHome `sessions/` 下持久 JSONL（home 层共享）；CL 控制文件放**测试项目目录内**（不落 home） | 控制文件 `pilot/dshtest/cl_control.json`；trace JSONL 落 `pilot/dshtest/traces/` | sessions 共享已由"专用 session-id 前缀+cwd 校拒"覆盖 |
| CL 项目绑定 | 绑定关系只存在于 CL 控制文件 + profile 补丁配置；不写 DSH 任何共享状态 | dsh-pilot patch 行 config: `{ clProject: "abu_modern_host_shadow", clHome: "D:/CCXXLESSON/contextledger", ... }` | 静默串项目风险由 §四.4.4 状态自检覆盖（每次注入前核项目名+版本） |
| 模型/计费 | profile 级 provider 行；日常 web profile 用 step-fun/step-5-preview 等自有行 | dsh-pilot **显式声明**模型路由行（不继承日常），便于成本归因 | 计费按 provider key 分账；本轮不共用日常 key 的话需用户授权（见 §2.4 预算栏） |

## 2.2 off / shadow / on 最小实现设计（§四.4.1）

**同一 Bundle、同一插件代码路径，模式由 profile 补丁行的一个 config 字段驱动**（`mode: off|shadow|on`，缺省 off——即未插入插件的日常 profile 天然 off）。

| 模式 | 实现位置与行为 | 保证 |
|---|---|---|
| `off` | 插件 apply() 读 `mode==='off'` → **不注册任何事件监听、不建 trace 文件句柄、不读 CL 目录**；只注册 `ctx.effect` 停机钩子 | 零 CL 行为：无采集、无抽取、无发布、无注入、无阻断（可被"off 跑一轮无任何 CL 文件产生"证明） |
| `shadow` | 注册只读监听：`agent/pre-step`（记新输入批次旁证，**不发 llm_call_start**）、`agent/request`（记该次请求配置）、`tools/pre-execute`（旁记决策输入）、`tools/post-execute`（旁记结果）、`tools/result`、以及会话事件观察（`compaction/*` 等，只读）。**所有发射都是旁证事件 type=`*_observed`，不得冒载执行语义**（§3.7）。产出签名核对：deriveMessages 摘要 vs 持久日志重建摘要 | 不改变模型输入（pre-step 一律 `await next()` 原样返回；post-execate 不加 additionalContexts）、不改工具决策（pre-execute 一律 allow） |
| `on` | 在 shadow 全部只读登记之上，加一个 `tools/post-execute` 的 `additionalContexts` 旁路**或** `agent.inject()`：把 CL 侧**已发布**的当前任务记忆（current_states.json + assembler_manifest）作为一条带来源 `UserMessage` 注入（"CL 任务记忆（机器装配）"标记，沿用 cl_common 渲染口径）。注入前核绑定项目名 + 发布版本；失败即显式降级提示，**绝不用其他项目记忆顶替** | 保留 DSH 原有全部机制（系统提示/历史/工具/压缩不动），CL 仅**追加**一条来源标识消息；不重开阻断关口（§3.2：本轮不含 pre-execute deny 路径） |

**"on"的准确边界（§四.4.1 末段）**：DSH 原有上下文管理 + CL 任务记忆补充。CL 注入的是"当前已发布任务记忆"这条追加消息，不是接管会话历史/系统提示/工具结果/压缩/请求组装。

**A/B 分离（§四.4.3）**：
- A（读取并注入已发布记忆）= on 模式插件的自动行为，触发时点 = 已验证的 `agent/pre-step` 装配后/请求派生前（每轮适用请求自动执行，无需用户逐轮启动）；
- B（从新对话采集→抽取→裁定→发布）= **不由插件自动执行**。本轮更新链用既有受控 runner 手动触发（`tools/cl_turn.py` 的 DSH 变体 + `pilot_turn_driver.py`），
  遇到待裁定项（pending_merge/人工裁定边界）即停，不代替用户裁定。on 模式**只**含 A。

**自动加载（§四.4.3）**：插件经 profile 组合常驻装载，无额外常驻进程；headless 单次调用进程内完成"装载→监听→退出"，生命周期归 DSH 进程自身。

## 2.3 可见状态与失效处理（§四.4.4）

- 插件启动时（apply）与每次注入时向 stderr 写一行业务状态行（`dsh: cl-seam:` 前缀）：
  `mode=<off|shadow|on> profile=<name> session=<id> cwd=<path> clProject=<名|未绑定> lastInjectedRevision=<rev|尚未注入> gate=OFF extractTrigger=<手动 runner 命令> status=<ok|degraded|failed>`
- 失败显式化：控制文件缺失/绑定项目不符/记忆读取失败/版本为空 → 状态行 `status=degraded` 且
  **本步不注入**（不静默跳过、不顶替、不谎报版本）。
- 降级策略：`on` 注入失败 → 该请求按 DSH 原生上下文继续（不阻断用户任务），状态行留痕。
  降级绝不触碰 DSH 安全审批（§3.3）。

## 2.4 开关与回退语义（§四.4.5）

- 生效边界：**选择模式 = 选择 profile**，模式在新会话首拍生效（本轮不做运行中无痕热切换，§四.4.5 允许的最小方案）。
- off 之后：不新增 CL 行为；**同一会话历史中已注入的 CL 内容不保证消失**——操作说明写明；
  干净新会话 = 不带 profile 或换日常 profile + 新 sessionId 启动。
- 回退 = 回到日常 profile/入口；测试插件停用 = 删 dsh-pilot profile 的 insert 行（保留包安装物
  与 git 历史），或直接 `git revert` 对应提交。

## 2.5 成本估计与 LLM 预算（§三.9）

本轮**所有真实 LLM 调用预算未由用户填写**（原任务模板 `[N]`/`[X]` 为空）。
按 §三.9 纪律：**未填写预算不得发起真实调用**。

阶段 0/1/2 的设计与离线核对阶段预算为 **0 次真实 LLM 调用**（模式骨架与隔离检查可用
"不装 provider 的组合装配失败即报错"或最小请求不发生的路径验证——loader 加载/补Patch生效/
off 零 CL 文件，均不需要模型回答）。拆分为：

| 阶段 | 预计真实 LLM 调用 | 说明 |
|---|---|---|
| 阶段 0（本阶段） | 0 | 纯文档 + 只读核对 |
| 阶段 1 | 0 起步（骨架+隔离+语义发射自检可用 dry 模式）；reassignment_recovery 复跑与 S1–S3 取证**需预算批准** | 若用户批准小预算（建议 N=6 封顶：2 轮 shadow × 2 个 turn + 1 次对照 + 1 次独立复跑预留），将列明预计用途后执行 |
| 阶段 2 | 依赖阶段 1 裁定 | 同上 |
| 阶段 3/4 | 依赖前两阶段 | G4 真实抽取预算单列报批 |

**每阶段汇报列明：本阶段/累计真实调用次数、用途分解（宿主模型调用 / CL 抽取调用 / 其他）、费用估算。**

## 2.6 本阶段 git 提交映射（§三.10）

- 宿主仓 `d4-spike-minimal-migration` 分支：
  - `4fe1f30` 可行性报告+裁定书归档（d4_spike 输入）；
  - 阶段 0 末提交：报告 §5 M1 对齐修正 + `00_interface_audit.md` + `01_isolation_mode_design.md`。
- 主仓：阶段 0 无新增（建议记录留待阶段 4，按 §五.4 不自行写决策）。
