# 归档说明：v2 尝试（超时误判，未产出判定数据）

> 归档时间：2026-09-24 22:0x ｜ 依据：§7 装置事件记录纪律（不删轮、不静默重试）
> 本目录 = C' 重跑的**第一次尝试**，因驱动缺陷分类错误而中止；**无任何轮次进入判定机械**。

## 发生了什么

1. 布景成功：两臂种子同源，**每臂嵌套 git init 成功**（clv0/baseline 初始 HEAD 均为
   `f96f4e1`——git 隔离整改生效），cl_install/selfcheck 6/6、摘要与信息量下限全过；
2. clv0 t1 **宿主会话 420s 超时**（rc=1，510.8s；首轮同轮在污染运行中为 260.7s——
   模型时延波动，非系统性故障）；
3. 驱动把**任何** clv0 rc≠0 一律按 D'（提取层复发预案）处置 → 误写 HALTED_clv0.json
   并转 baseline-only。**D' 的适用范围是提取层失败（reconcile/隔离），不含超时**——
   超时按 §7 属装置事件，重试算新轮次（预算同记）；
4. 执行方发现后即停驱动（baseline t1 被中断，无答案落盘），归档本目录，修驱动后重开。

## 本目录保留的证据

- `clv0/answers/turn_001.json`：超时轮完整记录（rc=1、510.8s、TimeoutExpired 栈）；
- `HALTED_clv0.json`：误判产物（保留以记录缺陷本身）；
- `git_heads.json`：两臂嵌套 git 初始 HEAD（整改生效的实证）；
- `seeding_manifest.json`、两臂 task-project（布景态 + clv0 的 .opencode 装置）、
  trace（turn_0000：仅装配/注入事件，宿主未产出即超时）；
- `*/git_history.txt`：两臂内嵌 git 史导出（各 1 行种子提交）后已清理嵌套 .git。

## 预算计入

本尝试共发生 **2 次 opencode 调用**（clv0 t1 超时 510.8s；baseline t1 被驱动停止时
已运行 186s、无答案落盘）、**0 次完成的抽取**（clv0 宿主超时发生在 CL 抽取之前）。
已计入 window_budget.json 的 archived 口径（host_turns 35 = 污染运行 33 + 本尝试 2；
extractions 17 = 污染运行 17 + 0）。

> **更正（第八号裁定书 §6-3，2026-09-25）**：本注记原句"重跑 44 轮后总账 =
> 28 + 35 + 44 = 107/300"系 v3 开跑**前**的投影（v3 按满 44 轮双臂预算）。
> v3 实际为 baseline 22/22 + clv0 3 轮（t3 停机）= 28 轮（live 56 = 场景 1–3 28 +
> v3 28），**实际总账 91/300**（live 56 + archived 35），全账抽取 53 次 ≈6.1/50 元。
> 以 `window_budget.json` 为准；原投影句保留以记录预算口径的演进，不删除。

## 后续

驱动修复：失败三分类（超时 → §7 重试路径（新轮次计预算）；reconcile/QUARANTINE →
D' 停机终态；其他 rc≠0 → 停场景报阻塞）。重开运行：
`--run-name reassignment_recovery_v3 --cl-suffix 3`（新目录 + 新 CL 项目
`round1_wr1rr3_clv0`，不继承任何毒化/超时状态）。
