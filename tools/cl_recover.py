#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CL v0.1 故障恢复：三种常见故障的一键恢复。

用法：
    python tools/cl_recover.py --project <项目目录> --cl-project <CL项目名> --issue agents_md
    python tools/cl_recover.py --project <项目目录> --cl-project <CL项目名> --issue control_file
    python tools/cl_recover.py --project <项目目录> --cl-project <CL项目名> --issue quarantine

    agents_md     AGENTS.md 缺失/损坏 → 从 CL 当前图 + manifest 重建
    control_file  控制文件损坏 → 重建（刷新到当前权威图 revision）
    quarantine    查看隔离裁定队列 → sync + check 报告（裁定后按 S6 流程销账）
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cl_common import current_revision, load_json, project_paths, render_agents_md  # noqa: E402

CL_HOME = Path("D:/CCXXLESSON/contextledger")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--cl-project", required=True)
    parser.add_argument("--issue", required=True, choices=["agents_md", "control_file", "quarantine"])
    args = parser.parse_args()

    pp = project_paths(Path(args.project).resolve())
    graph = CL_HOME / "graph" / "projects" / args.cl_project / "graph_state.json"
    manifest = CL_HOME / "graph" / "projects" / args.cl_project / "run" / "assembler_manifest.recovery.json"

    if args.issue == "agents_md":
        if not graph.exists():
            print(f"ERROR: CL 图不存在: {graph}")
            return 1
        states: dict[str, str] = {}
        for node in load_json(graph).get("nodes", {}).values():
            if (node.get("status") or "active") == "active" and node.get("entity_ref"):
                st = node.get("state")
                if st and str(st).strip().lower() not in {"unknown", "null"}:
                    key = f"{node['entity_ref']}@{node['state_slot']}" if node.get("state_slot") else str(node["entity_ref"])
                    states[key] = str(st)
        readiness, codes = "ready", []
        subprocess.run(
            [sys.executable, str(CL_HOME / "graph" / "scripts" / "assembler_manifest.py"),
             "--project-id", args.cl_project, "--turn-id", "recovery", "--out", str(manifest)],
            capture_output=True, text=True,
        )
        if manifest.exists():
            m = load_json(manifest)
            readiness, codes = m.get("readiness", "ready"), m.get("reason_codes", [])
        pp["agents_md"].write_text(
            render_agents_md(states, readiness, codes, current_revision(graph),
                             warning="本文件由 cl_recover 重建"), encoding="utf-8")
        print(f"AGENTS.md 已重建（states={len(states)} readiness={readiness}）")
        return 0

    if args.issue == "control_file":
        if not graph.exists():
            print(f"ERROR: CL 图不存在: {graph}")
            return 1
        manifest = CL_HOME / "graph" / "projects" / args.cl_project / "run" / "assembler_manifest.recovery.json"
        subprocess.run(
            [sys.executable, str(CL_HOME / "graph" / "scripts" / "assembler_manifest.py"),
             "--project-id", args.cl_project, "--turn-id", "recovery", "--out", str(manifest)],
            capture_output=True, text=True,
        )
        from cl_common import refresh_control
        control = refresh_control(pp["control_file"], str(CL_HOME), args.cl_project, graph, manifest if manifest.exists() else None, None)
        print(f"控制文件已重建：revision={control['expected_state_revision']}")
        return 0

    if args.issue == "quarantine":
        subprocess.run([sys.executable, str(CL_HOME / "graph" / "scripts" / "quarantine_register.py"),
                        "sync", "--project-id", args.cl_project], check=False)
        r = subprocess.run([sys.executable, str(CL_HOME / "graph" / "scripts" / "quarantine_register.py"),
                            "check", "--project-id", args.cl_project, "--current-turn", "9999"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout or r.stderr)
        print("裁定方法：编辑 quarantine_register.json 的 disposition（unreviewed→requeued/accepted_loss/superseded），"
              "重跑 assembler_manifest 后 blocked 解除（S6 流程）。")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
