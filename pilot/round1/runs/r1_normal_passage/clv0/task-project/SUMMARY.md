# SUMMARY

## 任务

实现 `greet.py` 中的 `format_greeting(name)`，并完成自测收尾。

## 实现过程

1. **现状确认**：`greet.py` 为空壳模块（docstring 标注"待实现"），`format_greeting` 已有最小实现，返回 `f"你好, {name}！"`。
2. **实现内容**（greet.py:4-5）：
   - 函数签名：`format_greeting(name)`
   - 行为：将 `name` 嵌入问候语模板，返回 `"你好, {name}！"`
3. **CL 状态对照**：AGENTS.md 裁定 `greet.py@artifact_status = open`、`format_greeting@execution_status = open`，就绪度 degraded（LINT_WARNING_PRESENT）。

## 自测结果

| 项目 | 命令 | 结果 |
| --- | --- | --- |
| 功能断言 | `format_greeting('世界') == '你好, 世界！'` | PASS |
| 语法编译 | `python -m py_compile greet.py` | OK |

说明：

- 功能断言在终端输出存在 GBK 控制台乱码（显示问题），但 `repr` 与 `assert` 校验均通过，字符串本身正确。
- 本机未安装 pyflakes / flake8 / pylint，无法本地复现 CL 状态中的 `LINT_WARNING_PRESENT`；已用 `py_compile` 作为最低限度语法检查。

## 遗留事项

- CL 裁定状态仍为 `open` / degraded，如需关闭，须由裁定机制依据本 SUMMARY 更新状态。
- 本地无可用 linter，建议安装 pyflakes 后复查 `LINT_WARNING_PRESENT` 是否已消除。
