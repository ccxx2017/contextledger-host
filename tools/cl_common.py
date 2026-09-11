#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CL v0.1 试用版工具共享库（安装/自检/停用/恢复/端到端）。"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

DEFAULT_CL_HOME = "D:/CCXXLESSON/contextledger"


def load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def project_paths(project_dir: Path) -> dict[str, Path]:
    oc = project_dir / ".opencode"
    return {
        "opencode_dir": oc,
        "plugin_dir": oc / "plugin",
        "plugin_file": oc / "plugin" / "cl-v0-inject.js",
        "control_file": oc / "cl_v0.json",
        "agents_md": project_dir / "AGENTS.md",
        "backup_dir": oc / "backup",
    }


def current_revision(graph_state: Path) -> str:
    h = hashlib.sha256()
    h.update(graph_state.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
    data = json.loads(graph_state.read_text(encoding="utf-8"))
    return f"{int(data.get('turn_counter', 0)):04d}:{h.hexdigest()[:12]}"


def refresh_control(control_file: Path, cl_home: str, cl_project: str,
                    graph_state: Path, manifest_path: Path | None,
                    states_path: Path | None, *, gate: bool = True, inject: bool = True) -> dict[str, Any]:
    """会话起始装配 / 每轮装配的公共实现：刷新宿主控制文件到当前权威图。"""
    control: dict[str, Any] = {}
    if control_file.exists():
        try:
            control = load_json(control_file)
        except Exception:
            control = {}
    control.update({
        "cl_home": cl_home.replace("\\", "/"),
        "cl_project": cl_project,
        "gate": gate,
        "inject": inject,
        "expected_state_revision": current_revision(graph_state),
        "manifest_path": str(manifest_path).replace("\\", "/") if manifest_path else control.get("manifest_path"),
        "current_states_path": str(states_path).replace("\\", "/") if states_path else control.get("current_states_path"),
    })
    write_json(control_file, control)
    return control


def render_agents_md(states: dict[str, str], readiness: str, reason_codes: list[str],
                     revision: str, *, warning: str | None = None) -> str:
    lines = ["# CL-PILOT-STATE", ""]
    for k, v in states.items():
        lines.append(f"{k} = {v}")
    lines.append("")
    if warning:
        lines.append(f"【CL 警告】{warning}")
    rc = f"（{', '.join(reason_codes)}）" if reason_codes else ""
    lines += [f"【CL 就绪度】{readiness}{rc}", f"【CL 版本】{revision}",
              "【CL 使用规则】以上为经裁定机制维护的当前态；与其冲突的早期记忆应以此为准。"]
    return "\n".join(lines) + "\n"
