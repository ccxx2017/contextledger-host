/**
 * CL 影子观察插件（OpenCode，工作包 D2 宿主侧）。
 *
 * 状态：代码就绪、未启用。启用前置条件（host_seam_decision.json）：
 *   1. OpenCode 版本钉扎（checkout ↔ 运行二进制对齐）
 *   2. chat.params / experimental.chat.messages.transform 签名在钉扎 sha 上复核
 *
 * 只读纪律：本插件只观察与记录（写 host_event.v1 JSONL），不改写宿主上下文、
 * 不阻断任何调用。注入与阻断属于成对运行阶段（CL-V0 臂），且必须以
 * verify_preaction.py 的裁定为前提。
 *
 * 采集面（D1 研判核实的真实 hook 面，file:line 见 host_seam_decision.json）：
 *   - chat.params                     （LLM 调用前，结构化 payload）
 *   - tool.execute.before / after     （工具调用观察）
 *   - event(file.edited)              （文件变更）
 *   - event(session.compacted)        （压缩事件）
 *
 * 事件落盘：traces/host_events.jsonl（host_event.v1，见 adapter/observe.py）
 */

import * as fs from "fs";
import * as path from "path";

interface HostContextRef {
  entity: string;
  state?: string;
  source: "prompt" | "tool" | "file";
}

interface HostEvent {
  type: "llm_call_start" | "tool_execute_before" | "tool_execute_after" | "file_edited" | "session_compacted";
  ts: string;
  turn_id: string;
  context_refs: HostContextRef[];
  payload: Record<string, unknown>;
}

const TRACE_FILE = process.env.CL_SHADOW_TRACE ?? "traces/host_events.jsonl";

function emit(event: HostEvent): void {
  fs.mkdirSync(path.dirname(TRACE_FILE), { recursive: true });
  fs.appendFileSync(TRACE_FILE, JSON.stringify(event) + "\n", "utf-8");
}

let currentTurn = 0;
function nextTurnId(): string {
  currentTurn += 1;
  return `host-turn-${String(currentTurn).padStart(3, "0")}`;
}

/** 从即将发出的 messages 中粗提取实体引用（宿主实际上下文快照）。 */
function extractContextRefs(messages: Array<{ role: string; content: unknown }>): HostContextRef[] {
  const refs: HostContextRef[] = [];
  const seen = new Set<string>();
  for (const m of messages) {
    const text = typeof m.content === "string" ? m.content : JSON.stringify(m.content ?? "");
    // 实体行启发式：`Entity: state` / `entity_ref = state`
    const pattern = /([A-Za-z][A-Za-z0-9_\- ]{2,40}?)\s*[:=]\s*([a-z0-9_.\-]{2,40})/g;
    let match: RegExpExecArray | null;
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
  return refs;
}

export const CLShadowObserverPlugin = async ({ project, client, $ }: any) => {
  return {
    "chat.params": async (input: any, output: any) => {
      const messages = output.messages ?? [];
      emit({
        type: "llm_call_start",
        ts: new Date().toISOString(),
        turn_id: nextTurnId(),
        context_refs: extractContextRefs(messages),
        payload: {
          provider: output.provider ?? undefined,
          model: output.model ?? undefined,
          message_count: messages.length,
        },
      });
    },
    "tool.execute.before": async (input: any, output: any) => {
      emit({
        type: "tool_execute_before",
        ts: new Date().toISOString(),
        turn_id: `host-turn-${String(currentTurn).padStart(3, "0")}`,
        context_refs: [],
        payload: { tool: input?.tool, args: output?.args },
      });
    },
    "tool.execute.after": async (input: any, output: any) => {
      emit({
        type: "tool_execute_after",
        ts: new Date().toISOString(),
        turn_id: `host-turn-${String(currentTurn).padStart(3, "0")}`,
        context_refs: [],
        payload: { tool: input?.tool, title: output?.title },
      });
    },
    event: async (input: { event: { type: string; properties?: any } }) => {
      const type = input.event?.type;
      if (type === "file.edited") {
        emit({
          type: "file_edited",
          ts: new Date().toISOString(),
          turn_id: `host-turn-${String(currentTurn).padStart(3, "0")}`,
          context_refs: [{ entity: String(input.event.properties?.file ?? ""), source: "file" }],
          payload: { file: input.event.properties?.file },
        });
      } else if (type === "session.compacted") {
        emit({
          type: "session_compacted",
          ts: new Date().toISOString(),
          turn_id: `host-turn-${String(currentTurn).padStart(3, "0")}`,
          context_refs: [],
          payload: {},
        });
      }
    },
  };
};
