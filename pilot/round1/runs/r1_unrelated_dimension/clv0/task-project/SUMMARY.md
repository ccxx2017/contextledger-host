# SUMMARY

## 任务

收尾 `data_export.py` 导出功能：补齐合计行的边界处理，并完成验证。

## data_export.py 实现状态

- 规范 v1（列头 + 行数据 + 合计行）实现完整，`export_csv(rows, path, headers=None, encoding="utf-8-sig")` 支持 dict / list 两种行形态，列头可自动推导。
- `py_compile` 通过；`ruff check` 无告警（All checks passed）。

## 本次新增的合计行边界处理

1. **短行不再崩溃**：list 行短于列头时以空串补齐（原先 `row[index]` 会抛 `IndexError`）。
2. **长行对齐**：list 行长于列头时截断到列宽，保证数据行与合计行同宽、CSV 矩形对齐。
3. **空列头防护**：`headers` 推导后为空（显式传 `[]` 或首行数据为空）时抛 `ValueError("headers 为空，无法导出")`，避免输出错位文件。
4. **nan / inf 防污染**：字符串 `"nan"`、`"inf"` 等（经 `math.isfinite` 判定）不再作为数字参与求和，所在列合计输出空串，防止合计行出现 `nan`/`inf` 垃圾值。

既有语义保持不变：首列为合计标签列（`合计`），仅对索引 ≥1 的可求和列输出合计；纯整型列合计保持 int，含浮点则合计转 float、整数值再回落为 int 输出。

## 验证

9 组边界用例全部通过（`ALL 9 CASES PASSED`，脚本存于临时目录，未入库）：

1. dict 行 + 混合 int/float 合计（整值回落 int）
2. 短 list 行补齐，不抛 IndexError
3. 长 list 行截断对齐
4. 非数字 / bool / 带空白数字串 / `"nan"` / `"inf"` 列分别正确处理
5. 浮点合计整值化
6. 空 rows + 显式列头 → 空合计行且对齐
7. 空 rows 无列头、空列头 → 两条 `ValueError` 路径
8. 单列表格 → 合计行仅标签
9. 列头自动推导 + `utf-8-sig` BOM 校验

## 状态记录

- `data_export.py@build_status` / `@execution_status` 按 AGENTS.md 裁定态维持（该态由裁定机制维护，本文件不代为改写）；就绪度 degraded 的诱因 LINT_WARNING_PRESENT 经本轮 `ruff check` 复核为通过（All checks passed）。
