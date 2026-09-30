#!/usr/bin/env python3
"""cl_report.py —— CL 试用记录聚合与使用报告生成器（v0.1，配套 host tools/）

用途：试用结束后，把 cl_turn 每轮自动落盘的原料聚合成一份 usage_report.md：
  项目侧：.opencode/cl_v0.json（cl_home/cl_project/gate 等）、traces/*.jsonl
  CL  侧：graph/projects/<cl_project>/{patches,run,reports}/*
原则：纯机械聚合，不做价值判定；任何缺失如实标 na，不臆造、不外推。

用法：
  python tools/cl_report.py --project <你的项目目录> [--out <报告路径>]
                           [--extract-rate 0.115] [--host-home <宿主仓路径>]

退出码：0 正常；1 输入条件不满足（如缺少 .opencode/cl_v0.json）。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TOOL = "cl_report.py v0.1"
EXTRACT_MODEL_DEFAULT = "deepseek-v4-flash"


# ---------------------------------------------------------------- 基础读取
def read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_jsonl(p: Path) -> list[dict]:
    out: list[dict] = []
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def git_head(path: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else "na"
    except Exception:
        return "na"


def git_dirty(path: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(path), "status", "--porcelain"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return "na"
        n = len([ln for ln in r.stdout.splitlines() if ln.strip()])
        return f"{n} 项未提交" if n else "clean"
    except Exception:
        return "na"


def snip(s, n=60) -> str:
    if s is None:
        return ""
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s[:n] + ("…" if len(s) > n else "")


# ---------------------------------------------------------------- 数据收集
def collect_traces(project: Path, cl_project: str) -> dict[str, list[dict]]:
    """按轮次归集 trace 事件。trace 文件名形如 <cl_project>_turn_0004.jsonl。"""
    dirs = [project / "traces", project.parent / "traces"]
    files: list[Path] = []
    for d in dirs:
        if d.is_dir():
            files.extend(sorted(d.glob("*.jsonl")))
    seen, uniq = set(), []
    for f in files:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            uniq.append(f)
    per_turn: dict[str, list[dict]] = {}
    for f in uniq:
        m = re.search(r"_turn_(\d+)", f.stem)
        key = m.group(1) if m else f.stem
        per_turn.setdefault(key, []).extend(read_jsonl(f))
    for k in per_turn:
        per_turn[k].sort(key=lambda e: str(e.get("ts") or ""))
    return per_turn


def trace_stats(events: list[dict]) -> dict:
    st = {"boundary": None, "injected": None, "tool_calls": [], "gate_blocks": [],
          "errors": [], "unknown_types": {}}
    for e in events:
        t = e.get("type")
        p = e.get("payload") or {}
        if t == "cl_v0_boundary_dump":
            st["boundary"] = {"message_count": p.get("message_count"),
                              "cl_injection_locations": len(p.get("cl_injection_locations") or []),
                              "in_system": p.get("cl_injection_in_system_message")}
        elif t == "cl_v0_injected":
            st["injected"] = {"states_count": p.get("states_count"),
                              "readiness": p.get("readiness"),
                              "state_revision": p.get("state_revision")}
        elif t == "cl_gate_verdict":
            tool = e.get("tool") or p.get("tool") or "?"
            blocked = (p.get("readiness") == "blocked") or (p.get("exit_code") == 2)
            st["tool_calls"].append(tool)
            if blocked:
                st["gate_blocks"].append({"tool": tool,
                                          "gate": p.get("gate"),
                                          "reason_codes": p.get("reason_codes")})
        elif t == "tool_execute_before":
            st["tool_calls"].append((p.get("tool") or "?"))
        elif t == "cl_v0_error":
            st["errors"].append({"stage": p.get("stage"), "error": snip(p.get("error"), 120)})
        else:
            st["unknown_types"][t] = st["unknown_types"].get(t, 0) + 1
    return st


def user_text_from_prompt(prompt: dict | None) -> tuple[str, str]:
    """从 extractor prompt 的 messages 里取【本轮时间】与【用户】两行（原文进 raw 的组装）。"""
    if not prompt:
        return "na", "na"
    msgs = prompt.get("messages") or []
    for m in msgs:
        if (m.get("role") or "") == "user":
            c = str(m.get("content") or "")
            mt = re.search(r"【本轮时间】\s*(.+)", c)
            mu = re.search(r"【用户】\s*(.+)", c)
            return (mt.group(1).strip() if mt else "na",
                    mu.group(1).strip() if mu else "na")
    return "na", "na"


def patch_transitions(patch: dict) -> list[str]:
    """机械提取一轮 patch 的账本动作（节点/边/取代关系）。"""
    acts: list[str] = []
    for n in patch.get("new_nodes") or []:
        who = n.get("entity_ref") or "(无实体)"
        st = n.get("state") or "(无状态)"
        slot = f"@{n.get('state_slot')}" if n.get("state_slot") else ""
        acts.append(f"新增 {snip(who, 40)}{slot} = {st}｜{snip(n.get('content'), 50)}")
    for u in patch.get("updated_nodes") or []:
        ch = u.get("changes") or {}
        if ch.get("state") or ch.get("status"):
            acts.append(f"更新 {u.get('node_id')}: state={ch.get('state') or '-'}"
                        f" status={ch.get('status') or '-'}｜{snip(u.get('reason'), 40)}")
    for s in patch.get("superseded_nodes") or []:
        acts.append(f"取代 {s.get('node_id')}｜{snip(s.get('reason'), 50)}")
    for e in patch.get("new_edges") or []:
        if e.get("relation") in ("invalidates", "supersedes"):
            acts.append(f"边 {e.get('source')} --{e.get('relation')}--> {e.get('target')}")
    return acts


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="试用项目目录（含 .opencode/cl_v0.json）")
    ap.add_argument("--out", default=None, help="报告输出路径（缺省 <project>/usage_report.md）")
    ap.add_argument("--extract-rate", type=float, default=0.115,
                    help="单次 DeepSeek 抽取估算单价（元，默认 0.115，按 window_budget 既有口径）")
    ap.add_argument("--host-home", default=None, help="宿主仓路径（缺省取本脚本所在仓）")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    control_path = project / ".opencode" / "cl_v0.json"
    if not control_path.exists():
        print(f"[cl_report] 缺少 {control_path}：请先安装（cl_install.py）或确认 --project 指向试用项目。",
              file=sys.stderr)
        return 1
    control = read_json(control_path) or {}
    cl_home = Path(control.get("cl_home") or "").resolve() if control.get("cl_home") else None
    cl_project = control.get("cl_project")
    if not cl_home or not cl_project:
        print("[cl_report] cl_v0.json 缺 cl_home/cl_project 字段，无法定位 CL 账本。", file=sys.stderr)
        return 1
    proj_dir = cl_home / "graph" / "projects" / cl_project
    if not proj_dir.is_dir():
        print(f"[cl_report] CL 项目目录不存在：{proj_dir}", file=sys.stderr)
        return 1
    host_home = Path(args.host_home).resolve() if args.host_home \
        else Path(__file__).resolve().parent.parent

    # ---- 轮次归集：以 patches 为权威轮次清单
    patch_files = sorted((proj_dir / "patches").glob("patch_*.json")) if (proj_dir / "patches").is_dir() else []
    retry_files = [p for p in patch_files if ".retry_" in p.name]
    main_patches = [p for p in patch_files if ".retry_" not in p.name]
    turns: dict[int, dict] = {}
    for pf in main_patches:
        tid = int((pf.stem.split("_")[1]))
        turns.setdefault(tid, {})["patch"] = pf
        turns[tid]["retry"] = [r for r in retry_files if f"patch_{tid:03d}.retry_" in r.name]
    # reports：turn_NNN 或 turn_NNN_pilot 两种目录名都兼容
    for rd in sorted((proj_dir / "reports").glob("turn_*")) if (proj_dir / "reports").is_dir() else []:
        m = re.match(r"turn_(\d+)", rd.name)
        if not m:
            continue
        tid = int(m.group(1))
        meta = sorted(rd.glob("extractor_meta*.json"))
        prompt = sorted(rd.glob("prompt.turn_*"))
        turns.setdefault(tid, {})["report_dir"] = rd
        turns[tid]["meta_files"] = meta
        turns[tid]["prompt_file"] = prompt[0] if prompt else None
    # manifests
    manifest_files = {}
    run_dir = proj_dir / "run"
    if run_dir.is_dir():
        for mf in run_dir.glob("assembler_manifest.turn_*.json"):
            m = re.search(r"turn_(\d+)", mf.stem)
            if m:
                manifest_files[int(m.group(1))] = mf
    # traces
    traces = collect_traces(project, cl_project)
    trace_turn_ids = {int(t) for t in traces if t.isdigit()}

    turn_ids = sorted(turns.keys())
    all_turn_ids = sorted(set(turn_ids) | trace_turn_ids | set(manifest_files.keys()))

    # ---- 逐轮取数
    rows = []
    for tid in all_turn_ids:
        info = turns.get(tid, {})
        kind = "装配" if (not info.get("patch") and not info.get("meta_files")) else "任务"
        patch = read_json(info["patch"]) if info.get("patch") else None
        meta_files = info.get("meta_files") or []
        metas = [read_json(m) for m in meta_files]
        metas = [m for m in metas if m]
        finished = [m.get("finished_at") for m in metas if m.get("finished_at")]
        prompt = read_json(info["prompt_file"]) if info.get("prompt_file") else None
        when, utext = user_text_from_prompt(prompt)
        man = read_json(manifest_files[tid]) if tid in manifest_files else None
        ts = trace_stats(traces.get(f"{tid:04d}", [])) if f"{tid:04d}" in traces \
            else trace_stats(traces.get(str(tid), []))
        acts = patch_transitions(patch) if patch else []
        rows.append({
            "turn": tid, "kind": kind, "when": when, "utext": utext,
            "n_extract": len(meta_files), "finished_at": sorted(finished)[-1] if finished else None,
            "n_tool": len(ts["tool_calls"]), "n_block": len(ts["gate_blocks"]),
            "errors": ts["errors"], "gate_blocks": ts["gate_blocks"],
            "injected": ts["injected"], "boundary": ts["boundary"],
            "readiness": (man or {}).get("readiness"),
            "reason_codes": (man or {}).get("reason_codes") or [],
            "acts": acts, "retry": len(info.get("retry") or []),
            "has_patch": bool(info.get("patch")), "has_report": bool(info.get("meta_files")),
            "has_manifest": tid in manifest_files,
            "has_trace": (f"{tid:04d}" in traces) or (str(tid) in traces),
            "unknown_types": ts["unknown_types"],
        })

    # ---- 汇总计数
    n_extract_total = sum(r["n_extract"] for r in rows)
    n_tool_total = sum(r["n_tool"] for r in rows)
    n_block_total = sum(r["n_block"] for r in rows)
    n_error_total = sum(len(r["errors"]) for r in rows)
    n_retry_total = sum(r["retry"] for r in rows)
    gate_now = control.get("gate")
    gate_recorded_turns = [r["turn"] for r in rows if r["n_tool"] > 0]
    gate_recorded = len(gate_recorded_turns) > 0
    final_states = (read_json(run_dir / "current_states.json") or {}).get("states", {}) \
        if run_dir.is_dir() else {}
    models = set()
    for pf in (proj_dir / "reports").glob("*/extractor_meta*.json") if (proj_dir / "reports").is_dir() else []:
        m = read_json(pf) or {}
        if m.get("model"):
            models.add(m["model"])

    # ---- 组装报告
    out = Path(args.out).resolve() if args.out else project / "usage_report.md"
    L: list[str] = []
    A = L.append
    A(f"# CL 试用使用报告（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）")
    A("")
    A(f"> 生成工具：{TOOL} ｜ 性质：**机械聚合，不含价值判定**；缺失项如实标 `na`。")
    A("")
    A("## 0. 试前条件（版本钉）")
    A("")
    A("| 项 | 值 |")
    A("|---|---|")
    A(f"| 试用项目目录 | `{project}` |")
    A(f"| CL 账本项目 | `{cl_project}` |")
    A(f"| 主仓（cl_home）commit | `{git_head(cl_home)}`（工作区：{git_dirty(cl_home)}） |")
    A(f"| 宿主仓 commit | `{git_head(host_home)}`（工作区：{git_dirty(host_home)}） |")
    A(f"| 门控 gate（安装模板/当前控制文件） | `{gate_now}` |")
    A(f"| 供给 inject | `{control.get('inject')}` |")
    A(f"| 装配版本 expected_state_revision | `{control.get('expected_state_revision')}` |")
    A(f"| 抽取模型（meta 实记） | {', '.join(sorted(models)) if models else 'na'} |")
    A("")
    A("## 1. 轮次总览")
    A("")
    A("| 轮 | 用户输入（摘要） | 抽取次数(含重试) | 工具调用 | 拦截 | 注入状态数 | readiness | 异常 |")
    A("|---|---|---|---|---|---|---|---|")
    for r in rows:
        flag = ",".join(filter(None, [
            f"{r['retry']} 重试" if r["retry"] else "",
            f"{len(r['errors'])} error" if r["errors"] else "",
            "缺patch" if not r["has_patch"] else "",
            "缺report" if not r["has_report"] else "",
            "缺trace" if not r["has_trace"] else "",
        ])) or "-"
        A(f"| {r['turn']}{'（装配）' if r['kind'] == '装配' else ''} | {snip(r['utext'], 28)} | {r['n_extract']} | {r['n_tool']} | "
          f"{r['n_block']} | {(r['injected'] or {}).get('states_count', 'na')} | "
          f"{r['readiness'] or 'na'} | {flag} |")
    A("")
    A("> 注：标注“装配轮”的轮次只发生装配/注入、无任务输入（无 patch/report 属该轮正常形态，"
      "其 error 多为装后首会话尚无 current_states_path 的插件 fail-open 记录，见 §5 已知缺口）。")
    A("")
    A("## 2. 账本动作与状态迁转（按轮次，摘要级）")
    A("")
    any_act = False
    for r in rows:
        if r["acts"]:
            any_act = True
            A(f"**Turn {r['turn']}**（{snip(r['utext'], 40)}）")
            for a in r["acts"]:
                A(f"- {a}")
    if not any_act:
        A("- na（未采集到任何 patch 动作）")
    A("")
    A("## 3. 供给面终态（current_states.json，最新装配）")
    A("")
    if final_states:
        A("| 键 | 当前态 |")
        A("|---|---|")
        for k, v in final_states.items():
            A(f"| {k} | {snip(v, 70)} |")
    else:
        A("- na")
    A("")
    A("## 4. 注入与边界记录（trace，逐轮）")
    A("")
    A("| 轮 | 最终消息数 | 注入标记命中 | 注入状态数 | 装配版本 |")
    A("|---|---|---|---|---|")
    for r in rows:
        b, i = r["boundary"], r["injected"]
        A(f"| {r['turn']} | {(b or {}).get('message_count', 'na')} | "
          f"{(b or {}).get('cl_injection_locations', 'na')} | "
          f"{(i or {}).get('states_count', 'na')} | {(i or {}).get('state_revision', 'na')} |")
    A("")
    A("## 5. 异常与缺口")
    A("")
    if n_block_total:
        A(f"**门控拦截 {n_block_total} 次**：")
        for r in rows:
            for b in r["gate_blocks"]:
                A(f"- Turn {r['turn']} tool={b['tool']} gate={b['gate']} "
                  f"reason_codes={b['reason_codes']}")
    else:
        A(f"- 门控拦截：0 次（注意：{'gate=true 有记录' if gate_recorded else '**gate=false 或未开，无工具级记录**'}）")
    if n_error_total:
        A(f"- 插件错误事件 {n_error_total} 次：")
        for r in rows:
            for e in r["errors"]:
                A(f"  - Turn {r['turn']} stage={e['stage']} {e['error']}")
    else:
        A("- 插件错误事件：0")
    if n_retry_total:
        A(f"- 抽取重试 patch {n_retry_total} 个（.retry_N 文件）")
    else:
        A("- 抽取重试：0")
    missing = []
    for r in rows:
        gaps = [name for name, ok in (("patch", r["has_patch"]), ("report", r["has_report"]),
                                      ("manifest", r["has_manifest"]), ("trace", r["has_trace"]))
                if not ok]
        if gaps:
            missing.append(f"Turn {r['turn']}: 缺 {'/'.join(gaps)}")
    A(f"- 原料完整性问题：{'；'.join(missing) if missing else '无'}")
    unknown_types = sorted({t for r in rows for t in r["unknown_types"]})
    if unknown_types:
        A(f"- trace 中未识别事件类型：{unknown_types}（不影响本报告其他口径）")
    A("")
    A("**已知结构性缺口（装置属性，非本次试用引入，如影响记录请升级装置）**：")
    A("")
    A("1. 工具调用记录依赖 `gate=true`：插件仅在门控开启时经 `tool.execute.before` 发 "
      "`cl_gate_verdict`（工具名级，无参数）；`gate=false` 的轮次 trace 只有注入/边界事件。")
    A("2. CL raw 的工具摘要口径与现行插件不匹配（driver `tool_summary_from_trace` 解析旧格式 "
      "`tool_execute_before`，插件已不发该事件）——CL 账本 raw 中的“本轮工具活动摘要”在用户路径下"
      "可能为空；本报告的工具数来自 trace 直接解析，不受该缺口影响。")
    A("")
    A("## 6. 成本估算")
    A("")
    A(f"- DeepSeek 抽取调用：**{n_extract_total} 次**（含重试；"
      f"其中重试 patch {n_retry_total} 个）× 单价 {args.extract_rate:.3f} 元 "
      f"≈ **{n_extract_total * args.extract_rate:.2f} 元**")
    A("- 宿主侧 token 成本不在本口径内（由 opencode 侧统计）。")
    A("")
    A("## 7. 裁定区（供指导员/裁定方填写，本工具不预填）")
    A("")
    A("| 项 | 记录 |")
    A("|---|---|")
    A("| 观察（值得注意的现象） |  |")
    A("| 异常裁定 |  |")
    A("| 试用结论 |  |")
    A("")
    A("---")
    A(f"*本报告由 {TOOL} 生成；原料路径：`{proj_dir}` 与 `{project/'traces'}`（及 `{project.parent/'traces'}`）。"
      "判定口径若需引用，请回到封存判据，不因此报告改变。*")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[cl_report] 报告已生成：{out}")
    print(f"[cl_report] 轮次 {len(rows)}｜抽取 {n_extract_total} 次≈{n_extract_total*args.extract_rate:.2f}元"
          f"｜工具调用 {n_tool_total}｜拦截 {n_block_total}｜错误 {n_error_total}")
    if not gate_recorded:
        print("[cl_report][提示] 本轮试用未见任何工具调用记录——若曾发生工具调用，说明试运行时 gate=false"
              "（或 trace 未落盘）；需要工具级记录时请在试用期间把 .opencode/cl_v0.json 的 gate 置 true。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
