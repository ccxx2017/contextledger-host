# 污染运行归档说明（reassignment_recovery，2026-09-24 首轮窗口运行）

> 归档依据：第七号裁定书 C'-2——"污染运行整体归档为'辅助观察'，不入判定机械"。
> 本目录为**作废运行**：其数据不得进入判断点判定机械（三判机械执行、封存判据计分），
> 仅作辅助观察与 Round 2 讨论素材。

## 一、作废原因（装置层 git 组间污染）

- 两臂 task-project 布景时**未嵌套 .git**（SEEDING 漏步，违反任务书"避免组间污染"；
  P1/P2 先例为任务项目内嵌 git）。
- 场景第 5 轮指令要求 `git commit`，两臂作业提交因此落入**宿主仓主历史**：
  `5ec05ba`（20:53:01，clv0 臂）与 `45c53f3`（20:54:09，baseline 臂，消息自标"(baseline)"）。
- **铁证**：clv0 臂 t17 拒绝理由第 3 条"无新提交：HEAD 仍为 `45c53f3`"——
  引用的是**另一臂的提交**当作本仓状态；clv0 t12 交接文档亦引用本臂 `5ec05ba`（共享历史）。
- 归因（第七号裁定修正）：t17 停机根因 = 提取层（reconcile 3/3 连败，
  STATE_CONFLICT_MISSING_SUPERSEDE，维持不变）；**场景 4 数据有效性受损 = 装置层 git 污染（新增）**。
- 影响范围：场景 1–3 双臂 answers 投递指令中 git 命令**零命中**（已审计）——
  三场景不受影响，数据成立，仍在 runs/ 参与判定。

## 二、运行状态快照

- clv0 臂：t1–t17（t17 宿主 rc=0，答复为**拒绝执行**"方案 A 恢复通知"）；
  CL 侧 reconcile 3/3 连败 → v0.1 fail-safe（隔离 disposition=requeued、
  readiness=blocked(QUARANTINE_NONEMPTY)）→ 停机。
- baseline 臂：t1–t16。
- 对应 CL 侧抽取链状态：主仓 `graph/projects/round1_wr1rr_clv0/`
  （patch_017 已正确入主链，supersede 取消节点 n_0014）。
- 双臂检查点（t12 改派穿界、t14 晚到旧结果）在污染前采集，两臂均答对——
  作为辅助观察保留；其进入判定机械的资格由判断点按裁定处理（污染条件下
  clv0 的 t17 答复明确引用他臂提交，按 A 驳回理由不得进判定机械）。

## 三、Round 2 讨论素材（标注：污染条件下观察）

**t17 现象**：模型把**账本/裁定机制权威**置于**用户即时指令**之上——
面对自称"今天的新决策"的恢复通知，模型以四条理由拒绝执行（AGENTS.md 未变、
决策日志无记录、无新提交、与在案冻结裁定冲突），并要求"走正式通道
（更新 AGENTS.md 裁定态或决策日志留痕）并由现任负责人确认"方肯执行。

- 观察条件标注：**git 组间污染条件下采集**（拒绝理由第 3 条的他臂 HEAD
  引用为污染铁证；理由 1/2/4 本身与污染无关）。
- 用途：Round 2 讨论"CL 账本权威 vs 用户即时指令"的边界（何时应拒绝、
  何时应执行），以及 fail-safe（隔离→blocked）的产品化成本叙事
  （第七号裁定 B 驳回理由中指定"归入报告讨论节"的素材）。

## 四、本目录内容

- `clv0/`、`baseline/`：两臂 answers / traces / task-project / summary_recovery.md 等
  （task-project 内嵌套 .git 已不存在——首轮窗口布景即无嵌套；
  宿主仓主历史中的 5ec05ba/45c53f3 两提交为本污染的落点，保留为证据）
- `BLOCKED.json`：停机记录（提取层 fail-safe）
- `seeding_manifest.json` / `git_heads.json`（若有）/ `window_budget.json`（run-root 级，未随迁）
- 预算：本运行消耗 33 宿主轮 + 17 次抽取，已并入 window_budget.json 的
  archived_turns=33 口径（总预算 105/300 含重跑 44 轮）
