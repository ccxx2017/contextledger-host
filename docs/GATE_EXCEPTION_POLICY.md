# 门控异常策略（v0.1）

原则：**关口自身的故障不得放大为宿主任务故障；宿主的错误动作必须被关口拦住。**
两者冲突时，优先拦错误动作，但任何异常必须留痕（trace 事件）。

## 异常矩阵

| 异常 | 行为 | 留痕 |
|---|---|---|
| verify_preaction.py 不可达 / 崩溃 | fail-open（放行） | `cl_gate_error` |
| verify_preaction 超时（15s） | fail-open（放行） | `cl_gate_error` |
| 控制文件不可解析 / 缺失 | fail-open（放行） | `cl_gate_error` |
| manifest 不可读 | fail-open（放行） | `cl_gate_error` |
| verify_preaction exit 2（依据过期/前提违反） | **阻断**（抛错，工具不执行） | `cl_gate_verdict` |
| manifest readiness=blocked | **阻断** | `cl_gate_verdict` / `cl_readiness_verdict` |
| verify_preaction 非预期退出码 | fail-open（放行） | `cl_gate_unexpected` |

## 紧急停用（一行）

```bash
# 方式一：解除门控（保留观察）
python -c "import json,pathlib; p=pathlib.Path('.opencode/cl_v0.json'); d=json.loads(p.read_text()); d['gate']=False; p.write_text(json.dumps(d))"
# 方式二：完整停用恢复
python tools/cl_disable.py --project <项目目录>
```

## 已知取舍（待评审确认）

- **fail-open**：关口故障时放行。理由：关口故障是装置问题，不应把任务卡死；
  代价是故障窗口内的错误动作不被拦——由 trace 的 cl_gate_error 全量留痕补偿，
  事后可审计。若评审要求 fail-closed（故障即阻断），改动为一处 throw，但任务将
  在关口故障期间完全停摆。
- **spawnSync 15s 超时**：verify_preaction 挂起时放行（同样 fail-open + 留痕）。
