"""numparse.py —— 报表数据解析组件（版本 B，即 v2；场景实体"parser"的载体文件）。

命名说明：parser 是 Python 3.9 内置模块名，项目文件不可同名（会被内置模块遮蔽），
故组件概念名"parser"的载体文件为 numparse.py；v2 升级即改写本文件。
版本 A 已知缺陷（已被 v2 修复）：parse_number 不接受千分位逗号（"1,234.50" 直接 ValueError）。
"""


def parse_number(text):
    """把字符串解析为 float（版本 B：先剥离千分位逗号再转换）。"""
    return float(text.replace(",", ""))
