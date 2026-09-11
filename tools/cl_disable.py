#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CL v0.1 停用恢复：移除插件与控制文件、还原装前 AGENTS.md，宿主回到装前状态。

用法：
    python tools/cl_disable.py --project <项目目录>
行为：
    1. 移除 .opencode/plugin/cl-v0-inject.js（若无其他插件且 plugin 目录空则一并移除）
    2. 移除 .opencode/cl_v0.json
    3. AGENTS.md：若装前有备份 → 还原备份；若 AGENTS.md 为 CL 所建（装前无）→ 移除
    4. CL 侧数据（graph/quarantine/manifest）保留不动——停用只影响宿主项目
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cl_common import project_paths  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    pp = project_paths(Path(args.project).resolve())
    actions: list[str] = []

    if pp["plugin_file"].exists():
        pp["plugin_file"].unlink()
        actions.append("移除插件")
    if pp["control_file"].exists():
        pp["control_file"].unlink()
        actions.append("移除控制文件")

    backup = pp["backup_dir"] / "AGENTS.md.preinstall"
    if backup.exists():
        shutil.copy2(backup, pp["agents_md"])
        actions.append("AGENTS.md 还原为装前备份")
    elif pp["agents_md"].exists() and "CL-PILOT-STATE" in pp["agents_md"].read_text(encoding="utf-8"):
        pp["agents_md"].unlink()
        actions.append("AGENTS.md 为 CL 所建（装前不存在）→ 已移除")

    # plugin 目录空则清理
    try:
        pp["plugin_dir"].rmdir()
        actions.append("移除空 plugin 目录")
    except OSError:
        pass

    if not actions:
        print("未发现 CL 安装痕迹（已停用或从未安装）。")
        return 0
    print("停用完成：" + "；".join(actions))
    print("宿主已回到装前状态。CL 侧历史数据（graph/quarantine）保留在 CL 主仓库。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
