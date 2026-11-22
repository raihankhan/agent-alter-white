#!/usr/bin/env python3
"""Clone a frozen commit into a constrained run workspace."""
import argparse, json, re, subprocess, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--worker", type=int, required=True)
    ap.add_argument("--repo", required=True, help="full_name, e.g. org/team_alpha")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    item = next((r for r in manifest["repositories"] if r["full_name"] == args.repo), None)
    if not item or not item.get("eligible") or not item.get("commit_sha"):
        raise SystemExit("Repository is not eligible in this manifest")

    owner, name = item["full_name"].split("/", 1)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise SystemExit("Unsafe repository name")

    run_root = Path(args.run_dir).resolve()
    work_root = (run_root / "workspaces").resolve()
    destination = (work_root / f"worker-{args.worker}" / name).resolve()
    if work_root not in destination.parents:
        raise SystemExit("Destination escaped workspace root")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise SystemExit(f"Destination already exists: {destination}")

    depth = int(manifest.get("config", {}).get("shallow_clone_depth", 1))
    # Fetch the frozen SHA directly. A normal --branch master shallow clone can
    # miss the discovery SHA if the branch advances between discovery and cloning.
    destination.mkdir(parents=True)
    commands = [
        ["git", "-C", str(destination), "init", "--quiet"],
        ["git", "-C", str(destination), "remote", "add", "origin", item["url"]],
        ["git", "-C", str(destination), "fetch", "--quiet", "--depth", str(depth), "origin", item["commit_sha"]],
        ["git", "-C", str(destination), "checkout", "--quiet", "--detach", "FETCH_HEAD"],
    ]
    for cmd in commands:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode:
            raise SystemExit(p.stderr.strip() or f"command failed: {cmd[3] if len(cmd) > 3 else cmd[-1]}")

    actual = subprocess.check_output(["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip()
    if actual != item["commit_sha"]:
        raise SystemExit(f"SHA mismatch: expected {item['commit_sha']}, got {actual}")

    print(json.dumps({
        "full_name": item["full_name"], "commit_sha": actual,
        "workspace": str(destination), "worker": args.worker
    }))
if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"prepare_workspace: {e}", file=sys.stderr); sys.exit(1)
