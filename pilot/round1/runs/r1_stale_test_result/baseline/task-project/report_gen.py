"""report_gen.py —— 月度报表生成器（有 bug 待修）。"""

from numparse import parse_number


def build_report(rows):
    """rows: [(name, amount_str), ...] -> 报表文本（含合计行）。"""
    lines = ["月度报表", "------"]
    total = 0.0
    for name, amount in rows:
        value = parse_number(amount)
        total += value
        lines.append(f"{name}: {value:.2f}")
    lines.append(f"合计: {total:.2f}")
    return "\n".join(lines) + "\n"
