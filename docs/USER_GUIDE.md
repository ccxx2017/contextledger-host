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
