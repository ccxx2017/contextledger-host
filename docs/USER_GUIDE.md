# CL v0.1 用户指南（试用版）

适用：opencode 1.18.29 + Windows + Python 3.9+。试用范围：单会话/多会话主任务，
单目录项目。**不覆盖**：子 Agent、后台路径、请求级上下文接管（v0.1 供给走 AGENTS.md 文件通道）。

## 一、安装（3 分钟）

```bash
cd D:/CCXXLESSON/contextledger-host
python tools/cl_install.py --project <你的项目目录> --cl-project <CL项目名，新取一个>
python tools/cl_selfcheck.py --project <你的项目目录>
```

自检 6 项全 PASS 即安装成功。任何 FAIL 按提示修复后重跑。
（安装会备份你已有的 AGENTS.md 到 `.opencode/backup/`。）

CL 侧初始化（首次）：

```bash
cd D:/CCXXLESSON/contextledger
mkdir -p graph/projects/<CL项目名>/run graph/projects/<CL项目名>/patches raw/projects/<CL项目名>/s001
printf '%s' '{"turn_counter": 0, "nodes": {}, "edges": []}' > graph/projects/<CL项目名>/graph_state.seed.json
```

## 二、日常使用

每轮任务一条命令（装配刷新 → 宿主执行 → CL 裁定入库，全自动）：

```bash
python tools/cl_turn.py --project <你的项目目录> --cl-project <CL项目名> --text "<本轮任务>"
```

- **AGENTS.md** 会被 CL 自动维护（当前裁定状态 + 就绪度 + 版本）。它就是 CL 告诉
  Agent 的"当前什么成立"；与其冲突的早期记忆以它为准。
- **门控行为**：装配依据过期（宿主知识落后于 CL 裁定）或就绪度 blocked 时，
  Agent 的工具调用会被拦截，错误信息含原因码与恢复指引。这是设计行为，不是故障。
- **被拦后怎么办**：按错误提示处理——通常等待 CL 裁定完成（隔离条目）或确认装配刷新，
  然后重试。Agent 自己也会执行该恢复流程。

### 2.1 参数详解

```bash
python tools/cl_turn.py --project . --cl-project my_trial --text "你这轮的任务描述"
```

| 参数 | 含义 |
|---|---|
| `--project .` | **Agent 干活的项目目录**。也是插件（`.opencode/plugin/`）和 AGENTS.md 所在地。`.` = 当前目录 |
| `--cl-project my_trial` | **CL 账本名**。裁定后的状态存在 CL 主仓库 `graph/projects/my_trial/` 下，与别的项目隔离。同一个项目每次用同一个名字，账本连续累积；换新项目换新名字 |
| `--text "..."` | **本轮你对 Agent 说的话**（用户消息） |
| `--turn N` | 轮次号（缺省自动 +1，存于 `.opencode/cl_turn_state.json`） |
| `--new-session` | 强制新会话（见 2.3） |
| `--timeout 420` | 宿主会话超时秒数（端点偶发挂起时自动结束，重跑即可） |

**插件加载由目录决定，与 git 分支无关**：插件装在哪个项目目录，就在那个目录里启动
opencode 才生效；切分支不影响（文件在工作区就在）。

### 2.2 会话续接（-c 自动机制）

`cl_turn.py` 默认自动带 `-c`（续接该项目上一次会话）——Agent 记得之前所有对话和操作：

```bash
# 第 1 轮：新会话
python tools/cl_turn.py --project . --cl-project my_trial --text "任务启动：重构 calc.py"
# 第 2、3、4 轮：自动续接同一会话，Agent 记得前面所有事
python tools/cl_turn.py --project . --cl-project my_trial --text "继续：补测试"
```

只有想**故意失忆**时才加 `--new-session`（新会话从零开始）——测"跨会话记忆丢失"或
开启全新独立任务时使用。

### 2.3 每轮哪些内容进入 CL（数据边界）

一轮的完整数据流：

```
cl_turn.py --text "继续：给 calc.py 补测试"
   ├─ ① 装配刷新：AGENTS.md / 控制文件更新到 CL 最新裁定态
   ├─ ② opencode run -c "<text>"     ← Agent 自主调工具、生成答复（会话内记得）
   ├─ ③ 插件把工具调用留痕到 trace（工具名 + 参数）
   └─ ④ CL 驱动组装本轮 raw：
         【本轮时间】…
         【用户】继续：给 calc.py 补测试
         【本轮工具活动摘要】
         - 工具调用 write: {"filePath": ".../test_calc.py", ...}
      → DeepSeek 抽取 → 裁定入库 → AGENTS.md 刷新
```

| 内容 | 是否进入 CL | 形式 |
|---|---|---|
| 你说的话（--text） | ✅ | 原文 |
| Agent 的工具调用 | ✅ | 工具名 + 参数摘要（每条 200 字符） |
| Agent 的文字反馈 | ❌ | 设计如此：raw 只收"用户说了什么 + 客观工具痕迹"，不把 Agent 自我叙述当事实源 |
| Agent 的任务记忆 | 不经 CL | `-c` 续接的会话内 Agent 自己记得；CL 补充的是裁定过的状态层（AGENTS.md） |

### 2.4 三种使用方式与能力边界

| 方式 | 门控 | 观察（trace） | AGENTS.md 供给 | CL 裁定入库 | 适用 |
|---|---|---|---|---|---|
| **cl_turn.py**（推荐） | ✅ | ✅ | ✅ 自动 | ✅ 自动 | 日常任务；v0.1 主推 |
| **TUI 交互式**（项目目录内直接 `opencode`） | ✅ | ✅ | ⚠️ 会话内即时重读未单独实测（`run -c` 续接已实测生效） | ❌ 需手动跑驱动器 | 习惯交互式的用户 |
| **裸 opencode**（其他目录） | ❌ | ❌ | ❌ | ❌ | 对照 / 不想用 CL 时 |

TUI 交互式的完整用法：项目目录内 `opencode` 正常对话（门控+观察生效）；对话告一段落后，
在另一终端跑一次驱动器入库刷新：

```bash
python D:/CCXXLESSON/contextledger/graph/scripts/pilot_turn_driver.py \
  --cl-project my_trial --turn-num 1 --user-text "刚才的任务概要" \
  --control-file <项目>/.opencode/cl_v0.json --agents-md <项目>/AGENTS.md \
  --env-file D:/CCXXLESSON/contextledger/env
```

验证供给是否生效的最简单方法：新会话里问 Agent "AGENTS.md 里的 CL-PILOT-STATE
列了哪些状态？"——答得出来即通道正常。

## 三、故障排查

| 现象 | 处理 |
|---|---|
| Agent 说被 CL_GATE_BLOCKED / STATE_REVISION_STALE 拦截 | 正常拦截。重新装配：`cl_turn.py` 下一轮会自动刷新；紧急放行见下方停用 |
| Agent 说 CL_READINESS_BLOCKED | 存在未裁定隔离条目。裁定：`python tools/cl_recover.py --project ... --cl-project ... --issue quarantine` |
| AGENTS.md 丢失/损坏 | `python tools/cl_recover.py ... --issue agents_md` |
| 控制文件损坏 | `python tools/cl_recover.py ... --issue control_file` |
| trace 里出现 cl_gate_error | 关口异常放行（fail-open），动作未被拦。请把该 trace 提交开发者 |

所有异常的 trace 在 `CL_SHADOW_TRACE` 指向的 JSONL；完整策略见
`docs/GATE_EXCEPTION_POLICY.md`；恢复规程见 `docs/RECOVERY.md`。

## 四、停用恢复

```bash
python tools/cl_disable.py --project <你的项目目录>
```

移除插件与控制文件、还原装前的 AGENTS.md（备份在 `.opencode/backup/`）。
宿主立即回到装前状态；CL 侧历史数据保留在 CL 主仓库，随时可重装。

## 五、试用验收清单（请在你的可回滚项目中执行）

1. 按本文档从零安装，自检 6/6 PASS
2. 完成一轮真实小任务（≥3 轮对话），确认 AGENTS.md 被自动维护
3. 中途人工制造一次状态反转（如"取消刚才的做法"），确认后续轮次 Agent
   以 CL 当前态为准（可对照 `traces/` 的 cl_v0_boundary_dump）
4. 确认门控：手动把 `.opencode/cl_v0.json` 的 expected_state_revision 改成旧值，
   观察 Agent 动作被拦、文件未被改动；改回后恢复
5. 按第四节停用，确认 AGENTS.md 还原、插件移除、项目行为与装前一致

验收通过/问题请记录（含 trace 文件），提交给开发者。

## 六、试用记录与使用报告（cl_report.py，v0.1 新增）

CL 在试用全程**自动留痕**，你无需干预：

| 侧 | 位置 | 内容 |
|---|---|---|
| 项目侧 | `traces/<CL项目名>_turn_NNNN.jsonl` | 注入/边界/门控事件（cl_v0_injected、cl_v0_boundary_dump、cl_gate_verdict、cl_v0_error） |
| 项目侧 | `.opencode/cl_turn_state.json` | 轮次计数 |
| CL 侧 | `graph/projects/<CL项目名>/` | 每轮 patch、`run/` 当前态与 manifest、`reports/` 抽取留痕与成本 meta |

试用结束生成报告（一条命令）：

```bash
python tools/cl_report.py --project <你的项目目录>
# 输出：<你的项目目录>/usage_report.md
```

报告含：版本钉（两仓 commit）、轮次总览（用户输入/抽取次数/工具调用/拦截/readiness/异常）、账本动作与状态迁转、供给面终态、注入与边界记录、异常与缺口、成本估算、空白裁定区（供指导员/裁定方填写）。本报告为**机械聚合，不做价值判定**。

**记录口径三要点（须知）**：

1. **工具调用记录依赖 `gate=true`**：插件只在门控开启时经 `tool.execute.before` 记录工具名（不含参数）；默认 `gate=false` 下 trace 只有注入/边界事件。若本次试用需要"实施行为"级记录，试用期间把 `.opencode/cl_v0.json` 的 `"gate"` 置 `true`——注意这是**真实行为变化**（readiness=blocked 或装配过期会真实拦截动作；round1 全部窗口实测 150 条 verdict 0 次拦截，一般只增记录不增阻碍，但请知情后自行决定）；
2. 已知缺口（装置属性）：CL raw 的"本轮工具活动摘要"用旧事件格式解析，用户路径下可能为空——不影响 `cl_report.py`（工具数直接来自 trace 解析）；
3. 装后未先跑 `cl_turn.py` 就直接开会话时，trace 可能出现 `read_states` fail-open error——无害，先跑一轮 cl_turn 即消失。
