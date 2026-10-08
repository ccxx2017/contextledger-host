// 预算闸门本地 mock 测试（零 LLM）——调用前占用、耗尽拦截、重试路径、终止确认
import { pathToFileURL } from "node:url";
import * as fs from "node:fs";

const BASE = "C:/Users/Lenovo/AppData/Local/Temp/d4spike";
const distUrl = pathToFileURL(BASE + "/seam/dist/index.js").href;
const { apply } = await import(distUrl);

const TRACE = BASE + "/mock_gate_trace";
fs.rmSync(TRACE, { recursive: true, force: true });
const MOCK_HOME = BASE + "/mock_home";
fs.mkdirSync(MOCK_HOME + "/graph/projects/projG/run", { recursive: true });
fs.writeFileSync(MOCK_HOME + "/graph/projects/projG/run/current_states.json", JSON.stringify({ states: { k: "v" } }));
fs.writeFileSync(MOCK_HOME + "/graph/projects/projG/run/assembler_manifest.json", JSON.stringify({ state_revision: "rev-g1" }));

function assert(name, cond) {
  if (!cond) throw new Error("ASSERT FAIL: " + name);
  console.log("PASS " + name);
}
function gateEvents() {
  const sd = fs.readFileSync(TRACE + "/host_sidestep.jsonl", "utf-8").trim().split("\n").map((l) => JSON.parse(l));
  return sd.filter((e) => e.seam_event === "budget_gate_blocked" || e.seam_event === "budget_gate_admitted");
}

// 带预算的实例（N=2）
const g = makeGateCtx(2);
function makeGateCtx(n) {
  const listeners = {};
  const logs = [];
  const ctx = {
    logger: { info: (m) => logs.push("INFO:" + m), warn: (m) => logs.push("WARN:" + m) },
    on: (e, h) => { listeners[e] = h; },
  };
  apply(ctx, { mode: "on", clProject: "projG", clHome: MOCK_HOME, tracePath: TRACE + "/host_events.jsonl", verbose: false, budgetMaxCalls: n });
  return { listeners, logs, adapterEntries: { n: 0 } };
}
// 模拟适配器（next() = 进入适配器）
const adapterNext = async () => { g.adapterEntries.n += 1; return "ADAPTER_STREAM"; };
async function attempt(options) {
  return g.listeners["llm/stream"](options, adapterNext);
}
const opts = () => ({ provider: "step-fun", model: "step-5-preview", messages: [] });

// BG1：N=2 内放行
await attempt(opts());
await attempt(opts());
assert("BG1 two admitted within budget", g.adapterEntries.n === 2);

// BG2：第 3 次尝试不进入适配器，抛错拦截
let threw = false;
try { await attempt(opts()); } catch (e) { threw = String(e).includes("budget gate"); }
assert("BG2 third attempt blocked before adapter", threw && g.adapterEntries.n === 2);

// BG3：重试路径也被拦截且有界终止（模拟 llm-retry：逐次捕获、最多 3 次重试）
let retries = 0;
let lastErr;
let adapterBefore = g.adapterEntries.n;
for (let r = 0; r < 3; r++) {
  try {
    retries += 1;
    await attempt(opts());
    lastErr = undefined;
    break;
  } catch (e) {
    lastErr = e;
  }
}
assert(
  "BG3 retries gated and bounded",
  retries === 3 && String(lastErr).includes("budget gate") && g.adapterEntries.n === adapterBefore,
);
const gEv = gateEvents().filter((e) => e.seam_event === "budget_gate_blocked");
assert("BG3b blocked events recorded", gEv.length >= 3);

// BG4：预算未设（undefined）= 闸门不启用
const u = makeGateCtxUndef();
async function attemptU(options) {
  return u.listeners["llm/stream"](options, async () => { u.adapterEntries.n += 1; return "ADAPTER_STREAM"; });
}
await attemptU(opts());
await attemptU(opts());
await attemptU(opts());
assert("BG4 unlimited when budget unset", u.adapterEntries.n === 3);

function makeGateCtxUndef() {
  const listeners = {};
  const ctx = { logger: { info: () => {}, warn: () => {} }, on: (e, h) => { listeners[e] = h; } };
  apply(ctx, { mode: "on", clProject: "projG", clHome: MOCK_HOME, tracePath: TRACE + "/host_events.jsonl", verbose: false });
  return { listeners, adapterEntries: { n: 0 } };
}

console.log("\nALL BUDGET GATE TESTS PASSED (BG1-BG4)");
