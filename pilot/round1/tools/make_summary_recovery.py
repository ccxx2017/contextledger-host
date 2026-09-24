#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
make_summary_recovery.py — round1 baseline 臂"约定的摘要恢复"机械生成器。

模板 r1_summary_template_v1（全文冻结于 round1_preregistration.json，改动即窗口重开）：
- 只从场景的 scripted_turns 机械转写，不做任何语义改写、不增删事实；
- 会话 1 的每一条 external_event 必须逐字出现在摘要中（信息量下限，由
  check_info_floor.py 机械核验）；
- 不含任何"什么已失效/什么不能作为依据"的裁定性表述——裁定是 cl_v0 臂的
  被测能力，写进 baseline 摘要即泄判（对照变成稻草人）。

用法：
    python make_summary_recovery.py --scenario <scenario.json> --out <summary.md>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TEMPLATE_ID = "r1_summary_template_v1"

TEMPLATE = """# 会话恢复摘要（{template_id}）

> 本摘要由固定模板机械生成，供新会话恢复上文使用。

## 任务背景
{task_line}

## 会话 1 逐轮记录
{turn_lines}

## 会话 1 结束时的已知事实（逐条转写自外部事件通知）
{event_lines}

## 备注
以上为会话 1 的全部已知信息。请基于当前目录的实际文件状态继续工作。
"""


def build_summary(scenario: dict) -> str:
    turns = scenario.get("scripted_turns", [])
    session1 = [t for t in turns if int(t.get("session", 0)) == 1]

    task_line = str(scenario.get("title", "")).strip()
    entities = scenario.get("entities", {})
    if entities:
        task_line += "；涉及实体：" + "、".join(f"{k}={v}" for k, v in entities.items())

    turn_lines: list[str] = []
    for t in session1:
        line = f"- 第 {t.get('turn')} 轮（用户）：{str(t.get('user', '')).strip()}"
        evt = t.get("external_event")
        if evt:
            line += (
                f"；【外部事件通知】kind={evt.get('kind')}，"
                f"entity={evt.get('entity')}，state={evt.get('state')}"
            )
        turn_lines.append(line)

    event_lines: list[str] = []
    for t in session1:
        evt = t.get("external_event")
        if evt:
            event_lines.append(
                f"- 外部事件：kind={evt.get('kind')}；entity={evt.get('entity')}；"
                f"state={evt.get('state')}"
            )
    if not event_lines:
        event_lines.append("- （会话 1 无外部事件通知）")

    return TEMPLATE.format(
        template_id=TEMPLATE_ID,
        task_line=task_line,
        turn_lines="\n".join(turn_lines),
        event_lines="\n".join(event_lines),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="round1 baseline 臂机械摘要恢复生成器")
    parser.add_argument("--scenario", required=True, help="场景 JSON 路径")
    parser.add_argument("--out", required=True, help="输出摘要 md 路径")
    args = parser.parse_args()

    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    summary = build_summary(scenario)
    Path(args.out).write_text(summary, encoding="utf-8")
    print(f"wrote {args.out} ({TEMPLATE_ID})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
