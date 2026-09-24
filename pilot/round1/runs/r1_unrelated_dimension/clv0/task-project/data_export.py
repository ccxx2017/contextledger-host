"""data_export.py —— CSV 导出模块（规范 v1：列头 + 行数据 + 合计行）。"""

import csv
import math
from pathlib import Path

TOTAL_LABEL = "合计"


def _parse_number(value):
    """把单元格解析为数字，失败返回 None。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            try:
                number = float(text)
            except ValueError:
                return None
            return number if math.isfinite(number) else None
    return None


def _column_total(cells):
    """列内所有非空单元格均为数字时返回合计，否则返回 None。"""
    total = 0
    has_value = False
    saw_float = False
    for cell in cells:
        if cell is None or (isinstance(cell, str) and not cell.strip()):
            continue
        number = _parse_number(cell)
        if number is None:
            return None
        total += number
        has_value = True
        saw_float = saw_float or isinstance(number, float)
    if not has_value:
        return None
    return float(total) if saw_float else total


def _format_total(total):
    """合计值格式化为单元格，无合计的列输出空字符串。"""
    if total is None:
        return ""
    if isinstance(total, float) and total.is_integer():
        return int(total)
    return total


def export_csv(rows, path, headers=None, encoding="utf-8-sig"):
    """导出行数据为 CSV 文件：首行列头、中间行数据、末行合计，返回文件路径。"""
    normalized = [dict(row) if isinstance(row, dict) else list(row) for row in rows]

    if headers is None:
        if not normalized:
            raise ValueError("rows 为空且未提供 headers，无法确定列头")
        first = normalized[0]
        if isinstance(first, dict):
            headers = [str(key) for key in first]
        else:
            headers = [f"col{i + 1}" for i in range(len(first))]
    headers = [str(h) for h in headers]
    if not headers:
        raise ValueError("headers 为空，无法导出")

    width = len(headers)
    if normalized and isinstance(normalized[0], dict):
        data = [[row.get(header, "") for header in headers] for row in normalized]
    else:
        data = [(list(row) + [""] * width)[:width] for row in normalized]

    total_row = [TOTAL_LABEL]
    for index in range(1, len(headers)):
        total_row.append(_format_total(_column_total([row[index] for row in data])))

    with open(path, "w", newline="", encoding=encoding) as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
        writer.writerow(total_row)
    return Path(path)
