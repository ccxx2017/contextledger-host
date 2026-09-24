# pilot/round1 — round1 双臂对照评测装置（DRAFT，待预注册批准后启用）

> 依据：`temp/CL试用评测行动计划_v1.md`（v1.1）+ `temp/CL试用评测行动计划_v1_复核裁定.md`
> 边界：本目录及其子目录是宿主仓唯一的新增物落点（裁定书批准事项 1-b）；
> 不动已封存的 p1/p2/s4/s5/s6/v01 目录。判据封存（用户批准预注册文本）之前，
> 本装置只可做装置自检，不得进入正式评测窗口。

## 目录

- `scenarios/` — 三个 round1 场景（pilot_scenario.v1 + round1_registration 六要素块）：
  - `r1_unrelated_dimension.json` — 负对照A：无关维度变化，不应触发失效/误拦；
  - `r1_normal_passage.json` — 负对照B：正常通行，全程零拦截（假阳性零容忍直测）；
  - `r1_stale_test_result.json` — 正例：旧测试结果失效，不得作为当前诊断依据。
  - （复用既有正例场景：宿主仓 `scenarios/reassignment_recovery.json`——预注册
    22 轮成对运行场景，尚未消耗，round1 可作第 4 个场景；`scenarios/p1_cancellation_late.json`
    与 `p2_reassignment_recovery.json` 已被 P1/P2 消耗，只作历史证据。）
- `tools/make_summary_recovery.py` — baseline 臂"约定的摘要恢复"机械生成器
  （模板 r1_summary_template_v1，全文冻结于主仓 round1_preregistration.json）；
- `tools/check_info_floor.py` — 信息量下限机械检查（裁定补强①：事件三元组
  逐字出现 + 逐轮记录齐全 + 无泄判关键词；不过即对照无效、不得开跑）。

## 臂定义（round1 第一轮，两臂）

- **cl_v0 臂**：会话起始装配（assembler_manifest）→ AGENTS.md 供给 →
  verify_preaction 关口（既有 v0.1 五件套，不改代码）；
- **baseline 臂（摘要恢复对照）**：同一模型、同一 scripted turns；会话 2 起始
  注入 `make_summary_recovery.py` 机械生成的摘要（公平、可复现、信息量下限
  经机械核验），无 CL 引擎与关口。

公平性设计（对照不是稻草人的三道保障）：
1. 两臂收到完全相同的 scripted turns（外部事件通知两臂都在会话 1 逐字收到）；
2. baseline 的摘要恢复由固定模板机械生成，含同样的外部事件三元组（信息量
   下限检查硬性把关）；
3. 摘要不含任何裁定性表述（泄判关键词检查）——"判断什么失效"正是 cl_v0 臂
   的被测能力。

## 运行方式（正式窗口，预注册批准后）

- 复用 v0.1 五件套：`tools/cl_install.py`（新测试目录安装）、`cl_turn.py`
  （端到端单轮）、`cl_selfcheck.py`（装置自检 6 项）；
- 主仓侧逐轮驱动：`graph/scripts/pilot_turn_driver.py`（--agents-md /
  --control-file / --trace / baseline 臂 --skip-cl-call）；
- 先 1 场景试跑装置并过验收清单（含"轨迹可被修好后的评分器重新打分"），
  再批量。验收清单与判据见主仓 `host_integration/round1_falsification_criteria.md`。

## 明确不做

- 不写新插件、不改 cl_* 工具与 cl-v0-inject.js（复用 v0.1 现状）；
- 不把 round1 结论建立在装置跑通之上（跑通≠成立）；
- blind_holdout、validate_v2、p1/p2 旧产物一概不动。
