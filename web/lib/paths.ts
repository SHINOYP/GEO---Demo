import path from "node:path";

// repoRoot: web/ is a direct child of the repo root, so one level up from
// this project's own directory. Overridable via CITELYTICS_REPO_ROOT for
// robustness against being started from an unexpected working directory.
export function repoRoot(): string {
  return process.env.CITELYTICS_REPO_ROOT || path.resolve(process.cwd(), "..");
}

export function cliPath(): string {
  return path.join(repoRoot(), "citation-predictor", "backend", "cli.py");
}

// The project's existing venv (see README.md) — not the system
// Python, so the ML deps (xgboost/shap/etc.) are guaranteed available.
export function pythonBin(): string {
  if (process.env.CITELYTICS_PYTHON_BIN) return process.env.CITELYTICS_PYTHON_BIN;
  const root = repoRoot();
  if (process.platform === "win32") {
    return path.join(root, ".venv", "Scripts", "python.exe");
  }
  return path.join(root, ".venv", "bin", "python3");
}
