"""test_report_gen.py —— 报表测试套件（3 项，版本 A 下全部失败）。"""

from report_gen import build_report


def test_thousands_separator():
    out = build_report([("A", "1,234.50")])
    assert "1234.50" in out


def test_total_with_thousands():
    out = build_report([("A", "1,000.00"), ("B", "2,500.00")])
    assert "合计: 3500.00" in out


def test_report_line_with_thousands():
    out = build_report([("C", "9,876.25")])
    assert "C: 9876.25" in out
