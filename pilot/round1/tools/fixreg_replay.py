"""reconcile 败链修复回归实证（第八号裁定书 Round 2 前置 1）。

用 round1 场景 4 v3 t3 的原样输入（slice_003.json + turn_003.md + t2 后主图），
在临时目录复现修复后的驱动重试回路（提示词整改 + reconcile 错误回喂），
验证败链是否闭合。不触碰封存项目 round1_wr1rr3_clv0。

旧行为档案：patch_003 / retry_1 / retry_2 三次盲采样全部
STATE_CONFLICT_MISSING_SUPERSEDE（n_0008 in_progress vs n_0004 open）。
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"D:\CCXXLESSON\contextledger")
PROJ = ROOT / "graph" / "projects" / "round1_wr1rr3_clv0"
SCRIPTS = ROOT / "graph" / "scripts"
V2_PROMPT = ROOT / "graph" / "prompts" / "extractor_system_lifecycle_v2.md"

sys.path.insert(0, str(SCRIPTS))
from build_extractor_prompt import format_reconcile_feedback  # noqa: E402


def run(cmd, check=True):
    r = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"rc={r.returncode}: {' '.join(cmd)}\n{r.stdout[-500:]}\n{r.stderr[-500:]}")
    return r


def main():
    out_dir = ROOT / "temp" / "round1_judgment" / "fixreg"
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        base_graph = work / "graph_state.json"
        shutil.copy2(PROJ / "graph_state.json", base_graph)  # t2 后主图（t3 失败未推进）
        slice_path = PROJ / "reports" / "turn_003_pilot" / "slice_003.json"
        raw_turn = ROOT / "raw" / "projects" / "round1_wr1rr3_clv0" / "s001" / "turn_003.md"
        turn_id = "turn_003"

        print("=== 输入核验 ===")
        g = json.loads(base_graph.read_text(encoding="utf-8"))
        active = [n for n in g.get("nodes", {}).values() if (n.get("status") or "active") == "active"]
        for n in active:
            print(f"  active {n['node_id']} entity={n.get('entity_ref')} state={n.get('state')} type={n.get('type')}")

        report = None
        for attempt in range(1, 4):
            patch = work / f"patch_003.attempt{attempt}.json"
            cmd = [str(SCRIPTS / "invoke_extractor.py"),
                   "--project-id", "round1_fixreg", "--turn-id", turn_id,
                   "--slice", str(slice_path), "--turn", str(raw_turn),
                   "--system", str(V2_PROMPT), "--env-file", "env",
                   "--out", str(patch),
                   "--raw-response-out", str(work / f"raw.{attempt}.txt"),
                   "--prompt-out", str(work / f"prompt.{attempt}.json"),
                   "--meta-out", str(work / f"meta.{attempt}.json")]
            if attempt > 1 and report is not None:
                fb = work / f"feedback.{attempt}.json"
                fb.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
                cmd += ["--reconcile-feedback", str(fb)]
            run(cmd)
            run([str(SCRIPTS / "sanitize_patch_entity_refs.py"),
                 "--patch", str(patch), "--graph", str(base_graph), "--out", str(patch)])
            rec = work / f"reconcile.{attempt}.json"
            run([str(SCRIPTS / "reconcile_patch.py"), str(base_graph), str(patch),
                 "--out", str(rec)], check=False)
            report = json.loads(rec.read_text(encoding="utf-8"))
            p = json.loads(patch.read_text(encoding="utf-8"))
            print(f"\n=== attempt {attempt}{'（带错误回喂）' if attempt > 1 else ''} ===")
            for n in p.get("new_nodes", []):
                print(f"  NEW {n.get('node_id')} entity={n.get('entity_ref')} state={n.get('state')}")
            for s in p.get("superseded_nodes", []):
                print(f"  SUPERSEDED {s.get('node_id')} reason={str(s.get('reason'))[:60]}")
            for u in p.get("updated_nodes", []):
                print(f"  UPDATED {u.get('node_id')} changes={u.get('changes')}")
            for e in p.get("new_edges", []):
                print(f"  EDGE {e.get('source')} -{e.get('relation')}-> {e.get('target')}")
            print(f"  reconcile ok={report.get('ok')} errors={len(report.get('errors') or [])}")
            for err in (report.get("errors") or [])[:3]:
                print(f"    [{err.get('code')}] {str(err.get('message'))[:110]}")
            if report.get("ok"):
                print(f"\n*** 败链闭合：attempt {attempt} reconcile PASS ***")
                # 证据留痕（复算用）
                shutil.copy2(patch, out_dir / f"patch_003.attempt{attempt}.json")
                shutil.copy2(rec, out_dir / f"reconcile.{attempt}.json")
                shutil.copy2(work / f"prompt.{attempt}.json", out_dir / f"prompt.{attempt}.json")
                # 验证 apply_patch 可应用且旧节点退出 active
                applied = work / "applied.json"
                run([str(SCRIPTS / "apply_patch.py"),
                     "--graph", str(base_graph), "--patch", str(patch),
                     "--out", str(applied)])
                ag = json.loads(applied.read_text(encoding="utf-8"))
                old = ag["nodes"].get("n_0004", {})
                print(f"  apply 后 n_0004 status={old.get('status')} state={old.get('state')}")
                shutil.copy2(applied, out_dir / "applied.json")
                return 0
        print("\n*** 败链未闭合：3 次采样后 reconcile 仍 FAIL ***")
        return 1


if __name__ == "__main__":
    sys.exit(main())
