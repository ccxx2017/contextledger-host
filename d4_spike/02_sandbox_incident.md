# D4-spike 阶段1 执行环境事故与排障记录（2026-10-08）

## 事故
1. 会话中段沙箱文件视图分裂：Write/glob 通道与 pwsh 通道对同一 D: 路径给出不同文件集，且跨调用波动。
   后果：部分产物曾落不到用户可见磁盘；trace 文件用户 copy 失败但我方通道可读。
2. 我的 pwsh 子进程与 DSH web 宿主同进程组：kill/中断挂起的 dsh 子进程时控制台 Ctrl 事件
   打到整组，两次打断用户的 blmcp（Blender MCP）→ web 服务中断。已停止该模式（不再 job_kill）。
3. 凭证外泄：检查 key 存在性时正则过宽，把 .dsh/.credentials.yaml 多个 key 明文打进会话输出。建议用户轮换。

## 排障结论（"挂起"真正根因）
- dsh-pilot profile 的 dsh.profile.bundles 缺 @deepseek-ai/dsh-headless（app 插件）→
  树挂载后无插件认领任务/help/退出 → 进程永久静默闲置。
  证据：dsh-min（纯 dsh-base）--dump-config 正常退出而 --help 挂起；补该行后 --help 正常退出。
- 排除项：文件锁、stdin 阻塞、进程组劫持、网络阻断（api.stepfun.com:443 实测可达）均非根因。
- 附带发现：Copy-Item -Recurse 会把 junction 解引用成物理副本 → profile 副本加载陈旧发射器。

## 修复清单
- 两处 profile（~/.dsh 与 ~/.dsh-pilot-home）bundles 补 @deepseek-ai/dsh-headless；
- 发射器 v2：契约/旁证分流（host_events.jsonl / host_sidestep.jsonl）、摘要逐项容错不丢事件；
- 残留进程按 PID 定点清理；预算台账建立（03_budget_ledger.md）。