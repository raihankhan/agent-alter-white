#!/usr/bin/env python3
"""Safely remove one checkout only when it is inside this run's workspaces root."""
import argparse, shutil, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--workspace", required=True)
    args = ap.parse_args()

    run_root = Path(args.run_dir).resolve(strict=True)
    work_root = (run_root / "workspaces").resolve()
    target = Path(args.workspace).resolve(strict=True)

    if work_root != target and work_root not in target.parents:
        raise SystemExit(f"Refusing cleanup outside workspaces root: {target}")
    if target == work_root or target == run_root:
        raise SystemExit("Refusing to remove workspace root")
    if not target.is_dir():
        raise SystemExit("Target is not a directory")
    shutil.rmtree(target)
    print(f"removed {target}")
if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"cleanup_workspace: {e}", file=sys.stderr); sys.exit(1)
