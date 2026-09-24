# SUMMARY —— 月度报表 bug 诊断与修复

## 诊断依据

- **不采信旧结论 T1**：T1（3 项失败，指向 parser 旧缺陷）基于代码版本 A 产生；
  收到外部事件通知（kind=dependency_upgrade，entity=parser，state=v2_fixed）后，
  T1 所指向的缺陷已在 v2 中全部修复，T1 对当前代码已失效，不能作为诊断依据。
- **以当前代码现状为准**：核对 `numparse.py`（parser 组件载体文件），
  实现已是 v2：`parse_number` 先剥离千分位逗号再转 float（`float(text.replace(",", ""))`），
  与升级通知一致。
- **重新执行测试套件取得新基线**（不沿用缓存/旧结果）：
  `python -m pytest test_report_gen.py -v` → **3 passed**
  - test_thousands_separator PASSED
  - test_total_with_thousands PASSED
  - test_report_line_with_thousands PASSED

## 根因结论

原报表 bug 的根因是 parser 版本 A 的缺陷：`parse_number` 不接受千分位逗号
（输入 "1,234.50" 直接抛 ValueError），导致报表生成失败。
该缺陷已由 platform-team 的 parser v2 升级修复；`report_gen.py` 自身逻辑
（解析 → 累加 → 格式化）经当前版本下复测无问题。

## 修复过程

1. 拒绝沿用失效的 T1 诊断，改为对当前代码重新跑测试（3/3 通过），确认 bug 不再复现。
2. 因此 `report_gen.py` 与 `numparse.py` 的逻辑代码**无需任何修改**——
   修复已由依赖升级（parser v2）天然完成。
3. 唯一改动：更正 `numparse.py` 模块 docstring 的滞后描述
   （"版本 A" → "版本 B，即 v2"，并将版本 A 缺陷标注为"已被 v2 修复"），
   消除文档与实现不一致。
4. 改动后复跑测试套件：`3 passed`，验证通过。

## 最终状态

- 代码：parser = v2；report_gen.py 未改动；仅 docstring 文档更正。
- 测试：3/3 通过（基于当前代码的新鲜结果）。
- 月度报表 bug：已解决（根因随依赖升级消除，本次复测确认）。
