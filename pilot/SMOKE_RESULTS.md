# 冒烟结果 S1–S3（2026-09-06，无头 opencode run）

环境：隔离项目 `pilot/smoke-project/`，项目级插件 `.opencode/plugin/cl-shadow-observer.js`（零依赖 JS），
全局配置未动（全局 plugin 键 ABSENT——插件仅该项目加载，无其他插件牵连）。
任务：创建 smoke.txt（内容 ok）→ Agent 实际创建并 `wc -c` 自验证。

## S1 插件实际加载 —— ✅ PASS

trace 采集到 12 个事件、5 类 hook 全部生效
（`sampling_params`×4 / `llm_call_start`×3 / `tool_execute_before`×2 / `tool_execute_after`×2 / `file_edited`×1）。
证据：`pilot/smoke_20260906_events.jsonl`（trace 目录 gitignored，故复制入库）。

## S2 原始事件完整采集与对齐 —— ✅ PASS（含一条提取器备注）

事件与会话操作对账一致：3 次 LLM 调用（多步循环：write → bash 验证 → 最终答复）、
工具事件含真实 args（write 的 filePath/content 完整可见——这是 S5 阻断面的抓手）、
file.edited 1 次。
备注：`context_refs` 实体提取启发式在本条无实体引用的会话中为 0 命中（预期行为）；
pilot 需用含实体状态语义的真实文本验证提取率。

## S3 最终模型输入可核验 —— ✅ 边界可观测性 PASS

`llm_call_start` 事件在 `experimental.chat.messages.transform` 边界采集
（payload.boundary 字段明确标注 final pre-model input），最后一轮 message_count=3。
即：**最终输入在发送前可完整 dump**——评审 §三.5 要求的可观测边界成立。
注意：本条仅证明边界可观测；"最终输入包含 CL 装配结果且未被覆盖"需 CL-V0 注入臂
（同一 hook 改写 messages/system）+ 对照 dump，属 pilot 主体，不在本冒烟范围。

## 尚未通过（后续步骤）

- **S4** lifecycle 从真实抽取链路进入主图：需 extractor prompt 输出 lifecycle 字段
  （当前 prompt 不产出 → 新实验版本 prompt v2，按评审 §六.6 开新版本，不改冻结实现）
- **S5** 过期动作实际阻止：需 CL-V0 插件把 `verify_preaction.py` 接入 `permission.ask`
  + `tool.execute.before`（args 已可见，抓手已验证）
- **S6** quarantine readiness 被宿主消费：需宿主读取 assembler_manifest 的消费逻辑
- 版本对齐残余：源码 checkout 仍在 1.17.11（GitHub 不可达）；SDK 级钉扎已完成
  （`opencode/sdk-1.18.29/`）；配置目录 SDK 1.18.23 待随插件安装对齐 1.18.29
