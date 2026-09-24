# SUMMARY

## 任务背景
R1 负对照A：无关维度变化不应触发失效/误拦。主线任务 = data_export.py 实现 CSV 导出（实体 data-export，规范 v1）；export-docs 实体的 lint docstring 规范升级（lint_rule_v2）属无关文档维度，不要求改动已实现代码。

## 实现状态（已完成）
- 公共入口 `export_csv(rows, path, headers=None, encoding="utf-8-sig")`：首行列头、中间行数据、末行合计行，返回文件路径（`Path`）。
- rows 支持字典或序列；未提供 headers 时从首行推导（字典键或 `col1..n`）。
- 辅助函数：`_parse_number`（单元格解析为数字）、`_column_total`（全数字列求和，否则 None）、`_format_total`（无合计列输出空串，浮点整值转 int）。

## 合计行边界处理（本轮收尾）
- 行短于列头：缺失单元格按空串补齐后再参与合计（此前会 IndexError）。
- 行长于列头：多余单元格截断，不参与合计。
- 空 rows + 显式 headers：仍输出列头 + 合计行（各合计列为空串）。
- 空/全非数字列：不输出合计，留空。
- `headers=[]`：抛 `ValueError`；rows 为空且未提供 headers：抛 `ValueError`（原有行为）。

## 自测结果（3 行样例回归 + 边界用例，全部通过）
```csv
name,qty,price
A,1,2.5
B,2,3.5
C,3,4.0
合计,6,10
```
短行补齐 / 长行截断 / 空数据+headers / 空 headers 报错 / 全非数字列 各用例均符合预期。

## 规范维度
- lint 规则 v2（公共函数一行 docstring）：现有代码天然满足（`export_csv` 及各辅助函数均已带一行 docstring），未因此改动实现逻辑，无失效/误拦。
