#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CL v0.1 端到端自动运行器（单轮）：装配刷新 → 宿主会话 → CL 轮处理。

一条命令完成一轮（修复 P2 发现的"会话起始装配时机"缺陷——装配先于行动）：
    0. 会话起始/每轮装配：控制文件刷新到当前权威图 revision + manifest 重生成
    1. opencode run [-c] "<用户消息>"（隔离项目内）
    2. CL 轮处理（调用主仓库 pilot_turn_driver.py：抽取→reconcile→apply→manifest→AGENTS.md→控制文件）

用法：
    python tools/cl_turn.py --project <项目目录> --cl-project <名> --turn <N> \
        --text "<用户消息>" [--new-session] [--timeout 420]
轮次计数器存于 .opencode/cl_turn_state.json（--turn 缺省自动递增）。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cl_common import current_revision, load_json, project_paths, refresh_control, write_json  # noqa: E402

CL_HOME = Path("D:/CCXXLESSON/contextledger")
OPENCODE_BIN = shutil.which("opencode") or shutil.which("opencode.cmd") or "opencode"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="opencode 任务项目目录")
    parser.add_argument("--cl-project", required=True)
    parser.add_argument("--text", required=True, help="本轮用户消息")
    parser.add_argument("--turn", type=int, default=None, help="轮次号（缺省自动 +1）")
    parser.add_argument("--new-session", action="store_true", help="新会话（不加 -c）")
    parser.add_argument("--timeout", type=int, default=420, help="宿主会话超时秒数")
    parser.add_argument("--env-file", default=None, help="CL 抽取用 env（缺省 CL 主仓库 env）")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    pp = project_paths(project)
    control_path = pp["control_file"]
    control = load_json(control_path) if control_path.exists() else {"gate": True, "inject": True}
    cl_project = control.get("cl_project") or args.cl_project
    cl_home = Path(control.get("cl_home") or CL_HOME)

    graph = cl_home / "graph" / "projects" / cl_project / "graph_state.json"
    if not graph.exists():
        print(f"ERROR: CL 图不存在（先完成首轮 CL 处理）: {graph}")
        return 1

    # 0. 会话起始/每轮装配：控制文件刷新 + manifest 重生成（先于行动）
    revision = current_revision(graph)
    manifest = cl_home / "graph" / "projects" / cl_project / "run" / "assembler_manifest.pre_turn.json"
    subprocess.run(
        [sys.executable, str(cl_home / "graph" / "scripts" / "assembler_manifest.py"),
         "--project-id", cl_project, "--turn-id", "pre_turn", "--out", str(manifest)],
        capture_output=True, text=True,
    )
    refresh_control(control_path, str(cl_home), cl_project, graph, manifest if manifest.exists() else None, None,
                    gate=control.get("gate", True), inject=control.get("inject", True))
    print(f"[装配] revision -> {revision}")

    # 1. 宿主会话
    turn_state_path = pp["control_file"].parent / "cl_turn_state.json"
    state = {}
    if turn_state_path.exists():
        state = json.loads(turn_state_path.read_text(encoding="utf-8"))
    session_flag = [] if args.new_session else ["-c"]
    env_cmd = [OPENCODE_BIN, "run", *session_flag, args.text]
    merged_env = {**__import__("os").environ,
                  "CL_SHADOW_TRACE": str(project.parent / "traces" / f"{cl_project}_turn_{revision[:4]}.jsonl")}
    print(f"[宿主] opencode run {'-c ' if not args.new_session else ''}{args.text[:40]}...")
    result = subprocess.run(env_cmd, cwd=project, env=merged_env,
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=args.timeout)
    answer_tail = (result.stdout or "")[-600:]
    print(f"[宿主] rc={result.returncode}\n{answer_tail}")

    # 2. CL 轮处理（抽取→…→AGENTS.md/控制刷新）
    turn_num = args.turn or (int(state.get("last_turn", 0)) + 1)
    driver = cl_home / "graph" / "scripts" / "pilot_turn_driver.py"
    driver_cmd = [sys.executable, str(driver),
                  "--cl-project", cl_project, "--turn-num", str(turn_num),
                  "--user-text", args.text,
                  "--trace", str(merged_env["CL_SHADOW_TRACE"]),
                  "--control-file", str(control_path),
                  "--agents-md", str(pp["agents_md"]),
                  "--env-file", args.env_file or "env"]
    print(f"[CL] pilot_turn_driver turn {turn_num} ...")
    drv = subprocess.run(driver_cmd, cwd=str(cl_home), capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    tail = (drv.stdout or "")[-400:] + (drv.stderr or "")[-400:]
    print(tail)
    state["last_turn"] = turn_num
    write_json(turn_state_path, state)
    return 0 if drv.returncode == 0 else drv.returncode


if __name__ == "__main__":
    sys.exit(main())
