#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
check_info_floor.py — round1 摘要恢复"信息量下限"机械检查（裁定补强①）。

规则（硬性，不过即对照无效、不得开跑）：
1. 场景会话 1 的每一条 external_event（kind/entity/state 三元组）必须在
   摘要文本中逐字出现；
2. 会话 1 的每一轮用户原话的前 60 个字符必须在摘要中出现（保证逐轮记录
   不缺轮）；
3. 摘要不得包含裁定性关键词（"失效/已取消/不得作为依据/superseded/冻结"
   等由 CL 侧判定的表述）——出现即视为泄判，对照无效。

用法：
    python check_info_floor.py --scenario <scenario.json> --summary <summary.md>
退出码：0 = 通过；2 = 未通过（打印缺失项）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VERDICT_BAN_PATTERNS = [
    "已失效",
    "不得作为依据",
    "superseded",
    "已取消",
    "已冻结",
    "不能作为行动依据",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="round1 摘要恢复信息量下限检查")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    summary = Path(args.summary).read_text(encoding="utf-8")

    failures: list[str] = []

    session1 = [t for t in scenario.get("scripted_turns", []) if int(t.get("session", 0)) == 1]

    for t in session1:
        evt = t.get("external_event")
        if evt:
            for field in ("kind", "entity", "state"):
                value = str(evt.get(field, ""))
                if value and value not in summary:
                    failures.append(
                        f"外部事件字段缺失：{t.get('session')}:{t.get('turn')} "
                        f"{field}={value}"
                    )
        head = str(t.get("user", "")).strip()[:60]
        if head and head not in summary:
            failures.append(f"逐轮记录缺轮：{t.get('session')}:{t.get('turn')} 用户原话头部未出现")

    for pattern in VERDICT_BAN_PATTERNS:
        if re.search(pattern, summary, flags=re.IGNORECASE):
            failures.append(f"泄判关键词出现：{pattern}")

    if failures:
        print("信息量下限检查未通过：")
        for item in failures:
            print(f"  - {item}")
        return 2

    print("信息量下限检查通过（事件三元组齐全、逐轮记录齐全、无泄判关键词）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
