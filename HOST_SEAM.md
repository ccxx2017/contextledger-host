# HOST_SEAM 宿主接缝决策记录（镜像）

权威记录：CL 主仓库 `graph/projects/abu_modern/host_integration/host_seam_decision.json`
（本文件是其人工可读镜像；两处不一致时以 JSON 为准）。

## 决策（2026-09-05，工作包 D1 重新研判）

**`decision: opencode_primary`** —— `decision_status: provisional_pending_version_pin`

- 两个宿主的本地源码 checkout 均已逐符号核实（file:line 证据见 JSON）：
  - OpenCode `D:/CCXXLESSON/opencode`（dev @ dfeb1b50，workspace 1.17.11）
  - OpenClaw `D:/CCXXLESSON/openclaw`(main @ c5b3f00d，2026.4.14)
- Q1-Q4 计分：两宿主均 3 分；平手按 Q2+Q3 双是进入架构裁决：
  评审首场景是**长程编码任务**，需要编码 Agent 的 session/tool 循环 →
  OpenCode（终端编码 Agent）胜出；OpenClaw 是消息网关，管线错配。
- 旧结论全部作废：OpenCode 源码中 `before_prompt_build`/`before_tool_call` **0 命中**
  （属 OpenClaw）；OpenClaw 中 `before_agent_run` **0 命中**（实名 before_agent_start，
  且正被迁移废弃）。

## 启用影子/注入的前置条件

1. **版本对齐**：checkout 停在 1.17.11+128 commits（2026-06-27），运行二进制 1.18.29。
   checkout 到运行版本对应 tag（本地无标签，需 fetch）或把 npm 包对齐 checkout。
2. **签名复核**：在钉扎 sha 上复核 `chat.params`、`experimental.chat.messages/system.transform`
   的签名与调用点（load-bearing hooks 带 experimental. 前缀，无 CHANGELOG 可考）。

## 前置条件失败时的降级路径

`decision: log_tail_adapter_only` —— D 降级为仅影子模式（只读采集 + verify_preaction 裁定），
**不硬做成对运行**。

## 影子模式边界（本轮已交付）

- `opencode/plugin/cl-shadow-observer.ts`：只读采集 host_event.v1 JSONL
  （代码就绪，未启用——等前置条件）。
- `opencode/adapter/observe.py`：影子观察器。支持两种输入：真实 hook JSONL、
  或 `--scenario scenarios/reassignment_recovery.json --simulate`（钉扎前管线验证）。
  影子模式只证明输入会变，不证明行动更好。
