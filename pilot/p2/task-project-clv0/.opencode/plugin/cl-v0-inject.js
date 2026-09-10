/**
 * CL-V0 注入 + 关口插件（P1/P2 成对运行的 cl_v0 臂）。
 *
 * 注入面（1.18.29 已验证）：experimental.chat.system.transform（output.system: string[]
 * 可追加）——把 CL 当前态与就绪度写入 system 区，随最终模型输入发送。
 * 观察面：experimental.chat.messages.transform（最终输入 dump，含注入效果的自证）。
 * 关口面：tool.execute.before —— readiness=blocked 或 verify_preaction exit 2 时抛错阻断。
 *
 * 控制文件 .opencode/cl_v0.json（由 CL 侧 pilot_turn_driver.py 每轮刷新）：
 * {
 *   "cl_home": "D:/CCXXLESSON/contextledger",
 *   "cl_project": "pilot_p1",
 *   "inject": true,
 *   "gate": true,
 *   "expected_state_revision": "0003:abc123456789" | null,
 *   "manifest_path": ".../reports/assembler_manifest.turn_00N.json",
 *   "current_states_path": ".../run/current_states.json"
 * }
 */
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { spawnSync } from "child_process";

const PLUGIN_DIR = path.dirname(fileURLToPath(import.meta.url));
const CONTROL_FILE = path.resolve(PLUGIN_DIR, "..", "cl_v0.json");
const TRACE_FILE = process.env.CL_SHADOW_TRACE ?? "traces/host_events.jsonl";

function emit(event) {
  fs.mkdirSync(path.dirname(TRACE_FILE), { recursive: true });
  fs.appendFileSync(TRACE_FILE, JSON.stringify(event) + "\n", "utf-8");
}

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

export const CLV0InjectPlugin = async () => {
  return {
    "experimental.chat.system.transform": async (input, output) => {
      let control;
      try { control = readJson(CONTROL_FILE); } catch (e) {
        emit({ type: "cl_v0_error", ts: new Date().toISOString(), payload: { stage: "read_control", error: String(e) } });
        return;
      }
      if (!control.inject) return;

      let states = {};
      let manifest = null;
      try { states = readJson(control.current_states_path); } catch (e) {
        emit({ type: "cl_v0_error", ts: new Date().toISOString(), payload: { stage: "read_states", error: String(e) } });
      }
      try { manifest = readJson(control.manifest_path); } catch {}

      const lines = ["【CL 当前态（机器装配，逐项可信）】"];
      const entries = Object.entries(states || {});
      if (entries.length === 0) {
        lines.push("（尚无已裁定实体状态）");
      } else {
        for (const [entity, st] of entries) {
          lines.push(`- ${entity} = ${st}`);
        }
      }
      if (manifest) {
        lines.push(`【CL 就绪度】${manifest.readiness}${(manifest.reason_codes || []).length ? "（" + manifest.reason_codes.join(", ") + "）" : ""}`);
        lines.push(`【CL 版本】${manifest.state_revision}`);
      }
      lines.push("【CL 使用规则】以上为经裁定机制维护的当前态；与其冲突的早期记忆应以此为准。");
      const block = lines.join("\n");

      // 策略二（system.transform 变异被丢弃后的降级尝试）：向最后一条 user 消息
      // 【就地】追加文本部件——引用变异，若管线复用同一对象则传播到实际请求。
      const msgs = output.messages ?? [];
      for (let i = msgs.length - 1; i >= 0; i--) {
        const m = msgs[i];
        const role = m?.info?.role ?? m?.role;
        if (role === "user") {
          if (!Array.isArray(m.parts)) m.parts = [];
          const already = m.parts.some((p) => typeof p.text === "string" && p.text.includes("【CL 当前态（机器装配，逐项可信）】"));
          if (!already) {
            m.parts.push({ type: "text", text: block });
          }
          emit({
            type: "cl_v0_inject_strategy",
            ts: new Date().toISOString(),
            payload: { strategy: "inplace_user_part", message_index: i },
          });
          break;
        }
      }

      emit({
        type: "cl_v0_injected",
        ts: new Date().toISOString(),
        payload: {
          states_count: entries.length,
          readiness: manifest ? manifest.readiness : null,
          state_revision: manifest ? manifest.state_revision : null,
        },
      });
    },

    "experimental.chat.messages.transform": async (input, output) => {
      // 最终输入自证 dump（含 marker 的精确位置：消息序号 + 角色 + 部件序号）
      let control;
      try { control = readJson(CONTROL_FILE); } catch { return; }
      const MARKER = "【CL 当前态（机器装配，逐项可信）】";
      const locations = [];
      (output.messages ?? []).forEach((m, idx) => {
        const role = m?.info?.role ?? m?.role ?? "unknown";
        (m.parts ?? []).forEach((p, pi) => {
          const text = typeof p.text === "string" ? p.text : "";
          if (text.includes(MARKER)) locations.push({ message_index: idx, role, part_index: pi });
        });
      });
      emit({
        type: "cl_v0_boundary_dump",
        ts: new Date().toISOString(),
        payload: {
          message_count: (output.messages ?? []).length,
          cl_injection_locations: locations,
          cl_injection_in_system_message: locations.some((l) => l.role === "system"),
        },
      });
    },

    "tool.execute.before": async (input) => {
      let control;
      try { control = readJson(CONTROL_FILE); } catch { return; }

      // 关口 1：readiness 消费
      if (control.gate && control.manifest_path) {
        try {
          const manifest = readJson(control.manifest_path);
          emit({
            type: "cl_gate_verdict", ts: new Date().toISOString(), tool: input?.tool,
            payload: { gate: "readiness", readiness: manifest.readiness, reason_codes: manifest.reason_codes },
          });
          if (manifest.readiness === "blocked") {
            throw new Error(`CL_READINESS_BLOCKED: ${(manifest.reason_codes || []).join(", ")}`);
          }
        } catch (e) {
          if (String(e).includes("CL_READINESS_BLOCKED")) throw e;
          emit({ type: "cl_v0_error", ts: new Date().toISOString(), payload: { stage: "readiness", error: String(e) } });
        }
      }

      // 关口 2：版本前提核验
      if (control.gate && control.expected_state_revision) {
        const verify = path.join(control.cl_home, "graph", "scripts", "verify_preaction.py");
        const result = spawnSync(
          process.env.CL_PYTHON || "python",
          [verify, "--project-id", control.cl_project, "--state-revision", control.expected_state_revision],
          { encoding: "utf-8" },
        );
        let parsed = {};
        try { parsed = JSON.parse(result.stdout || "{}"); } catch {}
        emit({
          type: "cl_gate_verdict", ts: new Date().toISOString(), tool: input?.tool,
          payload: { gate: "preaction", exit_code: result.status, reason_codes: parsed.reason_codes ?? [] },
        });
        if (result.status === 2) {
          throw new Error(`CL_GATE_BLOCKED: 装配依据过期（${(parsed.reason_codes || []).join(",")}）。以最新 CL 当前态为准重新决策。`);
        }
      }
    },
  };
};
