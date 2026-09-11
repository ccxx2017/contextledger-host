#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CL v0.1 安装自检（6 项逐项 PASS/FAIL，任一 FAIL 退出码 1）。

用法：
    python tools/cl_selfcheck.py --project <项目目录> [--cl-project <名>]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cl_common import DEFAULT_CL_HOME, current_revision, load_json, project_paths  # noqa: E402

RESULTS: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((ok, name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--cl-project", default=None, help="缺省从控制文件读取")
    parser.add_argument("--cl-home", default=DEFAULT_CL_HOME)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    pp = project_paths(project)

    # 1. 插件就位
    check("1. 插件已安装", pp["plugin_file"].exists(), str(pp["plugin_file"]))

    # 2. 控制文件可解析且含必需键
    control = {}
    ok2 = False
    detail2 = ""
    try:
        control = load_json(pp["control_file"])
        missing = [k for k in ("cl_home", "cl_project", "gate", "inject") if k not in control]
        ok2 = not missing
        detail2 = f"缺键: {missing}" if missing else "键完整"
    except Exception as e:
        detail2 = f"不可解析: {e}"
    check("2. 控制文件", ok2, detail2)

    cl_project = args.cl_project or control.get("cl_project") or ""
    cl_home = Path(args.cl_home if args.cl_home != DEFAULT_CL_HOME else control.get("cl_home", DEFAULT_CL_HOME))

    # 3. CL 主仓库引擎可达
    verify = cl_home / "graph" / "scripts" / "verify_preaction.py"
    check("3. CL 引擎（verify_preaction.py）", verify.exists(), str(verify))

    # 4. verify_preaction 可执行（对目标 CL 项目当前图运行一次）
    graph = cl_home / "graph" / "projects" / cl_project / "graph_state.json"
    ok4, detail4 = False, f"CL 项目图不存在: {graph}"
    if graph.exists():
        r = subprocess.run(
            [sys.executable, str(verify), "--project-id", cl_project, "--state-revision", "0000:selfcheck"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        # selfcheck 用占位 revision，预期 exit 2（STALE）——能返回 2 恰证明引擎工作
        ok4 = r.returncode == 2 and "STATE_REVISION_STALE" in (r.stdout or "")
        detail4 = f"exit={r.returncode}（占位 revision 探测，2=引擎正常）"
    check("4. verify_preaction 引擎响应", ok4, detail4)

    # 5. CL 侧装配产物可读（若有 manifest/current_states）
    states = cl_home / "graph" / "projects" / cl_project / "run" / "current_states.json"
    ok5, detail5 = True, "尚无 current_states.json（首轮前属正常）"
    if states.exists():
        try:
            data = load_json(states)
            detail5 = f"states={len(data.get('states', {}))} 项"
        except Exception as e:
            ok5, detail5 = False, f"损坏: {e}"
    check("5. CL 装配产物", ok5, detail5)

    # 6. AGENTS.md 可写（或备份存在）
    ok6 = pp["backup_dir"].exists() and (pp["agents_md"].exists() or not pp["agents_md"].exists())
    try:
        pp["agents_md"].write_text(pp["agents_md"].read_text(encoding="utf-8") if pp["agents_md"].exists() else "", encoding="utf-8")
        ok6 = True
        detail6 = "可读写"
    except Exception as e:
        detail6 = f"不可写: {e}"
    check("6. AGENTS.md 供给通道可写", ok6, detail6)

    passed = sum(1 for ok, _, _ in RESULTS if ok)
    print(f"\n自检结果: {passed}/{len(RESULTS)} PASS" + (" — 可以试用" if passed == len(RESULTS) else " — 存在 FAIL 项，见上"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
