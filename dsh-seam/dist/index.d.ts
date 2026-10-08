/**
 * D4-spike dist 类型声明（手写，与 dist/index.js 对应）。
 * spike 级：发布门阶段以真实 tsc 从 src/index.ts 重建。
 */
import type { Context } from "@deepseek-ai/cordis";
import type z from "@deepseek-ai/schemastery";

export declare const Config: z.ZodType<{
  mode: "off" | "shadow" | "on";
  clProject: string;
  clHome: string;
  tracePath: string;
  verbose: boolean;
}>;

export type SeamConfig = {
  mode: "off" | "shadow" | "on";
  clProject: string;
  clHome: string;
  tracePath: string;
  verbose: boolean;
};

export declare function apply(ctx: Context, config: SeamConfig): void;

export declare const name: "@contextledger/dsh-host-seam";
export declare const inject: ["logger"];
