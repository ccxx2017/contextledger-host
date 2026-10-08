# @contextledger/dsh-host-seam（D4-spike 最小 Bundle）

钉扎 DSH 0.2.0-rc.2。公开接口接入；私有内部接口与宿主补丁均为零。

- 插件根：`src/index.ts` —— named `apply` 命名空间 + `Config`（schemastery Standard Schema）+ `inject`；
- 随包补丁：`cordis.patch.yml`（`dsh.bundle.patch` 指向）；
- 构建：`tsc -p tsconfig.json` → `dist/index.js` + `dist/index.d.ts`。

三模式语义见 `src/index.ts` 头注与 `../d4_spike/01_isolation_mode_design.md` §2.2。

**本包为 spike 级**：发布门（typecheck/tests/validate_plugin/accept_plugin/清洁包/新 Profile 门）
在交付阶段按 deepseek-harness-plugin-creator 技能补做；本阶段只证明真实 Loader 可加载与行为。
