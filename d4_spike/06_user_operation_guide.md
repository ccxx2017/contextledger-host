# 用户操作说明（§六）——全部命令均已实测

前提：测试环境 = `dsh-pilot` profile + 独立 `DSH_HOME=C:\Users\Lenovo\.dsh-pilot-home` + 工作区 `contextledger-host\pilot\dshtest`。日常 DSH（web profile）完全不受影响。

## 1. 继续使用原来的 DSH
照常启动即可（`dsh web` 或你现有的日常入口）。测试安装未注册到日常 profile；`~/.dsh/pilot-home` 是独立数据根。

## 2. 启动 shadow
```powershell
$env:DSH_HOME = "C:\Users\Lenovo\.dsh-pilot-home"
# 编辑 C:\Users\Lenovo\.dsh-pilot-home\profiles\dsh-pilot\cordis.patch.yml → mode: shadow
cd D:\CCXXLESSON\contextledger-host\pilot\dshtest
dsh --profile dsh-pilot "你的任务"
```
实测：shadow 下模型正常工作，`pilot\dshtest\traces\` 产出旁证，模型输入不改变。

## 3. 启动 on 并绑定 CL 项目
```powershell
# 编辑同一补丁 → mode: on（clProject/clHome 已绑定 abu_modern）
$env:DSH_HOME = "C:\Users\Lenovo\.dsh-pilot-home"
cd D:\CCXXLESSON\contextledger-host\pilot\dshtest
dsh --profile dsh-pilot "你的任务"
```
实测：新会话首请求即自动携带已发布记忆（rev 0086:f77325d8e8cc，llm/stream 实证）。

## 4. 确认当前模式与已注入版本
- 模式：查看补丁文件 `Select-String "mode:" C:\Users\Lenovo\.dsh-pilot-home\profiles\dsh-pilot\cordis.patch.yml`；
- 已注入版本：`Select-String "cl_memory_supply" D:\CCXXLESSON\contextledger-host\pilot\dshtest\traces\host_sidestep.jsonl`（`cl_revision` 字段）；
- 启动状态行：headless 下插件状态行随日志输出（mode/profile/cwd/clProject/gate=OFF）。

## 5. 触发一次 CL 更新（哪些步骤需要你裁定）
- 更新链 = 明确触发：`raw/projects/abu_modern/s001/turn_0XX.md`（对话记录）→ `build_graph_slice.py` → `invoke_extractor.py`（deepseek-flash 1 次调用）→ `entity_resolver.py` → **pending_merge 待裁项交你裁定** → `apply_patch.py` + `assembler_manifest.py`（发布新 revision）。
- 需要你裁定的：pending_merge 逐条三选一（alias/supersede/coexist）；发布 readiness=degraded 时是否接受发布（本轮实测 degraded 发布，reason 如实标注）。
- 采集（对话）与抽取（脚本+模型）各自触发：采集=对话本身；抽取=你运行上述命令时。

## 6. 关闭 CL
补丁 `mode: off`（或直接停用插件，见 8）。**注意**：off 只停止新供给；已注入历史消息的会话中旧内容不会消失（本轮语义，见 04 文档 §5）。

## 7. 启动没有 CL 注入历史的新会话
off 模式下新开会话（不带 --session-id）即原生会话。实测：off 下 trace 零增长（V3）。

## 8. 停用测试环境并回到原入口
```powershell
# 停用插件（从 bundles 移除）：
# 编辑 C:\Users\Lenovo\.dsh-pilot-home\profiles\dsh-pilot\package.json
#   dsh.profile.bundles 移除 "@contextledger/dsh-host-seam"
# 之后日常照常：dsh web（DSH_HOME 不设或设回 ~/.dsh）
```
彻底清理（可选）：删除 `C:\Users\Lenovo\.dsh-pilot-home` 整目录 + `~/.dsh/profiles/dsh-pilot`。

## 明确回答（§六四问）
- **每轮手动启动 CL？** 不需要。选 on 入口后插件自动加载，每个适用请求自动读取并注入当前已发布记忆（实测：新会话、resume、换版三种场景）。
- **新对话自动更新 CL？** 否——新对话自动**注入**当前已发布记忆；更新（采集→抽取→裁定→发布）是明确触发的另一条链（见 5）。两者不混同。
- **关闭后旧内容消失？** 不能保证。off 停止新供给；干净新会话 = 无 CL 内容（实测 V3）。
- **是否启用 CL 工具阻断？** 本轮自始至终未启用（trace 中无任何阻断记录；供给旁证 decision_emitted=allow）。
