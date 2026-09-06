#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CL 影子观察器（工作包 D2）——只读旁路，绝不改宿主行为、绝不写 CL 主链。

边界契约（README.md）：
  - 本适配器不 import CL 主仓库任何代码；唯一机器契约是
    `verify_preaction.py` 的 CLI 退出码（0=前提成立 / 2=前提失效）。
  - CL 侧产物全部落在独立影子命名空间（--shadow-project），不碰主项目。

输入（二选一）：
  --from-jsonl FILE        宿主 hook 事件流（host_event.v1 JSONL，
                           由 opencode/plugin 采集：chat.params / tool.execute.before /
                           file.edited / session.compacted）
  --scenario FILE --simulate 场景驱动模拟（D4 场景定义展开为宿主事件流，
                           用于宿主版本钉扎前验证整条影子管线）

行为：
  1. 把宿主事件逐 turn 落为影子命名空间的 raw 锚文件（只写 shadow 项目，不碰主链）
  2. --with-cl-processing 时：对影子项目逐 turn 调 CL run_auto_turn --dry-run
     （消耗 Extractor API；缺省关闭——影子模式优先零成本采集）
  3. 每个污染检查点调 CL verify_preaction.py（subprocess，退出码即契约），
     记录 CL 对「宿主当前依据是否过期」的裁定
  4. 产出 shadow_diff_report.v1：逐 turn 分类
     stale_in_host（宿主依据了 CL 已判定失效的状态）/
     missing_in_host（CL 当前态有而宿主上下文缺失）/
     extra_in_host（宿主上下文有而 CL 未跟踪）

影子模式只证明「输入会变」，不得据此宣称行动指标（评审 §工作包D）。

用法：
    python adapter/observe.py --from-jsonl traces/host_events.jsonl \
        --shadow-project abu_modern_host_shadow --out traces/shadow_diff_report.json
    python adapter/observe.py --scenario scenarios/reassignment_recovery.json --simulate ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# CL 主仓库位置：contextledger-host/<this file> 的祖先链是
# adapter → opencode → contextledger-host → CCXXLESSON；CL 主仓库在
# CCXXLESSON/contextledger。可用环境变量 CL_HOME 覆盖。
import os as _os

CL_HOME = _os.environ.get("CL_HOME") or str(Path(__file__).resolve().parents[3] / "contextledger")
CL_HOME = Path(CL_HOME)
VERIFY_PREACTION = CL_HOME / "graph" / "scripts" / "verify_preaction.py"


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scenario_to_events(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """把 D4 场景定义展开为 host_event.v1 序列（模拟模式）。"""
    events: list[dict[str, Any]] = []
    for step in scenario.get("scripted_turns", []):
        context_refs = [
            {
                "entity": ref["entity"],
                "state": ref["state"],
                "source": ref.get("source", "prompt"),
            }
            for ref in step.get("host_context_refs", [])
        ]
        events.append({
            "type": "llm_call_start",
            "ts": step.get("at"),
            "turn_id": step["turn_id"],
            "context_refs": context_refs,
            "payload": {"note": step.get("note", "")},
        })
        for tool_event in step.get("tool_events", []):
            events.append({
                "type": "tool_execute_before",
                "ts": tool_event.get("at"),
                "turn_id": step["turn_id"],
                "context_refs": [],
                "payload": dict(tool_event),
            })
    return events


def group_by_turn(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for e in events:
        grouped.setdefault(str(e.get("turn_id")), []).append(e)
    return grouped


def write_raw_anchors(
    shadow_raw_dir: Path,
    turn_id: str,
    turn_events: list[dict[str, Any]],
) -> Path:
    """宿主事件落为影子命名空间 raw 锚（只追加、不改写）。"""
    shadow_raw_dir.mkdir(parents=True, exist_ok=True)
    body_lines = [f"# host shadow turn: {turn_id}", ""]
    for e in turn_events:
        body_lines.append(f"## {e.get('type')} @ {e.get('ts')}")
        for ref in e.get("context_refs", []):
            body_lines.append(f"- 宿主上下文引用: {ref.get('entity')} = {ref.get('state')} (via {ref.get('source')})")
        note = (e.get("payload") or {}).get("note")
        if note:
            body_lines.append(f"- note: {note}")
        body_lines.append("")
    anchor = shadow_raw_dir / f"{turn_id}.md"
    anchor.write_text("\n".join(body_lines), encoding="utf-8")
    return anchor


def call_verify_preaction(shadow_project: str, state_revision: str) -> dict[str, Any]:
    """调用 CL 的 verify_preaction.py（subprocess；退出码即契约）。"""
    if not VERIFY_PREACTION.exists():
        return {"available": False, "detail": f"CL_HOME 下找不到 {VERIFY_PREACTION}"}
    result = subprocess.run(
        [sys.executable, str(VERIFY_PREACTION),
         "--project-id", shadow_project,
         "--state-revision", state_revision],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    parsed = {}
    try:
        parsed = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        parsed = {"raw_stdout": result.stdout[-500:]}
    return {
        "available": True,
        "exit_code": result.returncode,
        "verdict": "premises_hold" if result.returncode == 0 else "premises_violated",
        "reason_codes": parsed.get("reason_codes", []),
        "detail": parsed.get("detail"),
    }


def classify_turn(
    turn_events: list[dict[str, Any]],
    cl_state: dict[str, Any],
    *,
    timeline: list[dict[str, Any]] | None = None,
    turn_ts: str | None = None,
) -> dict[str, Any]:
    """对比宿主上下文引用与 CL 在【该 turn 时点】的当前态，产出影子差异分类。

    timeline（可选）：由 build_shadow_state.py 产出的逐事件状态时间线
    [{as_of, current_states}]。提供时按 turn 时间戳取 <= as_of 的最近快照，
    避免用最终态错判历史 turn（方案取消后又被恢复的时序场景必需）。
    """
    stale_in_host: list[dict[str, Any]] = []
    missing_in_host: list[dict[str, Any]] = []
    extra_in_host: list[dict[str, Any]] = []

    # CL 在该 turn 时点的当前态
    cl_active: dict[str, Any] = {}
    snapshot_entry = None
    if timeline and turn_ts:
        earlier = [t for t in timeline if (t.get("as_of") or "") <= turn_ts]
        if earlier:
            snapshot_entry = earlier[-1]
            cl_active = dict(snapshot_entry.get("current_states") or {})
    if not cl_active and snapshot_entry is None:
        # 无时间线：退回最终态（不推荐，仅兜底）
        for node in (cl_state.get("nodes") or {}).values():
            if isinstance(node, dict) and node.get("status") == "active" and node.get("entity_ref"):
                cl_active.setdefault(str(node["entity_ref"]), node)
        cl_active = {
            entity: {"state": node.get("state"), "content": node.get("content")}
            if not isinstance(node, dict) or "state" not in node else node
            for entity, node in cl_active.items()
        }

    def cl_state_of(entity: str) -> str | None:
        value = cl_active.get(entity)
        if isinstance(value, dict):
            return value.get("state")
        return value

    # CL 已知实体全集（任一时间线快照中出现过的 entity）。
    # 已知但当前无态 = 该实体已被终结（如 cancelled），宿主仍引用旧值同样是 stale。
    known_entities: set[str] = set()
    for entry in timeline or []:
        known_entities.update((entry.get("current_states") or {}).keys())
    if not timeline:
        known_entities = set(cl_active.keys())

    host_refs: dict[str, dict[str, Any]] = {}
    for e in turn_events:
        for ref in e.get("context_refs", []):
            host_refs[str(ref.get("entity"))] = ref

    for entity, ref in host_refs.items():
        if entity not in cl_active:
            if entity in known_entities:
                # CL 有历史但当前无有效状态（终态/被隔离）：宿主引用旧值 = stale
                stale_in_host.append({
                    "entity": entity,
                    "host_state": ref.get("state"),
                    "cl_state": None,
                    "cl_note": "CL 当前无有效状态（已终结或待裁定）",
                    "as_of": snapshot_entry.get("as_of") if snapshot_entry else None,
                })
            else:
                extra_in_host.append({"entity": entity, "host_state": ref.get("state")})
            continue
        cl_node_state = str(cl_state_of(entity) or "").strip().lower()
        host_state = str(ref.get("state") or "").strip().lower()
        if cl_node_state and host_state and cl_node_state != host_state:
            stale_in_host.append({
                "entity": entity,
                "host_state": ref.get("state"),
                "cl_state": cl_state_of(entity),
                "as_of": snapshot_entry.get("as_of") if snapshot_entry else None,
            })
    for entity in cl_active:
        if entity not in host_refs:
            missing_in_host.append({"entity": entity, "cl_state": cl_state_of(entity)})

    return {
        "stale_in_host": stale_in_host,
        "missing_in_host": missing_in_host,
        "extra_in_host": extra_in_host,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-jsonl", help="宿主 hook 事件 JSONL")
    source.add_argument("--scenario", help="场景定义（配合 --simulate）")
    parser.add_argument("--simulate", action="store_true", help="把场景定义展开为宿主事件流（钉扎前管线验证）")
    parser.add_argument("--shadow-project", default="abu_modern_host_shadow",
                        help="影子命名空间项目名（绝不等于主项目）")
    parser.add_argument("--out", default="traces/shadow_diff_report.json")
    parser.add_argument("--with-cl-processing", action="store_true",
                        help="逐 turn 调 CL run_auto_turn --dry-run（消耗 Extractor API）")
    args = parser.parse_args()

    if args.shadow_project == "abu_modern":
        print("REFUSED: 影子命名空间不得等于主项目（单写者边界）", file=sys.stderr)
        return 2

    if args.scenario:
        if not args.simulate:
            print("--scenario 需要 --simulate", file=sys.stderr)
            return 2
        scenario = load_json(Path(args.scenario))
        events = scenario_to_events(scenario)
    else:
        events = [json.loads(line) for line in Path(args.from_jsonl).read_text(encoding="utf-8").splitlines() if line.strip()]

    cl_projects_dir = CL_HOME / "graph" / "projects"
    shadow_dir = cl_projects_dir / args.shadow_project
    shadow_raw_dir = shadow_dir / "raw" / "s001"

    cl_state_path = shadow_dir / "graph_state.json"
    cl_state = load_json(cl_state_path) if cl_state_path.exists() else {"nodes": {}, "edges": []}
    timeline_path = shadow_dir / "state_timeline.json"
    timeline = load_json(timeline_path) if timeline_path.exists() else None
    cl_state_revision = None
    if cl_state_path.exists():
        import hashlib as _hashlib
        h = _hashlib.sha256()
        h.update(cl_state_path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        cl_state_revision = f"{int(cl_state.get('turn_counter', 0)):04d}:{h.hexdigest()[:12]}"

    turn_reports = []
    checkpoints = set()
    if args.scenario:
        scenario = load_json(args.scenario)
        checkpoints = set(scenario.get("pollution_checkpoints", []))

    for turn_id, turn_events in group_by_turn(events).items():
        anchor = write_raw_anchors(shadow_raw_dir, turn_id, turn_events)
        turn_ts = next((e.get("ts") for e in turn_events if e.get("ts")), None)
        classification = classify_turn(turn_events, cl_state, timeline=timeline, turn_ts=turn_ts)
        preaction = None
        if cl_state_revision is not None and (not checkpoints or turn_id in checkpoints):
            preaction = call_verify_preaction(args.shadow_project, cl_state_revision)
        turn_reports.append({
            "turn_id": turn_id,
            "raw_anchor": str(anchor.relative_to(CL_HOME)) if anchor.is_relative_to(CL_HOME) else str(anchor),
            "is_pollution_checkpoint": turn_id in checkpoints if checkpoints else False,
            "host_context_ref_count": sum(len(e.get("context_refs", [])) for e in turn_events),
            "classification": classification,
            "verify_preaction": preaction,
        })

    stale_hits = sum(1 for t in turn_reports if t["classification"]["stale_in_host"])
    report = {
        "kind": "shadow_diff_report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "shadow_project": args.shadow_project,
        "source": args.scenario or args.from_jsonl,
        "simulate": bool(args.simulate),
        "with_cl_processing": bool(args.with_cl_processing),
        "turn_count": len(turn_reports),
        "turns_with_stale_in_host": stale_hits,
        "turns": turn_reports,
        "caveat": (
            "影子模式只证明输入会变（stale_in_host 命中），不证明改变后的行动更好；"
            "行动收益必须由受控成对运行（paired run）证明。"
        ),
    }
    write_json(Path(args.out), report)
    print(f"shadow diff: {len(turn_reports)} turns, stale_in_host hits: {stale_hits}")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
