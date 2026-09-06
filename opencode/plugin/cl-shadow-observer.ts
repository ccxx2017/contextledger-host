/**
 * CL 影子观察插件（OpenCode，工作包 D2 宿主侧）。
 *
 * 状态：代码就绪、未启用。钉扎证据（RUNTIME_FINGERPRINT.json / sdk-1.18.29/）：
 *   - hook 面已在运行版本 1.18.29 的官方插件 SDK 类型定义上逐签名复核
 *     （opencode/sdk-1.18.29/index.d.ts，行号见注释）；
 *   - 版本对齐残余：源码 checkout 仍停在 1.17.11（GitHub 不可达），
 *     以 SDK 精确版本钉扎为等效验证；源码级复核待网络条件恢复。
 *
 * 1.18.29 关键签名事实（与早期研判的差异已修正）：
 *   - chat.params 的 output 只有 temperature/topP/topK/maxOutputTokens/options
 *     （index.d.ts:203-215）——不含 messages，【不能用于上下文观察/注入】；
 *   - 上下文观察与注入面 = experimental.chat.messages.transform
 *     （:259-264，output.messages: {info, parts}[] 完整可改写）
 *     + experimental.chat.system.transform（:265-270，output.system: string[]）；
 *   - 阻断面 = permission.ask（:225-227，output.status: ask|deny|allow）；
 *   - tool.execute.before（:235-241）仅可改写 args，不可阻断。
 *
 * 只读纪律：本插件只观察与记录（写 host_event.v1 JSONL），不改写宿主上下文、
 * 不阻断任何调用。注入与阻断属于成对运行阶段（CL-V0 臂），且必须以
 * verify_preaction.py 的裁定为前提。
 *
 * 覆盖范围声明（评审 §三.4）：仅主会话的 LLM 调用与工具调用；
 * 子 Agent / 后台路径不在本阶段保证范围。
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
function currentTurnId(): string {
  return `host-turn-${String(currentTurn).padStart(3, "0")}`;
}
function nextTurnId(): string {
  currentTurn += 1;
  return currentTurnId();
}

/** 从最终 messages 中粗提取实体引用（宿主实际发送的输入快照）。 */
function extractContextRefs(messages: Array<{ info: unknown; parts: Array<{ type: string; text?: string }> }>): HostContextRef[] {
  const refs: HostContextRef[] = [];
  const seen = new Set<string>();
  for (const m of messages) {
    for (const part of m.parts ?? []) {
      const text = typeof part.text === "string" ? part.text : "";
      // 实体行启发式：`Entity: state` / `entity = state`
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
  }
  return refs;
}

export const CLShadowObserverPlugin = async ({ project, client, $ }: any) => {
  return {
    // 观察最终模型输入：1.18.29 上上下文的唯一可观测/可注入边界（index.d.ts:259）
    "experimental.chat.messages.transform": async (input: any, output: any) => {
      emit({
        type: "llm_call_start",
        ts: new Date().toISOString(),
        turn_id: nextTurnId(),
        context_refs: extractContextRefs(output.messages ?? []),
        payload: {
          message_count: (output.messages ?? []).length,
          note: "final pre-model input snapshot (experimental.chat.messages.transform)",
        },
      });
    },
    // 记录模型参数（1.18.29 签名：output 仅含采样参数与 options，index.d.ts:203）
    "chat.params": async (input: any, output: any) => {
      emit({
        type: "llm_call_start",
        ts: new Date().toISOString(),
        turn_id: currentTurnId(),
        context_refs: [],
        payload: {
          model: input?.model,
          temperature: output?.temperature,
          note: "sampling params snapshot (chat.params)",
        },
      });
    },
    "tool.execute.before": async (input: any, output: any) => {
      emit({
        type: "tool_execute_before",
        ts: new Date().toISOString(),
        turn_id: currentTurnId(),
        context_refs: [],
        payload: { tool: input?.tool, args: output?.args },
      });
    },
    "tool.execute.after": async (input: any, output: any) => {
      emit({
        type: "tool_execute_after",
        ts: new Date().toISOString(),
        turn_id: currentTurnId(),
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
          turn_id: currentTurnId(),
          context_refs: [{ entity: String(input.event.properties?.file ?? ""), source: "file" }],
          payload: { file: input.event.properties?.file },
        });
      } else if (type === "session.compacted") {
        emit({
          type: "session_compacted",
          ts: new Date().toISOString(),
          turn_id: currentTurnId(),
          context_refs: [],
          payload: {},
        });
      }
    },
  };
};
