// 实时通道（cl-v0-inject.js）注入钩子冒烟测试。
//
// 背景：2026-10-05 实施计划阶段3 改造了注入块（统一信任标签、更新提示、未合入记录），
// 但仅有 node --check 与 python 侧单测；本脚本用**真实 manifest**（run/assembler_manifest.turn_084.json，
// 含 UNMERGED_TURN_RECORDS）驱动插件钩子，断言输出块内容，防止通道回归。
// 顺带在 2026-10-05 修掉一个既存 bug：插件直接迭代 current_states.json 整包
// （{kind, as_of_turn, states}），渲染出 kind/as_of_turn/states=[object Object]；
// 现解包到真正的实体状态映射（仍兼容旧版裸映射）。
//
// 用法（任一侧有 manifest/状态变更后可重跑）：
//   node tools/smoke_cl_v0_inject.mjs
// 退出码：全部检查通过 0；任一失败 1。

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { fileURLToPath } from "url";

const HOST = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const REPO = process.env.CL_REPO ?? "D:/CCXXLESSON/contextledger";
const PLUGIN_SRC = path.join(HOST, "opencode/plugin/cl-v0-inject.js");

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "clv0_smoke_"));
const pluginDir = path.join(tmp, "opencode", "plugin");
fs.mkdirSync(pluginDir, { recursive: true });
fs.copyFileSync(PLUGIN_SRC, path.join(pluginDir, "cl-v0-inject.js"));

const manifestPath = path.join(REPO, "graph/projects/abu_modern/run/assembler_manifest.turn_084.json");
if (!fs.existsSync(manifestPath)) {
  console.error(`manifest 不存在：${manifestPath}；请先在 CL 侧生成 run/assembler_manifest.turn_084.json`);
  process.exit(2);
}

const control = {
  cl_home: REPO,
  cl_project: "abu_modern",
  inject: true,
  gate: false,
  expected_state_revision: "0084:f142622d0e9b",
  manifest_path: manifestPath,
  current_states_path: path.join(tmp, "current_states.json"),
};
fs.writeFileSync(path.join(tmp, "opencode", "cl_v0.json"), JSON.stringify(control, null, 2));
fs.writeFileSync(path.join(tmp, "current_states.json"), JSON.stringify({
  kind: "current_states.v1",
  as_of_turn: "turn_084",
  states: { "n_0006@intent_scope": "量化研究优先，AOS为手段不是目的" },
}, null, 2));
process.env.CL_SHADOW_TRACE = path.join(tmp, "traces", "host_events.jsonl");

const mod = await import("file://" + path.join(pluginDir, "cl-v0-inject.js"));
const plugin = await mod.CLV0InjectPlugin();
const hook = plugin["experimental.chat.system.transform"];

const out = { messages: [{ info: { role: "user" }, parts: [] }] };
await hook({}, out);
const text = out.messages[0].parts.map((p) => p.text || "").join("\n");

const checks = {
  has_unified_label: text.includes("【CL 任务记忆（机器装配，反映历史记录与当前约定）】"),
  no_overstrong_label: !text.includes("逐项可信）") && !text.includes("应以此为准"),
  has_readiness: text.includes("【CL 就绪度】"),
  has_version: text.includes("【CL 版本】"),
  has_update_hint: text.includes("【CL 更新提示】"),
  has_unmerged_section: text.includes("【CL 未合入记录】"),
  has_retrieval_entry: text.includes("retrieve_raw.py"),
  says_memory_not_instruction: text.includes("不因写入本消息而获得指令权限"),
  states_unwrapped: text.includes("- n_0006@intent_scope = 量化研究优先"),
  no_wrapper_keys: !text.includes("kind = current_states.v1") && !text.includes("[object Object]"),
};

const allPass = Object.entries(checks).every(([, ok]) => ok);
console.log(JSON.stringify({ checks, all_pass: allPass }, null, 2));
console.log("--- injected block ---");
console.log(text);
if (!allPass) process.exitCode = 1;
fs.rmSync(tmp, { recursive: true, force: true });
