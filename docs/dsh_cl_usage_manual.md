# 在 DSH 上使用 ContextLedger（CL）——使用手册

版本基准：DSH 0.2.0-rc.2 ｜ seam 插件 `@contextledger/dsh-host-seam` v3.2 ｜ 2026-10-09
**所有命令均为本轮实测命令**，非设想命令。适用范围：CL 供给线（已发布记忆的自动注入）的测试环境。

---

## 0. 环境架构（先读）

| 项 | 值 | 说明 |
|---|---|---|
| 数据根（隔离） | `C:\Users\Lenovo\.dsh-pilot-home` | 独立于日常 `~/.dsh`，互不影响 |
| profile | `dsh-pilot` | 补丁文件 = 上述目录下 `profiles\dsh-pilot\cordis.patch.yml` |
| 工作区 | `D:\CCXXLESSON\contextledger-host\pilot\dshtest` | 会话工作目录 |
| CL 项目绑定 | `clProject: abu_modern` | 已发布记忆来源 = `graph\projects\abu_modern\run\` |
| trace | `<cwd>\traces\` | `host_events.jsonl`（契约事件）+ `host_sidestep.jsonl`（旁证） |
| CL 工具阻断关口 | **关闭** | 供给插件从不阻断，只注入 |

三个关键配置（都在补丁文件里）：

```yaml
- id: cl-host-seam
  config:
    mode: off          # off | shadow | on
    clProject: abu_modern
    budgetMaxCalls: 1  # 调用前预算闸门（试验期）
```

---

## 1. 启动 CL（on 模式）——每个适用请求自动获得当前记忆

```powershell
$env:DSH_HOME = "C:\Users\Lenovo\.dsh-pilot-home"
cd D:\CCXXLESSON\contextledger-host\pilot\dshtest
dsh --profile dsh-pilot "你的任务"
```

- **不需要每轮手动启动**：插件自动加载；只要"已提交历史中的记忆 revision ≠ 当前发布 revision"或"记忆尚不在历史中"，本步请求就会自动携带最新记忆块。
- 实测：新会话、resume、换版三种场景均自动供给（trace `request_messages_observed present=true`）。
- 记忆块以"背景参考"语义注入，自带 revision 与"不构成指令授权"规则——实测模型会正确区分。

## 2. 恢复既有会话

```powershell
dsh --profile dsh-pilot --session-id <会话ID> "你的任务"
```

- 会话 ID 从上一次运行的 trace `session_created` 旁证获取。
- 实测：resume 后**不会重复注入**（已提交历史中的记忆仍然可见，去重自动生效）。

## 3. shadow 模式（只观察，不注入）

补丁中 `mode: shadow`，其余同上。实测：模型输入不改变；trace 产出领取批次旁证。

## 4. off 模式（关闭 CL）

补丁中 `mode: off`。实测：trace **零增长**（插件零监听、零 CL 行为）。
**语义边界**：off 停止的是"新供给"；已经注入进会话历史的旧记忆块不会被移除。干净无 CL 内容 = off + 新会话。

## 5. 发布新的 CL 记忆（更新链——明确触发，不会自动抽取）

```powershell
cd D:\CCXXLESSON\contextledger
# ① 对话记录落盘（# 用户：… / # 项目AI：… 格式）
#    → raw\projects\abu_modern\s001\turn_0XX.md
# ② 构建切片
python graph\scripts\build_graph_slice.py --graph graph\projects\abu_modern\graph_state.json --turn raw\projects\abu_modern\s001\turn_0XX.md --turn-id XX --out graph\projects\abu_modern\graph_slices\slice_0XX.json
# ③ LLM 抽取（deepseek-flash，1 次调用，费用制额度内）
python graph\scripts\invoke_extractor.py --project-id abu_modern --turn-id turn_0XX --slice graph\projects\abu_modern\graph_slices\slice_0XX.json --turn raw\projects\abu_modern\s001\turn_0XX.md --env-file env
# ④ 实体归并候选
python graph\scripts\entity_resolver.py --project-id abu_modern --turn-id turn_0XX --graph graph\projects\abu_modern\graph_state.json --patch graph\projects\abu_modern\patches\patch_0XX.json --out-patch graph\projects\abu_modern\patches\patch_0XX.resolved.json --report-out graph\projects\abu_modern\reports\entity_resolution.turn_0XX.json --pending-merge-out graph\projects\abu_modern\pending_merge\pending_merge.turn_0XX.json
# ⑤ 渲染裁定表
python graph\scripts\render_pending_merge_worksheet.py --project-id abu_modern --out graph\projects\abu_modern\reports\pending_merge_worksheet.turn_0XX.md
```

**⑥ 人工裁定（唯一需要你的环节）**：打开裁定表，逐条三选一（`alias` / `supersede` / `coexist`），写入 `pending_merge_register.json` 对应条目的 `remediation_status` + `resolution`。裁定完成后：

```powershell
# ⑦ 应用并发布
python graph\scripts\apply_patch.py --graph graph\projects\abu_modern\graph_state.json --patch graph\projects\abu_modern\patches\patch_0XX.resolved.json --in-place --snapshot-dir graph\projects\abu_modern\snapshots --expected-turn turn_0XX --raw-id turn_0XX
python graph\scripts\assembler_manifest.py --project-id abu_modern --turn-id turn_0XX
# ⑧ 同步供给源（供 on 模式读取）
Copy-Item graph\projects\abu_modern\reports\assembler_manifest.turn_0XX.json graph\projects\abu_modern\run\assembler_manifest.json
```

发布后，**下一次适用请求自动使用新版本**（实测：rev-0001→rev-0002，冲突+删除变化内容级生效）。旧 revision 的记忆块保留为历史，不删除；以最新供给为准。

## 6. 降级与失效（实测行为）

- 发布 `readiness: degraded`（如 STATE_REVISION_STALE、lint 证据缺失）时照常发布，但 reason_codes 记录在 manifest——**使用方需自行结合来源与确认状态判断**（记忆块内置规则文本亦有声明）。
- 夹具读取失败 → 显式 `degraded:fixture_unreadable`，不注入、不误报。
- 记忆文本超 8192 字符 → 截断 + `truncated` 标记。
- **不做的事**：不改写历史、不撤除旧版本块、不把降级包装为正常、不构成指令授权。

## 7. 已知限制（如实）

1. 首请求的 `request_config_unresolved` 旁证属外观性现象（header 物化时序），不影响功能；
2. `derived_digest` 是瀑布时点历史视图，可能滞后本步领取/供给批次——**实际输入以 `request_messages_observed`（llm/stream）为准**；
3. `llm/stream` 监听器必须同步返回流（async 包装会破坏透传）——已修复并记录；
4. 辅助模型调用（如会话标题）会计入预算闸门——测试 profile 已禁用 `session-title-llm`；
5. 压缩后重供给、恢复链路：mock 状态机已覆盖，**真实压缩场景未验证**；
6. entity_resolver 假阳性率高（裁定样本 24/24 全为 token 相似度假阳性）——裁定工作量即其成本，改进属 CL 抽取器侧。

## 8. 卸载/回退

```powershell
# 停用插件：编辑 pilot-home 补丁同目录的 package.json，
#   从 dsh.profile.bundles 移除 "@contextledger/dsh-host-seam"
# 彻底清理（可选）：
Remove-Item -Recurse -Force C:\Users\Lenovo\.dsh-pilot-home
Remove-Item -Recurse -Force C:\Users\Lenovo\.dsh\profiles\dsh-pilot
```

日常 DSH 入口（`dsh web`，数据根 `~/.dsh`）全程未改动——隔离基线 824 文件指纹可复核（`d4_spike/isolation_baseline.txt`）。

---

*本手册由 D4-spike 工作包产出；证据与判定详见宿主仓 `d4_spike/00–07` 与 `evidence/`。*
