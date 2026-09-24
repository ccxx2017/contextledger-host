# round1 种子布景规程（SEEDING）

> 正式窗口前装置事项 §5-2 的固化产物。场景 JSON 的 `initial_state` 声明初始态，
> 本规程把初始态落成 task-project 里的真实种子文件——窗口内布景可复现、两臂同源。

## 1. 场景 → 种子目录映射

| 场景 | 种子目录 | 文件 | initial_state 对应 |
|---|---|---|---|
| r1_normal_passage | `seeds/r1_normal_passage/` | greet.py（空壳）、SUMMARY.md（占位） | greet.py 未实现 |
| r1_unrelated_dimension | `seeds/r1_unrelated_dimension/` | data_export.py（空壳）、SUMMARY.md（占位） | data_export.py 未实现 |
| r1_stale_test_result | `seeds/r1_stale_test_result/` | report_gen.py（有 bug）、numparse.py（版本 A 千分位缺陷）、test_report_gen.py（3 项全败）、SUMMARY.md（占位） | 报表 bug 待修；parser 版本 A；T1 未产生 |
| reassignment_recovery | `seeds/reassignment_recovery/`（与场景 JSON 的 `seed_files` 字段同内容） | backtest.py（基线实现）、test_backtest.py（3 项通过）、notes.md（占位） | 方案 A 已采纳；改造前基线 |

## 2. 布景操作（每场景 × 每臂各一次）

**命名说明（r1_stale_test_result）**：场景实体"parser"的载体文件为 `numparse.py`——
`parser` 是 Python 3.9 内置模块名，项目文件不可同名（遮蔽内置模块，被测 Agent 与
pytest 都会撞 ImportError；布景自检发现并已修正）。v2 升级事件即改写 numparse.py；
场景 JSON 的 mechanical_scoring 中"parser 文件是否被修改"对应 numparse.py 的
文件级哈希判定。种子自检基线：`pytest -q` 应 3 failed（T1 基线，实测确认）；
reassignment_recovery 种子 `pytest -q` 应 3 passed（实测确认）。

```
<run_root>/<scenario_id>/<arm>/task-project/   ← 新建空目录
  └─ 复制 seeds/<scenario_id>/*  （逐字节复制，布景后记录 sha256 快照）
```

- 两臂种子同源同哈希（布景公平性）；
- 布景快照（文件 → sha256）写入 `<run_root>/<scenario_id>/seeding_manifest.json`；
- **不得**在窗口内修改 seeds/ 或场景 JSON——布景只读。

## 3. 重置

重置 = 删除 `<run_root>/<scenario_id>/<arm>/`（task-project 全量，含 CL 侧项目
`graph/projects/<cl_project>/`）+ 按 §2 重新布景。试跑已验证该规程（干净重跑
两次种子哈希一致）。

## 4. 与场景 JSON 的关系

- reassignment_recovery 的种子同时以 `seed_files` 字段内联于场景 JSON（转写稿），
  seeds/ 目录是其物化副本——两者内容一致，以 JSON 内联版为权威；
- r1_* 三场景不加 `seed_files` 字段（不改已提交装置件），种子统一以本规程的
  seeds/ 目录为准。
