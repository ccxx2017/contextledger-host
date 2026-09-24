# round1 正式窗口执行规程（WINDOW PROCEDURE）

> 正式窗口前装置事项 §5-2/3/4 的固化产物。本规程只编排**既有工具**（cl_install /
> cl_selfcheck / cl_turn / make_summary_recovery / check_info_floor / opencode.exe），
> 不新增装置代码、不改任何已提交装置件与冻结件。

## 1. 运行矩阵与顺序

| 序 | 场景 | 角色 | 回合 | 会话切分 |
|---|---|---|---|---|
| 1 | r1_normal_passage | 负对照 B | 4 | s1: 1–2 / s2: 3–4 |
| 2 | r1_unrelated_dimension | 负对照 A | 5 | s1: 1–3 / s2: 4–5 |
| 3 | r1_stale_test_result | 正例 | 5 | s1: 1–3 / s2: 4–5 |
| 4 | reassignment_recovery | 正例（预注册可执行化稿） | 22 | s1: 1–11 / s2: 12–22 |

每场景两臂（baseline / cl_v0），**同模型（glm-5.3-flash）、同 turns、同预算、同序**；
外部事件通知两臂都在会话 1 逐字同收（scripted_turns 的 user 原文即投递内容）。
合计宿主轮次 = 36×2 = 72（上限 300）。

## 2. 目录布局（每场景）

```
<run_root>/<scenario_id>/
  seeding_manifest.json          布景快照（两臂种子 sha256）
  clv0/task-project/             cl_v0 臂（布景 + cl_install --init-cl）
  clv0/traces/                   CL 插件 trace（cl_turn 自动落盘）
  clv0/answers/turn_NNN.json     逐轮采集
  baseline/task-project/         baseline 臂（仅布景，无 CL）
  baseline/summary_recovery.md   机械摘要（会话 2 用）
  baseline/answers/turn_NNN.json 逐轮采集
  hashes/turn_NNN.json           每轮结束时的文件哈希快照（clv0 + baseline）
```

CL 侧项目名约定：`round1_<scenario 短名>_clv0`（如 `round1_r1np_clv0`），
建于主仓 `graph/projects/` 下，随证据归档。

## 3. 每轮驱动命令

### cl_v0 臂（cl_turn.py，v0.1 五件套路径）

```
python tools/cl_turn.py --project <clv0/task-project> \
    --cl-project round1_<短名>_clv0 --text "<scripted_turns[i].user>" \
    [--new-session] [--timeout 420]
```

- 会话 1 第 1 轮与每会话首轮加 `--new-session`；其余轮默认（-c 续会话）；
- 安装：`python tools/cl_install.py --project <task-project> --cl-project <名> --init-cl`；
- 自检：`python tools/cl_selfcheck.py --project <task-project>` 必须 6/6 PASS。

### baseline 臂（opencode.exe 直调）

```
<opencode.exe> run [-c] "<text>"
```

- **必须直调底层 exe**（`C:\Users\Lenovo\AppData\Roaming\npm\node_modules\opencode-ai\bin\opencode.exe`）：
  opencode.CMD 包装器经 cmd.exe 的 `%*` 转发会吞掉含 `>` 的提示词（试跑实测，
  摘要模板的 markdown 引用行因此丢失导致模型收到空摘要）；
- 会话 1 第 1 轮与每会话首轮**不带** `-c`（新进程 = 新会话）；其余轮带 `-c`；
- **会话 2 首轮**的 text = 摘要注入块 + 本轮 scripted 原文：

```
【会话恢复摘要（约定恢复机制）】
<summary_recovery.md 全文>
【以上为恢复信息，以下是本轮任务】
<scripted_turns[i].user>
```

- 摘要须先经 `make_summary_recovery.py --scenario <场景> --out <路径>` 生成，
  再经 `check_info_floor.py --scenario <场景> --summary <路径>` 退出码 0 方可注入。

## 4. 每轮采集项（写入 answers/turn_NNN.json）

`arm / session / turn / new_session / user_text / cmd / rc / stdout / stderr / seconds`；
每轮结束对两臂 task-project 做文件哈希快照（hashes/turn_NNN.json）——文件级
改动判定以哈希差为据（git 非必需）。

## 5. 拦截的机械识别规则（§5-3，首例须人工核验）

cl-v0-inject.js 的阻断语义（读码确认）：**先发 `cl_gate_verdict` 事件，再抛错**
（`CL_READINESS_BLOCKED` / `CL_GATE_BLOCKED`）——verdict 载荷本身**不含**
blocked/decision 字段。因此机械识别规则为：

1. trace 中存在 `cl_gate_verdict`（readiness 或 preaction 关口）；**且**
2. 该轮宿主输出（stdout/stderr）出现 `CL_READINESS_BLOCKED` 或 `CL_GATE_BLOCKED`
   错误串，或对应工具调用未执行（答复中可见失败的工具调用）。

两条同时满足 → 记 1 次拦截（needless_block 分子，负对照场景下即为误拦）；
仅 verdict 无错误串 → 放行（readiness=degraded 不阻断，试跑实测 30 次裁定零阻断）。
**试跑零拦截案例，本规则未获实测——正式窗口首个拦截案例出现时必须人工核验
识别规则一次，核验记录随证据归档。**

## 6. 预算记账

- 宿主轮次：每次 opencode 调用计 1 轮（上限 300；本窗口 72 + 试跑 8 = 80）；
- DeepSeek 成本：cl_v0 臂每轮 1 次抽取调用（≈0.115 元/次，试跑实测口径），
  上限 50 元；每 5 轮在运行日志记一次累计估算；
- 人工裁定：≤10 例，只用于 §5 规则的语义分类争议，逐例登记。

## 7. 失败处理

- 单轮 rc≠0 或超时：记录为该轮装置事件（answers JSON 如实留存），**不删轮、
  不静默重试**；同一轮重试 = 新轮次（轮次计数 +1，预算同记）；
- 任何 §7 验收项不过 / 装置异常：按封存令先报阻塞，不文字模拟结果。
