# 故障恢复规程（v0.1）

工具：`python tools/cl_recover.py --project <dir> --cl-project <名> --issue <类型>`

## 1. AGENTS.md 缺失/损坏

```bash
python tools/cl_recover.py --project <dir> --cl-project <名> --issue agents_md
```
从 CL 当前图 + manifest 重建（含就绪度与版本）。装前备份还原用
`cl_disable.py`（会还原 .opencode/backup/AGENTS.md.preinstall）。

## 2. 控制文件损坏

```bash
python tools/cl_recover.py --project <dir> --cl-project <名> --issue control_file
```
重建并刷新到当前权威图 revision。

## 3. 隔离裁定队列积压（readiness=blocked）

```bash
python tools/cl_recover.py --project <dir> --cl-project <名> --issue quarantine
```
输出未裁定清单与裁定方法。裁定流程（同 S6）：编辑 `quarantine_register.json`
的 disposition → 重跑 assembler_manifest → blocked 解除。

## 4. 轮次中途崩溃（宿主/抽取）

- 宿主会话崩溃：直接重跑 `cl_turn.py`（同一 --turn 号会重建 raw 并重抽取）
- 抽取反复失败进隔离：同 §3 裁定流程；重试 = 同 turn 号重跑 driver
- CL 图损坏：以 `graph_state.seed.json` + `patches/` 重放重建
  （参照主仓库 `replay_phase0_seal.py --reseed` 模式），重放后跑一次
  assembler_manifest 刷新

## 5. 停用/重装

停用 = `cl_disable.py`（宿主还原装前状态）；重装 = 重新 `cl_install.py`。
CL 侧数据（图/隔离/manifest）停用不影响，重装后自然续接。
