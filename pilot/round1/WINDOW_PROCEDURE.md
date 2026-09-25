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
  git_heads.json                 两臂 task-project 初始 git HEAD（嵌套隔离）
  clv0/task-project/             cl_v0 臂（布景 + git init + cl_install --init-cl）
  clv0/traces/                   CL 插件 trace（cl_turn 自动落盘）
  clv0/answers/turn_NNN.json     逐轮采集
  clv0/git_history.txt           场景结束导出（git log --all + status），随后删 .git
  baseline/task-project/         baseline 臂（布景 + git init，无 CL）
  baseline/summary_recovery.md   机械摘要（会话 2 用）
  baseline/answers/turn_NNN.json 逐轮采集
  baseline/git_history.txt       同上
  hashes/turn_NNN.json           每轮结束时的文件哈希快照（clv0 + baseline）
  delivery_check.json            会话 2 首轮 M3 投递核验记录
  BLOCKED.json / HALTED_clv0.json  场景停止 / clv0 臂停机终态（D'）
  run_log.json                   场景级步骤日志
```

CL 侧项目名约定：`round1_<scenario 短名>_clv0`（如 `round1_r1np_clv0`），
建于主仓 `graph/projects/` 下，随证据归档。**重跑用新目录 + 新 CL 项目名**
（第七号裁定 C'：污染运行不继承、不复用毒化状态，如
`round1_wr1rr2_clv0` + `runs/reassignment_recovery_v2/`）。

**嵌套 git 隔离（第七号裁定 C' 修订）**：每臂 task-project 布景时 `git init` +
初始提交（SEEDING §2.1），两臂 git 互相不可见；场景结束导出 git 史后删除嵌套
`.git`（SEEDING §2.2，避免外层仓 gitlink）。

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

**投递核验（机械，每场景一次，第六号裁定 M3）**：会话 2 首轮结束后，核验
`answers/turn_NNN.json` 记录的 user_text 包含 summary_recovery.md 全文（或至少
首行标记 + 全部 external_event 三元组）；不含 = 装置故障 → 按 §7-2 报阻塞，
该场景不得继续。（cmd.exe 吞 `>` 事件属投递层漏洞：check_info_floor 只检生成
文件、不检实际投递；摘要若再静默丢失将单向利多 CL——最危险偏置方向，故字节级
机械核验封口。）

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

- 宿主轮次：每次 opencode 调用计 1 轮（上限 300；原计划 72 + 试跑 8 = 80；
  第七号裁定后 = 已耗 61（含污染运行 33，归档不销账）+ 重跑 44 = 105/300）；
- DeepSeek 成本：cl_v0 臂每轮 1 次抽取调用（≈0.115 元/次，试跑实测口径），
  上限 50 元；累计 ≈6.1/50 元；每 5 轮在 `window_budget.json` 记一次累计估算
  （含 archived 口径：污染运行消耗计入总账）；
- 人工裁定：≤10 例，只用于 §5 规则的语义分类争议，逐例登记。

## 7. 失败处理

- 单轮 rc≠0 或超时：记录为该轮装置事件（answers JSON 如实留存），**不删轮、
  不静默重试**；同一轮重试 = 新轮次（轮次计数 +1，预算同记）；
- 任何 §7 验收项不过 / 装置异常：按封存令先报阻塞，不文字模拟结果；
- **D' 复发预案（第七号裁定，仅适用重跑场景 4）**：重跑中 clv0 臂再度停机
  （提取层失败可能系统性复发）→ 写 `HALTED_clv0.json` 终态、**不修复隔离条目、
  不强制续跑 clv0、不第三次重跑**；baseline 臂继续跑完全场景（干净嵌套 git 下
  两臂互不可见，纯采证补全，非不对称作弊）；双臂齐备检查点照封存 undeterminable
  规则进判断点（clv0 缺失的检查点剔除）；
- baseline 臂 rc≠0：仍按 §7-2 停场景报阻塞（D' 只覆盖 clv0 复发）。

## 7.1 嵌套 git 整改（第七号裁定 C'，装置层缺陷修复记录）

首轮窗口场景 4 因两臂 task-project 无嵌套 .git，第 5 轮 `git commit` 指令使两臂
作业落入宿主仓主历史（`5ec05ba`/`45c53f3`），clv0 t17 把他臂 HEAD 当本仓状态
引用——组间污染，场景作废归档（`archive/rr_polluted_20260924/`，审计见主仓
`round1_window_git_audit.md`）。整改：SEEDING §2.1/§2.2（每臂 git init + 初始提交、
收尾导出 git 史后清理嵌套 .git）；场景 1–3 经审计零 git 命中，数据成立。

## 8. 记录纪律（第六号裁定 §五）

- **全路径**：两个 `reassignment_recovery.json` 同名异径（`scenarios/` spec 与
  `pilot/round1/scenarios/` 转写稿）——窗口记录与结果登记一律写全路径；
- **种子基线分场景**：`seeds/r1_stale_test_result/` 布景 `pytest -q` = 3 failed
  （T1 基线）；`seeds/reassignment_recovery/` 布景 `pytest -q` = 3 passed（全通过
  基线）——报告与记录分开登记，不得混写。

## 9. 判断点仪器披露（预写，第六号裁定 M1/§四-3 + 第七号裁定 C'-5 增补）

- reassignment_recovery = **5 检查点（3 冻结 + 2 核定增补）**（008/014/017 冻结
  + s2_t12/s2_t20 增补，判分规则不变、两臂同题对称）；
- 结论按 criteria §9 三层格式，reassignment_recovery 固定标注"设计已见、运行未消耗"；
- 局限节必写：O1（首轮 read_states TypeError fail-open 伪影）、O2（readiness=degraded
  与图内容无关、仅 blocked 计拦截）、t17"（新决策，非回写历史）"括注的脚手架作用知悉；
- **第七号裁定增补披露（必写）**：
  (a) 装置层 git 组间污染缺陷及其整改（场景 4 首轮作废归档、每臂嵌套 git init 恢复
      P1/P2 先例、场景 1–3 零命中审计结论）；
  (b) 路径臂名自知（两臂 task-project 路径含臂名，P1/P2 以来一贯的已披露限制，
      非本次缺陷）；
  (c) readiness=degraded 持续全程（零 blocked 归因于图内容之外的固定降级）；
  (d) 拦截识别规则未获实测（全窗口零拦截案例，§5 规则无实证机会）；
  (e) 若重跑中 clv0 依 D' 停机：提取层停机段（t17 类 reconcile 3/3 连败 → 隔离 →
      readiness=blocked）与 clv0 缺失检查点（如 t20/t22 剔除）须在"未覆盖或不可判定
      路径"五要素中列明。

## 10. 扩样窗口附录（第八号裁定书授权，2026-09-25；装置版本钉 6c0302c）

**范围**：只补场景 4（reassignment_recovery）一格，双臂各 22 轮；场景 1–3 数据
不重采。判据 `b638e56`、预注册 `6ebbca4` 零改动；round1 已采证据全部有效。

**运行参数**：run_root 下新目录 `reassignment_recovery_v4/`；CL 项目名
`round1_wr1rr4_p1`（去臂名）；种子同 `seeds/reassignment_recovery/`；
每臂布景时 `git init` + 初始提交（C' 先例保持）。

**中性路径名（Round 2 前置 2）**：两臂落盘目录改为 `workspace-a`（cl_v0 逻辑臂）
/ `workspace-b`（baseline 逻辑臂）；运行目录内所有 JSON 件（seeding_manifest /
git_heads / hashes / HALTED.json / delivery_check）一律中性键；臂映射写驱动侧
`temp/round1_trial/arm_map_reassignment_recovery_v4.json`（不进运行目录）。
残余泄漏面（如实披露）：trace 文件名由 cl_turn 装置生成（随 CL 项目名中性化），
但模型若主动越目录窥探仍可能推断——与 round1 污染运行的跨臂窥探同型。

**拦截识别规则状态更新**：§5"未获实测"的限定已由**构造实测**解除（第八号裁定书
Round 2 前置 4）：scratch 项目 `round1_blocktest_p1`（隔离条目标 unreviewed 构造
readiness=blocked 真态）跑真 cl_turn，R1 宿主输出含
`CL_READINESS_BLOCKED: LINT_WARNING_PRESENT, QUARANTINE_NONEMPTY`、R2 trace 3 条
`cl_gate_verdict`（readiness=blocked）、R3 双证据齐备、R4 阻断前置（26.1s）。
证据：主仓 `temp/round1_judgment/blocktest/`。扩样窗口若出现自然拦截，仍按 §5
规则识别并人工核验一次（首例）。

**测量口径注记（必进扩样报告局限节）**：扩样 cl_v0 臂运行**修复后**提取层
（提示词 open→in_progress 互斥迁移补齐 + reconcile 错误回喂；主仓 6c0302c），
场景 1–3 运行修复前提取层；该缺陷在场景 1–3 未触发（reconcile 全过），修复为
contract 03 既有语义的提示词补齐，不改判定逻辑。readiness=degraded 恒置维持
（O2 根因：全局 lint 报告路径 + pilot 项目从未建 lint_baseline.json——一条他项目
陈旧 warning 让所有 pilot 项目恒降级；degraded 非阻断、构造实测证实 lint 不进
阻塞集；修复会動 assembler 核心件且改变测量条件，故文档化不修复）。

**预算延续**：宿主 91/300 起算 + 44 = 135/300；DeepSeek ≈6.45/50 起算
（56 次：36 live + 20 archived 含回归实证 2 + 拦截实测 1）+ 22 ≈ 78 次 ≈ 9.0/50；
人工裁定额度已用 1/10（D1），扩样段新争议另计。

**驱动与实测脚本快照（可复现性）**：扩样驱动 `tools/run_window_driver.py`
（sha256 `4302e9ecf8c6002e`）；装置测试脚本 `tools/fixreg_replay.py`
（`556358de09f39e28`，败链修复充分性实证）、`tools/blocktest_intercept.py`
（`48fdae68547c427e`，拦截识别规则实测）。三脚本与主仓 temp/round1_trial/ 工作件
同源；判据/评分器/五件套零改动（装置版本钉见主仓 round1_version_freeze.md §6）。
