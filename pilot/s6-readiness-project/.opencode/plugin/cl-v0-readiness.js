/**
 * CL-V0 readiness 消费插件（工作包冒烟 S6）：
 * 宿主在每次工具执行前读取 CL 的 assembler_manifest，
 * readiness=blocked 时拒绝行动（工具不执行），并展示 reason_codes 与未裁定事件。
 *
 * 控制文件 .opencode/cl_gate.json：
 *   { "gate_armed": true,
 *     "manifest_path": "D:/.../graph/projects/pilot_s6/run/assembler_manifest.turn_002.json" }
 *
 * 消费语义（contracts/04_assembly.md §7.3）：
 *   blocked → 宿主不得行动；degraded → 可行动但须知情；ready → 正常。
 */
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const PLUGIN_DIR = path.dirname(fileURLToPath(import.meta.url));
const CONTROL_FILE = path.resolve(PLUGIN_DIR, "..", "cl_gate.json");
const TRACE_FILE = process.env.CL_SHADOW_TRACE ?? "traces/host_events.jsonl";

function emit(event) {
  fs.mkdirSync(path.dirname(TRACE_FILE), { recursive: true });
  fs.appendFileSync(TRACE_FILE, JSON.stringify(event) + "\n", "utf-8");
}

export const CLV0ReadinessPlugin = async () => {
  return {
    "tool.execute.before": async (input) => {
      let control;
      try {
        control = JSON.parse(fs.readFileSync(CONTROL_FILE, "utf-8"));
      } catch (e) {
        emit({ type: "cl_gate_error", ts: new Date().toISOString(), payload: { stage: "read_control", error: String(e) } });
        return; // fail-open + 留痕
      }
      if (!control.gate_armed) return;

      let manifest;
      try {
        manifest = JSON.parse(fs.readFileSync(control.manifest_path, "utf-8"));
      } catch (e) {
        emit({ type: "cl_gate_error", ts: new Date().toISOString(), payload: { stage: "read_manifest", error: String(e) } });
        return;
      }

      emit({
        type: "cl_readiness_verdict",
        ts: new Date().toISOString(),
        tool: input?.tool,
        payload: {
          readiness: manifest.readiness,
          reason_codes: manifest.reason_codes,
          unresolved_event_ids: (manifest.unresolved_event_ids || []).map((u) => u.register_key),
        },
      });

      if (manifest.readiness === "blocked") {
        const unresolved = (manifest.unresolved_event_ids || []).map((u) => u.register_key).join(", ");
        throw new Error(
          `CL_READINESS_BLOCKED: 当前装配不可支撑行动。reason_codes=[${(manifest.reason_codes || []).join(", ")}]` +
          ` 未裁定事件=[${unresolved}]。宿主须等待隔离裁定完成后重新装配。`,
        );
      }
      if (manifest.readiness === "degraded") {
        // 可行动但须知情：把风险写进 args 备注（不阻断），留痕已足够本冒烟
        emit({ type: "cl_readiness_degraded_ack", ts: new Date().toISOString(), payload: { reason_codes: manifest.reason_codes } });
      }
    },
  };
};
