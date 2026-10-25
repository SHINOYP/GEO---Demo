import { spawn } from "node:child_process";
import type { AnalysisResult, ErrorPayload } from "./types";
import { isErrorPayload } from "./types";
import { cliPath, pythonBin } from "./paths";

export type BridgeResult<T> =
  | { ok: true; status: 200; body: T }
  | { ok: false; status: number; body: ErrorPayload };

function statusForKind(kind: ErrorPayload["kind"]): number {
  if (kind === "validation") return 400;
  if (kind === "scraping") return 422;
  return 500;
}

function internalError(message: string): ErrorPayload {
  return { error: true, kind: "internal", message };
}

export async function runAnalyze(
  url: string,
  html?: string,
): Promise<BridgeResult<AnalysisResult>> {
  const args = ["analyze", url];
  if (html) args.push("--html-stdin");

  const { stdout, stderr, code } = await spawnCollectText(args, html);
  if (stderr) console.error("[cli.py analyze stderr]", stderr);

  let parsed: unknown;
  try {
    parsed = JSON.parse(stdout);
  } catch {
    return {
      ok: false,
      status: 500,
      body: internalError("Malformed response from the analysis engine."),
    };
  }

  if (code !== 0 || isErrorPayload(parsed)) {
    const err = isErrorPayload(parsed)
      ? parsed
      : internalError("Analysis engine exited with an error.");
    return { ok: false, status: statusForKind(err.kind), body: err };
  }

  return { ok: true, status: 200, body: parsed as AnalysisResult };
}

export async function runReport(
  analysis: AnalysisResult,
): Promise<
  | { ok: true; status: 200; body: Buffer }
  | { ok: false; status: number; body: ErrorPayload }
> {
  const { stdout, stderr, code } = await spawnCollectBuffer(
    ["report"],
    JSON.stringify(analysis),
  );
  if (stderr) console.error("[cli.py report stderr]", stderr.toString("utf-8"));

  if (code !== 0) {
    let err: ErrorPayload;
    try {
      const parsed = JSON.parse(stdout.toString("utf-8"));
      err = isErrorPayload(parsed) ? parsed : internalError("Report generation failed.");
    } catch {
      err = internalError("Report generation failed.");
    }
    return { ok: false, status: statusForKind(err.kind), body: err };
  }

  return { ok: true, status: 200, body: stdout };
}

function spawnCollectText(
  args: string[],
  stdin?: string,
): Promise<{ stdout: string; stderr: string; code: number }> {
  return new Promise((resolve, reject) => {
    const child = spawn(pythonBin(), [cliPath(), ...args], { shell: false });
    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];

    child.stdout.on("data", (chunk: Buffer) => stdoutChunks.push(chunk));
    child.stderr.on("data", (chunk: Buffer) => stderrChunks.push(chunk));
    child.on("error", (err) => reject(err));
    child.on("close", (code) => {
      resolve({
        stdout: Buffer.concat(stdoutChunks).toString("utf-8"),
        stderr: Buffer.concat(stderrChunks).toString("utf-8"),
        code: code ?? 1,
      });
    });

    if (stdin !== undefined) child.stdin.write(stdin, "utf-8");
    child.stdin.end();
  });
}

function spawnCollectBuffer(
  args: string[],
  stdin?: string,
): Promise<{ stdout: Buffer; stderr: Buffer; code: number }> {
  return new Promise((resolve, reject) => {
    const child = spawn(pythonBin(), [cliPath(), ...args], { shell: false });
    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];

    // Deliberately never call setEncoding() on stdout here — the `report`
    // subcommand's success payload is raw PDF bytes, and decoding/re-encoding
    // them as text would corrupt the file.
    child.stdout.on("data", (chunk: Buffer) => stdoutChunks.push(chunk));
    child.stderr.on("data", (chunk: Buffer) => stderrChunks.push(chunk));
    child.on("error", (err) => reject(err));
    child.on("close", (code) => {
      resolve({
        stdout: Buffer.concat(stdoutChunks),
        stderr: Buffer.concat(stderrChunks),
        code: code ?? 1,
      });
    });

    if (stdin !== undefined) child.stdin.write(stdin, "utf-8");
    child.stdin.end();
  });
}
