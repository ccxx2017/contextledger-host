/**
 * CL-V0 关口插件（工作包冒烟 S5）：把 CL 的 verify_preaction.py 接入工具执行关口。
 *
 * 机制（1.18.29）：
 *   - tool.execute.before 中抛错 = 阻断该工具执行（官方文档机制；本冒烟实证）；
 *   - 关口依据 = CL 主仓库 verify_preaction.py 的退出码（0=前提成立 / 2=失效），
 *     这是宿主侧与 CL 的唯一机器契约（宿主仓库 README 边界规则）。
 *
 * 控制文件 .opencode/cl_gate.json（由实验装配步写入）：
 *   { "gate_armed": true, "cl_home": "...", "cl_project": "pilot_s5",
 *     "expected_state_revision": "0001:..." }
 *
 * 证据：每次关口裁定都写 CL_SHADOW_TRACE（含 exit code 与 reason_codes）。
 */
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { spawnSync } from "child_process";

const PLUGIN_DIR = path.dirname(fileURLToPath(import.meta.url));
const CONTROL_FILE = path.resolve(PLUGIN_DIR, "..", "cl_gate.json");
const TRACE_FILE = process.env.CL_SHADOW_TRACE ?? "traces/host_events.jsonl";

function emit(event) {
  fs.mkdirSync(path.dirname(TRACE_FILE), { recursive: true });
  fs.appendFileSync(TRACE_FILE, JSON.stringify(event) + "\n", "utf-8");
}

export const CLV0GatePlugin = async () => {
  return {
    "tool.execute.before": async (input) => {
      let control;
      try {
        control = JSON.parse(fs.readFileSync(CONTROL_FILE, "utf-8"));
      } catch (e) {
        emit({
          type: "cl_gate_error", ts: new Date().toISOString(),
          payload: { stage: "read_control", error: String(e) },
        });
        return; // 控制文件不可读：不阻断（fail-open），但留痕
      }
      if (!control.gate_armed) return;

      const verify = path.join(control.cl_home, "graph", "scripts", "verify_preaction.py");
      const result = spawnSync(
        process.env.CL_PYTHON || "python",
        [verify,
         "--project-id", control.cl_project,
         "--state-revision", control.expected_state_revision],
        { encoding: "utf-8" },
      );

      let parsed = {};
      try { parsed = JSON.parse(result.stdout || "{}"); } catch {}

      emit({
        type: "cl_gate_verdict",
        ts: new Date().toISOString(),
        tool: input?.tool,
        payload: {
          exit_code: result.status,
          reason_codes: parsed.reason_codes ?? [],
          expected_revision: control.expected_state_revision,
        },
      });

      if (result.status === 2) {
        // 关口阻断：装配依据已过期。工具不会执行，副作用不会发生。
        throw new Error(
          `CL_GATE_BLOCKED: 装配依据过期（${(parsed.reason_codes || []).join(",") || "unknown"}）。` +
          `宿主必须重新装配（assembler_manifest）后重试。详情: ${(result.stdout || "").slice(0, 300)}`,
        );
      }
      if (result.status !== 0) {
        // 非预期退出码：留痕并放行（避免关口自身故障放大）
        emit({ type: "cl_gate_unexpected", ts: new Date().toISOString(), payload: { stderr: (result.stderr || "").slice(0, 200) } });
      }
    },
  };
};
