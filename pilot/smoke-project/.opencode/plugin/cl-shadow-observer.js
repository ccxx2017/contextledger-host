/**
 * CL 影子观察插件（冒烟版，JS/无依赖——避免 SDK 版本牵连）。
 * hook 面已按运行版本 1.18.29 官方类型逐签名复核：
 *   - 上下文观察唯一边界: experimental.chat.messages.transform (index.d.ts:259)
 *   - 采样参数: chat.params (:203, 无 messages)
 *   - 工具: tool.execute.before(:235) / after(:249)
 * 只读纪律：只记录，不改写、不阻断。
 * 事件落盘：CL_SHADOW_TRACE 环境变量指定的 JSONL。
 */
import * as fs from "fs";
import * as path from "path";

const TRACE_FILE = process.env.CL_SHADOW_TRACE ?? "traces/host_events.jsonl";

function emit(event) {
  fs.mkdirSync(path.dirname(TRACE_FILE), { recursive: true });
  fs.appendFileSync(TRACE_FILE, JSON.stringify(event) + "\n", "utf-8");
}

let currentTurn = 0;
function currentTurnId() {
  return `host-turn-${String(currentTurn).padStart(3, "0")}`;
}
function nextTurnId() {
  currentTurn += 1;
  return currentTurnId();
}

function extractContextRefs(messages) {
  const refs = [];
  const seen = new Set();
  for (const m of messages ?? []) {
    for (const part of m.parts ?? []) {
      const text = typeof part.text === "string" ? part.text : "";
      const pattern = /([A-Za-z][A-Za-z0-9_\- ]{2,40}?)\s*[:=]\s*([a-z0-9_.\-]{2,40})/g;
      let match;
      while ((match = pattern.exec(text)) !== null) {
        const entity = match[1].trim();
        const key = `${entity}=${match[2]}`;
        if (!seen.has(key)) {
          seen.add(key);
          refs.push({ entity, state: match[2], source: "prompt" });
        }
        if (refs.length >= 200) return refs;
      }
    }
  }
  return refs;
}

export const CLShadowObserverPlugin = async () => {
  return {
    "experimental.chat.messages.transform": async (input, output) => {
      emit({
        type: "llm_call_start",
        ts: new Date().toISOString(),
        turn_id: nextTurnId(),
        context_refs: extractContextRefs(output.messages ?? []),
        payload: {
          message_count: (output.messages ?? []).length,
          boundary: "experimental.chat.messages.transform (final pre-model input)",
        },
      });
    },
    "chat.params": async (input, output) => {
      emit({
        type: "sampling_params",
        ts: new Date().toISOString(),
        turn_id: currentTurnId(),
        context_refs: [],
        payload: { model: input?.model?.modelID, temperature: output?.temperature },
      });
    },
    "tool.execute.before": async (input, output) => {
      emit({
        type: "tool_execute_before",
        ts: new Date().toISOString(),
        turn_id: currentTurnId(),
        context_refs: [],
        payload: { tool: input?.tool, args: output?.args },
      });
    },
    "tool.execute.after": async (input, output) => {
      emit({
        type: "tool_execute_after",
        ts: new Date().toISOString(),
        turn_id: currentTurnId(),
        context_refs: [],
        payload: { tool: input?.tool, title: output?.title },
      });
    },
    event: async (input) => {
      const type = input?.event?.type;
      if (type === "file.edited") {
        emit({
          type: "file_edited",
          ts: new Date().toISOString(),
          turn_id: currentTurnId(),
          context_refs: [],
          payload: { file: input.event.properties?.file },
        });
      }
    },
  };
};
