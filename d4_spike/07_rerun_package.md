# 独立复跑包（阶段 4 §五.4.3）——状态：尚未独立复核

由未实施本轮改动的复核方按本包执行即可复现关键结论。所有命令均为本轮实测命令。

## 0. 环境基线
- DSH 0.2.0-rc.2（`dsh --version` 验证）
- Node v22.19.0；python 3.12（CL 抽取脚本）
- 分支 `d4-spike-minimal-migration`（宿主仓 D:\CCXXLESSON\contextledger-host），HEAD 提交见 git log
- 隔离：`DSH_HOME=C:\Users\Lenovo\.dsh-pilot-home`（独立数据根）+ profile `dsh-pilot` + cwd `pilot\dshtest`

## 1. 复现"真实加载"（R1，零 LLM）
```powershell
$env:DSH_HOME = "C:\Users\Lenovo\.dsh-pilot-home"
dsh --profile dsh-pilot --dump-config
```
期望：输出含 `# == @contextledger/dsh-host-seam` 段与 `cl-host-seam` 条目（当前 mode/off 值以补丁为准）。

## 2. 复现"off 零行为"（R2，零 LLM）
补丁 `mode: off` 后：
```powershell
cd D:\CCXXLESSON\contextledger-host\pilot\dshtest
dsh --profile dsh-pilot "请只回复 OK"
```
期望：`pilot\dshtest\traces\host_sidestep.jsonl` 行数不增长。

## 3. 复现"on 供给 + L2 请求时点可见"（R3，1 次真实调用）
补丁 `mode: on`、`budgetMaxCalls: 1` 后：
```powershell
dsh --profile dsh-pilot "请只复述你收到的 CL 任务记忆块标注的 revision。不要使用工具。"
```
期望：模型复述 `run/assembler_manifest.json` 的 `state_revision`；`traces\host_sidestep.jsonl` 出现 `cl_memory_supply_proposed`（msg_id）与 `request_messages_observed`（present=true，同 msg_id）；`host_events.jsonl` 派发事件含 `supply_visible_in_derived` 字段。

## 4. 复现"版本替代"（R4，1 次真实调用）
修改 `run\current_states.json` 的 revision 与内容（conflict+deletion 变化）→ 重跑 R3 命令。
期望：新 revision 供给、模型按新内容回答（本包附通过样本：V2，回答 agent-zhao/无记录/已采纳）。

## 5. 复现"预算闸门"（R5，零真实调用消耗）
`budgetMaxCalls: 1` 下运行任何会触发 >1 次调用的任务。
期望：第 2 次调用在进入适配器前被拦（`budget_gate_blocked` 旁证 + 进程以预算错误终止）。

## 6. 隔离复核（R6，零 LLM）
```powershell
# 日常 profile 指纹比对（基线：d4_spike\isolation_baseline.txt，824 文件）
```
期望：web/headless 日常 profile 文件集与基线一致（本轮唯一差异：web 补丁 agent-default-model 行，系用户 GUI 切模型所致，非本工作包写入）。

## 关键结论与判据映射
| 结论 | 判据 |
|---|---|
| S1 真实加载 ✅ | R1 + 运行时旁证 |
| S2 部分（file.edited 未覆盖） | traces 逐 run 对账 |
| S3 请求时点可核验 ✅ | R3 的 llm/stream 观测（provider 实际所见） |
| S4 ❌ / S5 ⏸ / S6 ⏸ | 见 05_phase34_verdicts.md |
