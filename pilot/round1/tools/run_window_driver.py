#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""round1 正式窗口驱动（按 WINDOW_PROCEDURE.md 执行）——只编排既有工具，不新增装置代码。

用法：
    python run_window.py --scenario <scenario_id> [--run-root <dir>]

每场景：
  1. 布景：seeds/<scenario>/ → <run_root>/<scenario>/<arm_dir>/task-project/（两臂同源），
     布景快照写 seeding_manifest.json；reassignment_recovery 额外与场景 JSON 的
     seed_files 字段逐字节核对；
  2. cl_v0 臂：cl_install --init-cl → cl_selfcheck（必须 6/6）→ 逐轮 cl_turn.py；
  3. baseline 臂：make_summary_recovery → check_info_floor（必须退出码 0）→ 逐轮
     opencode.exe 直调；会话 2 首轮注入摘要；
  4. 每轮采集 answers/turn_NNN.json（rc/stdout/stderr/秒数/user_text/cmd）；
     每轮结束对两臂 task-project 做文件哈希快照 hashes/turn_NNN.json；
  5. 投递核验（M3）：会话 2 首轮后核验 baseline user_text 含摘要全文（或首行标记 +
     全部 external_event 三元组）；不含 = 装置故障 → 停该场景；
  6. 拦截识别：cl_v0 轮次扫 CL_READINESS_BLOCKED / CL_GATE_BLOCKED 错误串 +
     trace cl_gate_verdict 事件 → blocks/turn_NNN.json；首个拦截打印人工核验标记；
  7. 预算记账：每 5 轮追加 window_budget.json（宿主轮次/抽取调用/DeepSeek 估算）。

断点续跑：已有 answers/turn_NNN.json 的轮次跳过。失败（rc≠0/超时/自检不过/信息量
不过/投递不过）→ 停该场景并写 BLOCKED 标记，由执行方处置，不静默重试。

中性路径名（第八号裁定书 Round 2 前置 2）：两臂在盘目录用中性名（workspace-a/b），
臂映射不外泄到运行目录内——映射写驱动侧 temp/round1_trial/arm_map_<run>.json，
运行目录内所有 JSON 件（seeding_manifest/git_heads/hashes/HALTED/delivery_check）
一律用中性键。CL 项目名同去臂名（round1_w<short><suffix>_p1）。残余泄漏面：
trace 文件名由 cl_turn 装置生成（原含项目名，已随项目名中性化）；模型若主动越目录
窥探运行根仍可能推断——此残余与 round1 污染运行的跨臂窥探同型，如实披露。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOST = Path(r"D:\CCXXLESSON\contextledger-host")
CL_HOME = Path(r"D:\CCXXLESSON\contextledger")
OPENCODE_EXE = Path(r"C:\Users\Lenovo\AppData\Roaming\npm\node_modules\opencode-ai\bin\opencode.exe")
SEEDS = HOST / "pilot" / "round1" / "seeds"
TURN_TIMEOUT = 420
COST_PER_EXTRACTION = 0.115  # 元/次（行动计划口径）

CL_SHORT = {
    "r1_normal_passage": "r1np",
    "r1_unrelated_dimension": "r1ud",
    "r1_stale_test_result": "r1str",
    "reassignment_recovery": "r1rr",
}

# 中性臂目录名（Round 2 前置 2：路径不得泄露臂身份）。
# 注意：driver 内部仍用逻辑臂名（clv0/baseline）做分支与台账；落盘一律经此映射。
# 历史运行（round1 正式窗口）用臂名落盘，其 data 的 arm 字段即逻辑臂名，无需映射。
ARM_DIR = {"clv0": "workspace-a", "baseline": "workspace-b"}
ARM_MAP_PATH = Path(r"D:\CCXXLESSON\contextledger\temp\round1_trial")


def arm_dir(sc_dir: Path, arm: str) -> Path:
    return sc_dir / ARM_DIR[arm]


def task_project(sc_dir: Path, arm: str) -> Path:
    return arm_dir(sc_dir, arm) / "task-project"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def git_head(tp: Path):
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(tp),
                       capture_output=True, encoding="utf-8")
    return r.stdout.strip() if r.returncode == 0 else None


def rmtree_readonly(p: Path):
    """Windows 安全删除：git 对象文件只读，需先改权限再删。"""
    def onerror(func, path, exc_info):
        try:
            os.chmod(path, 0o700)
            func(path)
        except Exception:
            raise
    shutil.rmtree(p, onerror=onerror)


def answer_file(sc_dir: Path, arm: str, turn_no: int):
    """取该轮的成功尝试（rc=0）；无成功尝试时取最后一次尝试。"""
    cands = sorted((arm_dir(sc_dir, arm) / "answers").glob(f"turn_{turn_no:03d}*.json"))
    if not cands:
        return None
    for p in cands:
        try:
            if json.load(open(p, encoding="utf-8")).get("rc") == 0:
                return p
        except Exception:
            continue
    return cands[-1]


def run(cmd: list[str], *, cwd: Path, timeout: int | None = None) -> dict:
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=str(cwd), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout)
        rec = {"cmd": cmd, "cwd": str(cwd), "rc": r.returncode,
               "stdout": r.stdout or "", "stderr": r.stderr or "",
               "seconds": round(time.time() - t0, 1)}
    except subprocess.TimeoutExpired as e:
        rec = {"cmd": cmd, "cwd": str(cwd), "rc": "TIMEOUT",
               "stdout": (e.stdout or "") if isinstance(e.stdout, str) else "",
               "stderr": (e.stderr or "") if isinstance(e.stderr, str) else "",
               "seconds": round(time.time() - t0, 1)}
    return rec


def save(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dir_hashes(tp: Path) -> dict:
    out = {}
    for f in sorted(tp.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(tp).as_posix()
        if "node_modules" in rel or "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        try:
            out[rel] = sha256(f)
        except OSError:
            out[rel] = "<unreadable>"
    return out


def scenario_stop(scenario_dir: Path, reason: str) -> None:
    save(scenario_dir / "BLOCKED.json",
         {"reason": reason, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    print(f"\n*** 场景停止（装置事件，按规程不静默重试）：{reason}", flush=True)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--run-root", default=str(HOST / "pilot" / "round1" / "runs"))
    ap.add_argument("--run-name", default=None, help="运行目录名（默认=scenario；重跑用新目录）")
    ap.add_argument("--cl-suffix", default="", help="CL 项目名后缀（重跑隔离状态，如 '2' -> round1_wr1rr2_clv0）")
    ap.add_argument("--arms", default="clv0,baseline",
                    help="要跑的臂（默认双臂；装置回归可只跑 clv0——导出层修复只影响 clv0 供给面）")
    args = ap.parse_args()
    arms_to_run = [a.strip() for a in args.arms.split(",") if a.strip()]
    for a in arms_to_run:
        if a not in ("clv0", "baseline"):
            raise SystemExit(f"--arms 仅接受 clv0/baseline，收到: {a}")

    scenario_path = HOST / "pilot" / "round1" / "scenarios" / f"{args.scenario}.json"
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    turns = scenario["scripted_turns"]
    run_name = args.run_name or args.scenario
    sc_dir = Path(args.run_root) / run_name
    sc_dir.mkdir(parents=True, exist_ok=True)
    # CL 项目名去臂名（trace 文件名由它生成，模型可窥见 traces/ 目录）
    cl_project = f"round1_w{CL_SHORT[args.scenario]}{args.cl_suffix}_p1"
    log = {"scenario": args.scenario, "run_name": run_name, "scenario_path": str(scenario_path),
           "cl_project": cl_project, "arm_dirs": ARM_DIR, "arms_to_run": arms_to_run, "steps": []}
    # 臂映射外置到驱动侧（运行目录内不落臂名）
    ARM_MAP_PATH.mkdir(parents=True, exist_ok=True)
    save(ARM_MAP_PATH / f"arm_map_{run_name}.json",
         {"arm_dirs": ARM_DIR, "cl_project": cl_project, "run_dir": str(sc_dir),
          "note": "workspace-a=cl_v0 逻辑臂，workspace-b=baseline 逻辑臂；"
                  "本文件在驱动侧 temp/，不进运行目录（Round 2 前置 2 中性路径名）"})

    # ---- 1. 布景（两臂同源） ----
    seed_src = SEEDS / args.scenario
    if not seed_src.exists():
        scenario_stop(sc_dir, f"种子目录不存在: {seed_src}")
        return 2
    seeding = {}
    for arm in ("clv0", "baseline"):
        tp = task_project(sc_dir, arm)
        if not tp.exists():
            tp.mkdir(parents=True)
            for f in seed_src.rglob("*"):
                if f.is_file():
                    dest = tp / f.relative_to(seed_src)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)
        seeding[ARM_DIR[arm]] = {f.name: sha256(f) for f in sorted(task_project(sc_dir, arm).glob("*")) if f.is_file()}
    seeding_manifest_path = sc_dir / "seeding_manifest.json"
    manifest_existed = seeding_manifest_path.exists()
    # reassignment_recovery：与场景 JSON seed_files 逐字节核对（仅布景时；
    # resume 时 task-project 已被轮次改写，核对只在种子刚落盘时有效）
    if "seed_files" in scenario and not manifest_existed:
        for name, content in scenario["seed_files"].items():
            actual = (task_project(sc_dir, "clv0") / name).read_text(encoding="utf-8")
            if actual != content:
                scenario_stop(sc_dir, f"种子与场景 seed_files 不一致: {name}")
                return 2
        print("[布景] seed_files 逐字节核对一致", flush=True)
    if not manifest_existed:
        save(seeding_manifest_path, {"seeds": seeding, "arms_equal": seeding[ARM_DIR["clv0"]] == seeding[ARM_DIR["baseline"]]})
    else:
        print("[布景] resume：种子核对已在首建时完成（manifest 在案），跳过", flush=True)
    print(f"[布景] 两臂同源={seeding[ARM_DIR['clv0']] == seeding[ARM_DIR['baseline']]}"
          f"（manifest {'已存在，未覆盖' if manifest_existed else '首建'}）", flush=True)

    # ---- 1b. 每臂嵌套 git init（第七号裁定 C'：恢复 P1/P2 先例，两臂 git 互相不可见） ----
    git_heads = {}
    for arm in ("clv0", "baseline"):
        tp = task_project(sc_dir, arm)
        if (tp / ".git").exists():
            git_heads[ARM_DIR[arm]] = git_head(tp)
            continue
        # 任务项目 .gitignore：装置管线（.opencode/）不进臂内提交历史
        gi = tp / ".gitignore"
        if not gi.exists():
            gi.write_text(".opencode/\n", encoding="utf-8")
        def git_cmd(*a):
            return subprocess.run(["git", *a], cwd=str(tp), capture_output=True, encoding="utf-8")
        git_cmd("init", "-q")
        git_cmd("config", "user.email", "round1-window@local")
        git_cmd("config", "user.name", "round1 window")
        git_cmd("add", "-A")
        r = git_cmd("commit", "-qm", "round1 window seed（布景初始提交）")
        git_heads[ARM_DIR[arm]] = git_head(tp)
        print(f"[git init] {ARM_DIR[arm]}: HEAD={git_heads[ARM_DIR[arm]]} commit_rc={r.returncode}", flush=True)
        log["steps"].append({"step": "git_init", "arm_dir": ARM_DIR[arm], "head": git_heads[ARM_DIR[arm]], "rc": r.returncode})
    save(sc_dir / "git_heads.json", git_heads)

    # ---- 2. cl_v0 臂安装 + 自检 ----
    install = run([sys.executable, str(HOST / "tools" / "cl_install.py"),
                   "--project", str(task_project(sc_dir, "clv0")),
                   "--cl-project", cl_project, "--init-cl"], cwd=HOST)
    print(f"[cl_install] rc={install['rc']}", flush=True)
    if install["rc"] != 0:
        scenario_stop(sc_dir, "cl_install 失败")
        return 2
    selfcheck = run([sys.executable, str(HOST / "tools" / "cl_selfcheck.py"),
                     "--project", str(task_project(sc_dir, "clv0"))], cwd=HOST)
    ok_6 = "6/6" in selfcheck["stdout"] or "6/6" in selfcheck["stderr"]
    print(f"[cl_selfcheck] rc={selfcheck['rc']} 6/6={ok_6}", flush=True)
    log["steps"].append({"step": "cl_install", "rc": install["rc"]})
    log["steps"].append({"step": "cl_selfcheck", "rc": selfcheck["rc"], "six_of_six": ok_6})
    if selfcheck["rc"] != 0 or not ok_6:
        scenario_stop(sc_dir, "cl_selfcheck 未 6/6（§7-6 装置故障）")
        return 2

    # ---- 3. baseline 摘要 + 信息量下限 ----
    summary_md = arm_dir(sc_dir, "baseline") / "summary_recovery.md"
    gen = run([sys.executable, str(HOST / "pilot" / "round1" / "tools" / "make_summary_recovery.py"),
               "--scenario", str(scenario_path), "--out", str(summary_md)], cwd=HOST)
    floor = run([sys.executable, str(HOST / "pilot" / "round1" / "tools" / "check_info_floor.py"),
                 "--scenario", str(scenario_path), "--summary", str(summary_md)], cwd=HOST)
    print(f"[摘要] rc={gen['rc']} | [信息量下限] rc={floor['rc']}", flush=True)
    log["steps"].append({"step": "baseline_summary", "rc": gen["rc"]})
    log["steps"].append({"step": "info_floor", "rc": floor["rc"]})
    if gen["rc"] != 0 or floor["rc"] != 0:
        scenario_stop(sc_dir, "摘要生成或信息量下限未过（§7-5 装置故障）")
        return 2
    summary_text = summary_md.read_text(encoding="utf-8")

    # ---- 4. 逐轮执行 ----
    prev_session = None
    turn_index = 0
    ran_arms_total = {"host": 0, "extractions": 0}
    clv0_halted = False
    # D' 终态恢复：若在案 HALTED.json，clv0 维持停机（不复活、不补跑）
    halted_file = sc_dir / "HALTED.json"
    if halted_file.exists():
        clv0_halted = True
        hd = json.loads(halted_file.read_text(encoding="utf-8"))
        print(f"[D' 恢复] clv0 停机终态在案（t{hd.get('turn')}，{hd.get('at')}）——维持停机，不补跑", flush=True)
        log["steps"].append({"step": "clv0_halt_state_restored", "from": str(halted_file)})
    for t in turns:
        session = int(t["session"])
        turn_no = int(t["turn"])
        new_session = prev_session is not None and session != prev_session
        first_of_s1 = prev_session is None
        prev_session = session
        user_text = t["user"]
        turn_index += 1
        ran_any = False

        for arm in ("clv0", "baseline"):
            if arm not in arms_to_run:
                continue
            if arm == "clv0" and clv0_halted:
                print(f"[halt] clv0 t{turn_no}（臂已停机，D' 终态不补跑）", flush=True)
                continue
            # 尝试链：已有成功尝试则跳过；仅有失败尝试（超时）则按 §7 续试（新轮次计预算）
            existing = sorted((arm_dir(sc_dir, arm) / "answers").glob(f"turn_{turn_no:03d}*.json"))
            success = None
            for p in existing:
                try:
                    if json.load(open(p, encoding="utf-8")).get("rc") == 0:
                        success = p
                except Exception:
                    pass
            if success:
                print(f"[skip] {arm} t{turn_no}（已有成功答案 {success.name}）", flush=True)
                continue
            attempt = len(existing) + 1
            while True:
                suffix = "" if attempt == 1 else f"_r{attempt}"
                ans_path = arm_dir(sc_dir, arm) / "answers" / f"turn_{turn_no:03d}{suffix}.json"
                if arm == "clv0":
                    cmd = [sys.executable, str(HOST / "tools" / "cl_turn.py"),
                           "--project", str(task_project(sc_dir, "clv0")),
                           "--cl-project", cl_project, "--text", user_text,
                           "--timeout", str(TURN_TIMEOUT)]
                    if new_session or first_of_s1:
                        cmd.append("--new-session")
                    rec = run(cmd, cwd=HOST, timeout=TURN_TIMEOUT + 300)
                else:
                    text = user_text
                    if new_session or first_of_s1:
                        if session != 1:
                            text = ("【会话恢复摘要（约定恢复机制）】\n" + summary_text
                                    + "\n【以上为恢复信息，以下是本轮任务】\n" + user_text)
                    cmd = [str(OPENCODE_EXE) if OPENCODE_EXE.exists() else "opencode", "run"]
                    if not (new_session or first_of_s1):
                        cmd.append("-c")
                    cmd.append(text)
                    rec = run(cmd, cwd=task_project(sc_dir, "baseline"), timeout=TURN_TIMEOUT)
                rec.update({"arm": arm, "session": session, "turn": turn_no, "attempt": attempt,
                            "new_session": bool(new_session or first_of_s1),
                            "user_text": user_text,
                            "delivered_text": text if arm == "baseline" else user_text})
                ran_any = True
                ran_arms_total["host"] += 1
                if arm == "clv0":
                    ran_arms_total["extractions"] += 1
                save(ans_path, rec)
                print(f"[{arm}] s{session}t{turn_no}{suffix} rc={rec['rc']} {rec['seconds']}s"
                      f"（attempt {attempt}）", flush=True)
                log["steps"].append({"step": f"turn_{arm}_{turn_no}{suffix}", "rc": rec["rc"],
                                     "seconds": rec["seconds"], "session": session, "turn": turn_no,
                                     "attempt": attempt})
                # 哈希快照（每次尝试都留，含失败轮的部分写态）
                snap = {ARM_DIR[a]: {f.name: sha256(f) for f in sorted(task_project(sc_dir, a).glob("*")) if f.is_file()}
                        for a in ("clv0", "baseline")}
                save(sc_dir / "hashes" / f"turn_{turn_no:03d}{suffix}.json", snap)
                if rec["rc"] == 0:
                    break
                # ---- 失败三分类 ----
                blob = rec["stdout"] + "\n" + rec["stderr"]
                is_timeout = (rec["rc"] == "TIMEOUT") or ("TimeoutExpired" in blob)
                if is_timeout and attempt == 1:
                    print(f"[§7] {arm} t{turn_no} 超时=装置事件：重试算新轮次（attempt 2，预算同记）", flush=True)
                    log["steps"].append({"step": f"turn_{arm}_{turn_no}_timeout", "seconds": rec["seconds"]})
                    attempt += 1
                    continue
                if arm == "clv0" and ("reconcile FAIL" in blob or "QUARANTINE" in blob):
                    # D' 预案（第七号裁定）：提取层失败 → clv0 停机终态，baseline 续跑
                    save(sc_dir / "HALTED.json",
                         {"arm_dir": ARM_DIR["clv0"], "turn": turn_no, "session": session, "rc": rec["rc"], "seconds": rec["seconds"],
                          "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                          "note": "clv0 臂停机终态（第七号裁定 D'，提取层失败）：不修复隔离条目、"
                                  "不强制续跑、不三跑；baseline 臂继续跑完全场景；双臂齐备检查点照封存 "
                                  "undeterminable 规则进判断点。"})
                    print(f"\n*** [D'] clv0 t{turn_no} 提取层失败（reconcile/隔离）——"
                          f"clv0 维持停机终态，baseline 续跑剩余轮次", flush=True)
                    log["steps"].append({"step": f"turn_{arm}_{turn_no}{suffix}", "rc": rec["rc"],
                                         "seconds": rec["seconds"], "halted": True})
                    clv0_halted = True
                    break
                scenario_stop(sc_dir, f"{arm} t{turn_no}{suffix} rc={rec['rc']}（装置事件）")
                save(sc_dir / "run_log.json", log)
                return 2

        # ---- 预算记账（每 5 轮或场景末轮；从 answers 全量重数 + 归档量，断点自愈） ----
        if ran_any and (turn_index % 5 == 0 or turn_no == len(turns)):
            budget_file = Path(args.run_root) / "window_budget.json"
            budget = json.loads(budget_file.read_text(encoding="utf-8")) if budget_file.exists() else {"checks": []}
            host_total = 0
            extr_total = 0
            for sc_sub in sorted(Path(args.run_root).iterdir()):
                if not sc_sub.is_dir():
                    continue
                for arm in ("clv0", "baseline"):
                    # 双布局兼容：历史运行（round1 正式窗口）用臂名落盘，扩样用中性名
                    ans_dirs = [arm_dir(sc_sub, arm) / "answers", sc_sub / arm / "answers"]
                    n = sum(len(list(ad.glob("turn_*.json"))) for ad in ans_dirs if ad.exists())
                    if n:
                        host_total += n
                        if arm == "clv0":
                            extr_total += n
            archived = budget.get("archived", {"host_turns": 0, "extractions": 0})
            host_total += archived.get("host_turns", 0)
            extr_total += archived.get("extractions", 0)
            budget["checks"].append({
                "at_turn": turn_no, "scenario": run_name,
                "live_host_turns": host_total - archived.get("host_turns", 0),
                "archived_host_turns": archived.get("host_turns", 0),
                "host_turns_total": host_total,
                "extractions_total": extr_total,
                "deepseek_est_cny": round(extr_total * COST_PER_EXTRACTION, 3),
                "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            })
            save(budget_file, budget)
            print(f"[预算] 至 t{turn_no}：宿主轮次 {host_total}（含归档 {archived.get('host_turns', 0)}），"
                  f"抽取 {extr_total} 次，DeepSeek 估算 "
                  f"{budget['checks'][-1]['deepseek_est_cny']} 元（上限 50）", flush=True)

        # ---- 5. 投递核验（M3，会话 2 首轮后） ----
        if new_session or first_of_s1:
            if session != 1:
                if "baseline" not in arms_to_run:
                    print(f"[投递核验 M3] t{turn_no} 跳过（单臂回归：无 baseline 臂，M3 对象不存在）", flush=True)
                elif dc_path.exists() and json.loads(dc_path.read_text(encoding="utf-8")).get("ok"):
                    print(f"[投递核验 M3] t{turn_no} 已有核验记录，跳过", flush=True)
                else:
                    b_path = answer_file(sc_dir, "baseline", turn_no)
                    if b_path is None:
                        scenario_stop(sc_dir, f"M3 装置故障：baseline t{turn_no} 无答复文件")
                        save(sc_dir / "run_log.json", log)
                        return 2
                    b_ans = json.load(open(b_path, encoding="utf-8"))
                    delivered = b_ans.get("delivered_text") or b_ans.get("user_text", "")
                    first_line = summary_text.splitlines()[0] if summary_text else ""
                    triples = [ev for ev in scenario.get("round1_registration", {}).get("raw_events", [])]
                    has_full = summary_text in delivered
                    has_marker_triples = first_line in delivered and all(
                        str(ev.get("entity", "")) in delivered for ev in triples)
                    ok_delivery = has_full or has_marker_triples
                    print(f"[投递核验 M3] t{turn_no} 全文={has_full} 标记+三元组={has_marker_triples} -> {'PASS' if ok_delivery else 'FAIL'}", flush=True)
                    save(dc_path,
                          {"turn": turn_no, "full": has_full, "marker_triples": has_marker_triples,
                           "ok": ok_delivery, "delivered_len": len(delivered)})
                    if not ok_delivery:
                        scenario_stop(sc_dir, f"投递核验失败：baseline t{turn_no} delivered_text 不含摘要（M3 装置故障，单向利多 CL 方向）")
                        save(sc_dir / "run_log.json", log)
                        return 2

        # ---- 6. 拦截识别（cl_v0 轮次） ----
        c_ans_path = answer_file(sc_dir, "clv0", turn_no)
        if c_ans_path is None:
            print(f"[拦截识别] t{turn_no} clv0 无本轮答案（停机终态），跳过", flush=True)
            continue
        c_ans = json.load(open(c_ans_path, encoding="utf-8"))
        blob = c_ans["stdout"] + "\n" + c_ans["stderr"]
        hits = [s for s in ("CL_READINESS_BLOCKED", "CL_GATE_BLOCKED") if s in blob]
        trace_dir = arm_dir(sc_dir, "clv0") / "traces"
        verdicts = 0
        if trace_dir.exists():
            for tp in sorted(trace_dir.glob("*.jsonl")):
                for line in tp.read_text(encoding="utf-8").splitlines():
                    try:
                        if json.loads(line).get("type") == "cl_gate_verdict":
                            verdicts += 1
                    except json.JSONDecodeError:
                        pass
        if hits:
            blocks_file = Path(args.run_root) / "window_blocks.json"
            blocks = json.loads(blocks_file.read_text(encoding="utf-8")) if blocks_file.exists() else {"blocks": []}
            first = len(blocks["blocks"]) == 0
            blocks["blocks"].append({"scenario": args.scenario, "turn": turn_no,
                                     "markers": hits, "verdicts_in_traces": verdicts,
                                     "manual_verification_required": first,
                                     "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
            save(blocks_file, blocks)
            print(f"[拦截识别] t{turn_no} 命中 {hits}"
                  + ("  *** 首个拦截案例：按规程须人工核验识别规则一次 ***" if first else ""), flush=True)
        else:
            print(f"[拦截识别] t{turn_no} 零阻断（trace verdict 累计 {verdicts}）", flush=True)

    # ---- 7. 场景收尾：导出臂内 git 史 + 清理嵌套 .git（P1/P2 先例：外层仓不留 gitlink） ----
    save(sc_dir / "run_log.json", log)  # 先落轮次日志（收尾异常也不丢）
    git_export = {}
    for arm in ("clv0", "baseline"):
        tp = task_project(sc_dir, arm)
        if not (tp / ".git").exists():
            continue
        hist_path = arm_dir(sc_dir, arm) / "git_history.txt"
        def git_cmd(*a):
            return subprocess.run(["git", *a], cwd=str(tp), capture_output=True, encoding="utf-8")
        if not hist_path.exists():
            hist = git_cmd("log", "--all", "--date=format:%Y-%m-%d %H:%M:%S",
                           "--pretty=format:%h %ad %s")
            stat = git_cmd("status", "--short")
            hist_path.write_text(
                f"$ git log --all（{arm} 臂 task-project 内嵌仓库，运行期快照）\n{hist.stdout}\n\n"
                f"$ git status --short\n{stat.stdout}\n", encoding="utf-8")
            print(f"[git 归档] {arm}: git 史已导出（{len(hist.stdout.splitlines())} 行）", flush=True)
        else:
            print(f"[git 归档] {arm}: git_history.txt 已存在（早前导出），不覆盖", flush=True)
        git_export[arm] = {"head": git_head(tp), "history_preserved": True}
        rmtree_readonly(tp / ".git")
        print(f"[git 归档] {arm}: 嵌套 .git 已清理", flush=True)
    if git_export:
        save(sc_dir / "git_export.json", git_export)
        log["steps"].append({"step": "git_archive", **git_export})

    save(sc_dir / "run_log.json", log)
    if clv0_halted:
        print(f"[done] {run_name}：baseline 全 {len(turns)} 轮完成；clv0 停机终态"
              f"（HALTED.json）——按第七号裁定 D' 进判断点", flush=True)
    else:
        print(f"[done] {run_name} 全 {len(turns)} 轮完成", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
