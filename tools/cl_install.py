#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CL v0.1 安装：向目标项目装插件 + 控制文件 + AGENTS.md 备份。

用法：
    python tools/cl_install.py --project <项目目录> --cl-project <CL项目名> [--cl-home <路径>]
安装内容：
    1. 备份既有 AGENTS.md（若有）→ .opencode/backup/AGENTS.md.preinstall
    2. 复制 cl-v0-inject.js → .opencode/plugin/
    3. 写 .opencode/cl_v0.json（gate+inject 开启）
停用：python tools/cl_disable.py --project <项目目录>
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cl_common import DEFAULT_CL_HOME, project_paths  # noqa: E402

PLUGIN_SOURCE = Path(__file__).resolve().parent.parent / "opencode" / "plugin" / "cl-v0-inject.js"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="目标项目目录（opencode 在此启动）")
    parser.add_argument("--cl-project", required=True, help="CL 侧项目名（如 pilot_p1）")
    parser.add_argument("--cl-home", default=DEFAULT_CL_HOME, help="CL 主仓库路径")
    parser.add_argument("--init-cl", action="store_true", help="CL 侧不存在时自动初始化（种子图+目录）")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    if not project.exists():
        print(f"ERROR: 项目目录不存在: {project}")
        return 1

    cl_home = Path(args.cl_home)
    cl_project_dir = cl_home / "graph" / "projects" / args.cl_project
    if not cl_project_dir.exists():
        if not args.init_cl:
            print(f"ERROR: CL 项目不存在: {cl_project_dir}（加 --init-cl 自动初始化）")
            return 1
        (cl_project_dir / "run").mkdir(parents=True, exist_ok=True)
        (cl_project_dir / "patches").mkdir(exist_ok=True)
        (cl_project_dir / "quarantine").mkdir(exist_ok=True)
        (cl_project_dir / "reports").mkdir(exist_ok=True)
        (cl_home / "raw" / "projects" / args.cl_project / "s001").mkdir(parents=True, exist_ok=True)
        (cl_project_dir / "graph_state.seed.json").write_text(
            '{"turn_counter": 0, "nodes": {}, "edges": []}', encoding="utf-8")
        (cl_project_dir / "graph_state.json").write_text(
            '{"turn_counter": 0, "nodes": {}, "edges": []}', encoding="utf-8")
        print(f"initialized CL project: {cl_project_dir}")

    pp = project_paths(project)
    if not PLUGIN_SOURCE.exists():
        print(f"ERROR: 找不到插件源文件: {PLUGIN_SOURCE}")
        return 1

    pp["plugin_dir"].mkdir(parents=True, exist_ok=True)
    pp["backup_dir"].mkdir(parents=True, exist_ok=True)

    # 1. 备份既有 AGENTS.md（幂等：已有备份不覆盖）
    if pp["agents_md"].exists() and not (pp["backup_dir"] / "AGENTS.md.preinstall").exists():
        shutil.copy2(pp["agents_md"], pp["backup_dir"] / "AGENTS.md.preinstall")
        print(f"backed up AGENTS.md -> {pp['backup_dir'].name}/AGENTS.md.preinstall")

    # 2. 插件
    shutil.copy2(PLUGIN_SOURCE, pp["plugin_file"])
    print(f"installed plugin: {pp['plugin_file']}")

    # 3. 控制文件（首次安装写模板；已存在则保留用户/驱动器状态，仅确保键存在）
    # gate 默认 false（2026-09-25 收口裁定：关口降为可选、默认关闭；代码与
    # blocktest 证据归档保留，需要时显式置 true）
    control = pp["control_file"]
    if not control.exists():
        control.write_text(
            '{\n  "gate": false,\n  "inject": true,\n'
            f'  "cl_home": "{args.cl_home.replace(chr(92), "/")}",\n'
            f'  "cl_project": "{args.cl_project}"\n}}\n',
            encoding="utf-8",
        )
        print(f"created control file: {control}")
    else:
        print(f"control file already exists, kept: {control}")

    print("\n安装完成。下一步请运行自检：")
    print(f"  python tools/cl_selfcheck.py --project {project}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
