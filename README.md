# contextledger-host

ContextLedger 的宿主侧集成仓库（工作包 D3，GPT-6 评审工作包 D）。

本仓库与 `D:\CCXXLESSON\contextledger`（CL 主仓库）之间的**边界规则**：

1. **本仓库绝不 import `graph/scripts/*`**。唯一的机器契约是：
   - CL 主仓库的 `graph/scripts/verify_preaction.py` 的 CLI 退出码（0=前提成立 / 2=前提失效）；
   - 双方约定的 JSON 文件格式（`assembler_manifest.v1`、`shadow_diff_report.v1`、场景定义）。
2. **CL 主仓库绝不 import 本仓库代码**。主仓库只保存记录
   （`graph/projects/abu_modern/host_integration/*.json`），保存指针、场景定义与指标报告。
3. `traces/` 不入库（gitignore），与主仓库 `runs_archive/` 同等纪律。

## 目录

- `opencode/` — OpenCode 接缝（D1 研判：主接缝，待版本钉扎）
  - `plugin/` — OpenCode 插件（hook 消费、上下文注入、permission.ask 阻断）
  - `adapter/` — 只读影子观察器（D2）
- `openclaw/` — OpenClaw 备选接缝（D1 记录保留，不主推：消息网关架构与编码场景错配）
  - `plugin/` — before_prompt_build / before_tool_call + ContextEngine
  - `adapter/` — 同上结构的影子观察器
- `scenarios/` — 预注册场景定义（D4）
- `traces/` — 影子/成对运行产物（gitignored）

## 状态

- D1 研判结论：OpenCode 主接缝（`host_seam_decision.json`，
  `decision: opencode_primary`，`decision_status: provisional_pending_version_pin`）
- **前置条件未完成**：OpenCode checkout 停在 1.17.11+128 commits（dfeb1b50），
  实际运行二进制 1.18.29。在版本对齐 + experimental.chat.* 签名复核完成之前，
  影子模式只做**只读观察**（adapter），不写任何注入代码。
- 若版本钉扎失败 → `decision: log_tail_adapter_only`，D 降级为仅影子模式，
  不硬做成对运行。
