"""拦截识别规则构造实测（第八号裁定书 Round 2 前置 4）。

round1 窗口零自然阻断——v3 t3 停机是 reconcile 失败路径（输出含 QUARANTINE，
不含 CL_READINESS_BLOCKED/CL_GATE_BLOCKED），识别规则（verdict 事件 + 宿主输出
错误串）未获实证。本测试构造 readiness=blocked 真态（隔离条目标 unreviewed），
跑一次真 cl_turn，验证：

  R1 宿主输出含 CL_READINESS_BLOCKED（或 CL_GATE_BLOCKED）；
  R2 trace 出现 cl_gate_verdict 事件且 readiness=="blocked"；
  R3 两证据同时成立 → 识别规则可在扩样窗口机械套用；
  R4 阻断发生在模型实质工作之前（时间开销小 = 关口前置）。

装置测试，不进评测窗口；scratch 项目/任务项目均为副本，不碰封存件。
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

CL_HOME = Path(r"D:\CCXXLESSON\contextledger")
HOST = Path(r"D:\CCXXLESSON\contextledger-host")
SRC_PROJECT = CL_HOME / "graph" / "projects" / "round1_wr1rr3_clv0"
TEST_PROJECT = CL_HOME / "graph" / "projects" / "round1_blocktest_p1"
SRC_TP = HOST / "pilot" / "round1" / "runs" / "reassignment_recovery_v3" / "clv0" / "task-project"
SCRATCH = HOST / "pilot" / "round1" / "runs" / "blocktest_scratch"
TP = SCRATCH / "task-project"
OUT = CL_HOME / "temp" / "round1_judgment" / "blocktest"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if TEST_PROJECT.exists():
        shutil.rmtree(TEST_PROJECT)
    shutil.copytree(SRC_PROJECT, TEST_PROJECT)
    # 构造 blocked 真态：隔离条目标 unreviewed（v3 实际为 requeued——已有同轮 patch
    # 入主链故不触发；本测试模拟"重试后仍无 patch 入链"的自然失败态）
    reg_path = TEST_PROJECT / "quarantine" / "quarantine_register.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg["items"][0]["disposition"] = "unreviewed"
    reg["items"][0]["requires_evidence"] = "装置测试构造：模拟重试后仍无 patch 入主链的自然状态"
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[构造] {TEST_PROJECT.name} 隔离条目 -> unreviewed（readiness 应为 blocked）")

    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    TP.parent.mkdir(parents=True)
    shutil.copytree(SRC_TP, TP)
    ctrl_path = TP / ".opencode" / "cl_v0.json"
    ctrl = json.loads(ctrl_path.read_text(encoding="utf-8"))
    ctrl["cl_project"] = TEST_PROJECT.name
    ctrl_path.write_text(json.dumps(ctrl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[构造] scratch 任务项目 -> {TP}")

    t0 = time.time()
    r = subprocess.run(
        [sys.executable, str(HOST / "tools" / "cl_turn.py"),
         "--project", str(TP), "--cl-project", TEST_PROJECT.name,
         "--text", "装置测试：请看一下当前项目状态。", "--new-session", "--timeout", "150"],
        cwd=HOST, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    rec = {"rc": r.returncode, "stdout": r.stdout, "stderr": r.stderr,
           "seconds": round(time.time() - t0, 1)}
    (OUT / "cl_turn_record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")

    blob = (r.stdout or "") + "\n" + (r.stderr or "")
    traces = sorted((SCRATCH / "traces").glob("*.jsonl")) if (SCRATCH / "traces").exists() else []
    print(f"\n[cl_turn] rc={r.returncode} {rec['seconds']}s  traces={len(traces)}")

    r1 = "CL_READINESS_BLOCKED" in blob or "CL_GATE_BLOCKED" in blob
    print(f"R1 宿主输出含拦截错误串: {r1}")
    if r1:
        for line in blob.splitlines():
            if "CL_READINESS_BLOCKED" in line or "CL_GATE_BLOCKED" in line:
                print(f"   原文: {line.strip()[:160]}")

    verdicts = []
    for tp in traces:
        for line in tp.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("type") == "cl_gate_verdict":
                verdicts.append({"file": tp.name, "payload": e.get("payload")})
    (OUT / "gate_verdicts.json").write_text(json.dumps(verdicts, ensure_ascii=False, indent=2), encoding="utf-8")
    r2 = any((v["payload"] or {}).get("readiness") == "blocked" for v in verdicts)
    print(f"R2 trace cl_gate_verdict 且 readiness=blocked: {r2}（verdict 事件 {len(verdicts)} 条）")
    for v in verdicts[:3]:
        print(f"   {v['payload']}")
    r3 = r1 and r2
    print(f"R3 识别规则双证据齐备: {r3}")
    r4 = rec["seconds"] < 300
    print(f"R4 阻断前置（{rec['seconds']}s < 300s）: {r4}")
    result = {"R1_error_string": r1, "R2_verdict_blocked": r2, "R3_rule_applicable": r3,
              "R4_preemptive": r4, "cl_turn_rc": r.returncode, "seconds": rec["seconds"],
              "verdict_count": len(verdicts), "traces": [t.name for t in traces],
              "note": "装置测试（第八号裁定书 Round 2 前置 4）：构造 readiness=blocked 真态"
                      "（隔离 unreviewed）实测拦截识别规则；round1 窗口零自然阻断，"
                      "v3 t3 停机为 reconcile 失败路径（不含拦截错误串）。"}
    (OUT / "blocktest_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if r3 and r4 else 1


if __name__ == "__main__":
    sys.exit(main())
