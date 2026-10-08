// 供给状态机本地 mock 测试 v3.2（零 LLM）——权威=已提交历史 vs 当前发布
import { pathToFileURL } from "node:url";
import * as fs from "node:fs";

const BASE = "C:/Users/Lenovo/AppData/Local/Temp/d4spike";
const distUrl = pathToFileURL(BASE + "/seam/dist/index.js").href;
const { apply } = await import(distUrl);

const MOCK_HOME = BASE + "/mock_home";
function writeFixture(proj, revision, states) {
  const run = MOCK_HOME + "/graph/projects/" + proj + "/run";
  fs.mkdirSync(run, { recursive: true });
  fs.writeFileSync(run + "/current_states.json", JSON.stringify({ states }));
  fs.writeFileSync(run + "/assembler_manifest.json", JSON.stringify({ state_revision: revision, readiness: "published" }));
}
function breakFixture(proj) {
  const run = MOCK_HOME + "/graph/projects/" + proj + "/run";
  fs.mkdirSync(run, { recursive: true });
  fs.writeFileSync(run + "/current_states.json", "{ broken");
  fs.writeFileSync(run + "/assembler_manifest.json", "{}");
}

const TRACE = BASE + "/mock_trace";
fs.rmSync(TRACE, { recursive: true, force: true });

const userMsg = (text, id) => ({ role: "user", id, content: [{ type: "text", text }], source: { kind: "user" } });
function makeCtx() {
  const listeners = {};
  const logs = [];
  return {
    logs,
    ctx: {
      logger: { info: (m) => logs.push("INFO:" + m), warn: (m) => logs.push("WARN:" + m) },
      on: (e, h) => { listeners[e] = h; },
    },
    listeners,
  };
}

// 已提交历史（模拟宿主会话提交）
const committed = {};
function preStep(listeners, committedMap, sessionId, step, claimed, behavior = "pass", commit = true) {
  const session = { id: sessionId, deriveMessages: () => committedMap[sessionId] || [] };
  return listeners["agent/pre-step"](
    { agent: { session }, messages: claimed, turn: 1, step },
    async () => (behavior === "reject" ? { kind: "reject" } : { kind: "enter", messages: [...claimed] }),
  ).then((returned) => {
    // 模拟宿主提交：领取批次 + 追加消息一并提交（按 id 去重）
    if (commit && returned && returned.kind === "enter" && Array.isArray(returned.messages)) {
      const have = new Set((committedMap[sessionId] || []).map((m) => m.id));
      for (const m of returned.messages) if (!have.has(m.id)) (committedMap[sessionId] ||= []).push(m);
    }
    return returned;
  });
}
function proposals(sessionId) {
  const sd = fs.readFileSync(TRACE + "/host_sidestep.jsonl", "utf-8").trim().split("\n").map((l) => JSON.parse(l));
  return sd.filter((e) => e.seam_event === "cl_memory_supply_proposed" && e.sessionId === sessionId);
}
function observed() {
  const sd = fs.readFileSync(TRACE + "/host_sidestep.jsonl", "utf-8").trim().split("\n").map((l) => JSON.parse(l));
  return sd.filter((e) => e.seam_event === "request_messages_observed");
}
function assert(name, cond) {
  if (!cond) throw new Error("ASSERT FAIL: " + name);
  console.log("PASS " + name);
}

// T6 off
const off = makeCtx();
apply(off.ctx, { mode: "off", clProject: "projOff", clHome: MOCK_HOME, tracePath: TRACE + "/host_events.jsonl", verbose: false });
assert("T6 off has no pre-step listener", !off.listeners["agent/pre-step"]);

// 主实例（projX）
committed.s1 = [];
writeFixture("projX", "rev-test-0001", { "impl-owner": "agent-liu" });
const main = makeCtx();
apply(main.ctx, { mode: "on", clProject: "projX", clHome: MOCK_HOME, tracePath: TRACE + "/host_events.jsonl", verbose: false });

// T1 首供 + 提交
const r1 = await preStep(main.listeners, committed, "s1", 1, [userMsg("task", "u1")]);
assert("T1 proposed once rev0001", proposals("s1").length === 1 && proposals("s1")[0].cl_revision === "rev-test-0001" && proposals("s1")[0].outcome.startsWith("proposed"));
assert("T1 commit landed", committed.s1.length === 2);
// T2 同版本（已提交）不重复
await preStep(main.listeners, committed, "s1", 2, [userMsg("task2", "u2")]);
assert("T2 no re-supply same committed revision", proposals("s1").length === 1);

// T3 冲突变化（改派 agent-zhao）
writeFixture("projX", "rev-test-0002", { "impl-owner": "agent-zhao" });
const r3 = await preStep(main.listeners, committed, "s1", 3, [userMsg("task3", "u3")]);
assert("T3 resupply on conflict change", proposals("s1").length === 2 && proposals("s1")[1].cl_revision === "rev-test-0002");
{ const ids = new Set([["task3","u3"]][0][1]); for (const m of r3.messages) if (!ids.has(m.id)) committed.s1.push(m); }

// T3b 删除变化（快照移除全部实体）
writeFixture("projX", "rev-test-0003", {});
await preStep(main.listeners, committed, "s1", 4, [userMsg("task4", "u4")]);
assert("T3b resupply on deletion snapshot", proposals("s1").length === 3 && proposals("s1")[2].cl_revision === "rev-test-0003");

// T4 压缩：历史被摘要清空 + compaction 事件
committed.s1 = [];
await main.listeners["session/event"]({ type: "compaction/end" });
await preStep(main.listeners, committed, "s1", 5, [userMsg("task5", "u5")]);
assert("T4 post-compaction resupply", proposals("s1").length === 4 && proposals("s1")[3].cl_revision === "rev-test-0003");
await preStep(main.listeners, committed, "s1", 6, [userMsg("task6", "u6")]);
assert("T4b no repeat after post-compaction supply", proposals("s1").length === 4);

// T5 下游拒绝 → 不提交 → 下一步自动重试
committed.sR = [];
writeFixture("projR", "rev-r1", { "k": "v1" });
const rej = makeCtx();
apply(rej.ctx, { mode: "on", clProject: "projR", clHome: MOCK_HOME, tracePath: TRACE + "/host_events.jsonl", verbose: false });
await preStep(rej.listeners, committed, "sR", 1, [userMsg("t", "u1")], "reject", false);
assert("T5a rejected attempt recorded (not-appended)", proposals("sR").length === 1);
await preStep(rej.listeners, committed, "sR", 2, [userMsg("t", "u2")]);
assert("T5b auto-retry after uncommitted rejection", proposals("sR").length === 2);

// T5-new（指令4）：瀑布接纳但宿主未提交（取消/失败）→ 下一步仍供给
writeFixture("projR", "rev-r2", { "k": "v2" });
await preStep(rej.listeners, committed, "sR", 3, [userMsg("t", "u3")], "pass", false); // proposed 但不提交
assert("T5c proposed but uncommitted", proposals("sR").length === 3 && proposals("sR")[2].cl_revision === "rev-r2");
await preStep(rej.listeners, committed, "sR", 4, [userMsg("t", "u4")], "pass", false); // 仍未提交 → 重供给
assert("T5d resupply after uncommitted acceptance", proposals("sR").length === 4 && proposals("sR")[3].cl_revision === "rev-r2");
await preStep(rej.listeners, committed, "sR", 5, [userMsg("t", "u5")]); // 提交（本次供给 rev-r2 并落历史）
assert("T5e commit run supplied rev-r2", proposals("sR").length === 5 && proposals("sR")[4].cl_revision === "rev-r2");
await preStep(rej.listeners, committed, "sR", 6, [userMsg("t", "u6")]); // 已提交 → 不重复
assert("T5f after commit no duplicate", proposals("sR").length === 5);

// T7 双项目隔离
committed.sY = [];
writeFixture("projY", "rev-y1", { "only-y": "state-y" });
const y = makeCtx();
apply(y.ctx, { mode: "on", clProject: "projY", clHome: MOCK_HOME, tracePath: TRACE + "/host_events.jsonl", verbose: false });
await preStep(y.listeners, committed, "sY", 1, [userMsg("task-y", "uy1")]);
assert("T7 projY supplied independently", proposals("sY").length === 1 && proposals("sY")[0].cl_project === "projY");

// T8 超长记忆截断
writeFixture("projX", "rev-big", { "big": "x".repeat(9000) });
const r8 = await preStep(main.listeners, committed, "s1", 7, [userMsg("task7", "u7")]);
{ const ids = new Set(["u7"]); for (const m of r8.messages) if (!ids.has(m.id)) committed.s1.push(m); }
const p8 = proposals("s1").filter((e) => e.cl_revision === "rev-big");
assert("T8 truncated flagged", p8.length === 1 && p8[0].truncated === true);

// T10 进程重启恢复：新实例 + 同会话（已提交含 rev-big 记忆）→ 同版本不重复（去重状态从历史恢复）
const restart = makeCtx();
apply(restart.ctx, { mode: "on", clProject: "projX", clHome: MOCK_HOME, tracePath: TRACE + "/host_events.jsonl", verbose: false });
await preStep(restart.listeners, committed, "s1", 8, [userMsg("task8", "u8")]);
assert("T10 dedup state recovered from committed history after restart", proposals("s1").filter((e) => e.cl_revision === "rev-big").length === 1);
// 换版后正常供给
writeFixture("projX", "rev-after-restart", { "impl-owner": "agent-zhao" });
await preStep(restart.listeners, committed, "s1", 9, [userMsg("task9", "u9")]);
assert("T10b resupply after restart on revision change", proposals("s1").filter((e) => e.cl_revision === "rev-after-restart").length === 1);

// T9 夹具读取失败
committed.sBad = [];
breakFixture("projMissing");
const bad = makeCtx();
apply(bad.ctx, { mode: "on", clProject: "projMissing", clHome: MOCK_HOME, tracePath: TRACE + "/host_events.jsonl", verbose: false });
await preStep(bad.listeners, committed, "sBad", 1, [userMsg("t", "ub1")]);
assert("T9 no supply when fixture unreadable", proposals("sBad").length === 0);
assert("T9 degraded logged", bad.logs.some((l) => l.includes("fixture_unreadable")));

// llm/stream 只读观测：给 s1 的已提交历史（含供给消息）做一次观测
const observedBefore = observed().length;
const streamNext = async () => "STREAM_SENTINEL";
const streamOut = await main.listeners["llm/stream"](
  { provider: "step-fun", model: "step-5-preview", messages: committed.s1 },
  streamNext,
);
assert("llm/stream passthrough", streamOut === "STREAM_SENTINEL");
const obs = observed();
assert("llm/stream observed supply message", obs.length > observedBefore && obs[obs.length - 1].supply_msg_present === true && obs[obs.length - 1].supply_revision === "rev-after-restart");

console.log("\nALL MOCK TESTS PASSED (v3.2: T1-T10 + llm/stream)");
