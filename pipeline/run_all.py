"""
Run the full real-data pilot pipeline: collect_citations -> collect_candidates
-> build_dataset -> pilot_stats.

Usage (Windows PowerShell or bash — identical, just use `python` or `python3`):
    python -m pipeline.run_all --dry-run
    python -m pipeline.run_all --yes --max-calls 60 --repeats 1
"""
import argparse
import subprocess
import sys


def run(cmd):
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Step failed: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(result.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--max-calls", type=int, default=60)
    ap.add_argument("--repeats", type=int, default=1)
    args = ap.parse_args()

    py = sys.executable

    flags = ["--dry-run"] if args.dry_run else (["--yes", "--max-calls", str(args.max_calls)])

    run([py, "-m", "pipeline.collect_citations", *flags, "--repeats", str(args.repeats)])
    run([py, "-m", "pipeline.collect_candidates", *flags])

    if args.dry_run:
        print("\n--dry-run: stopping before build_dataset/pilot_stats "
              "(they need real collected data to do anything meaningful).")
        return

    run([py, "-m", "pipeline.build_dataset"])
    run([py, "-m", "pipeline.pilot_stats"])

    print("\nPipeline complete. Next: python -m pipeline.evaluate")


if __name__ == "__main__":
    main()
