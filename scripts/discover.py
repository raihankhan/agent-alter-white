#!/usr/bin/env python3
"""Discover eligible team repositories and freeze the target branch commit SHA."""
import argparse, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULTS = {
    "repository_prefix": "team_", "branch": "master",
    "exclude_archived": True, "exclude_forks": True,
    "max_repo_size_mb": 2048, "worker_count": 5,
    "memory_worker": True, "memory_dir": "memory", "memory_poll_seconds": 60
}

def run(args, check=True):
    p = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode:
        raise RuntimeError(p.stderr.strip() or f"Command failed: {args[0]}")
    return p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", required=True)
    ap.add_argument("--config", default="config/alter-white.json")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    cfg = dict(DEFAULTS)
    warnings = []
    cp = Path(args.config)
    if cp.exists():
        try:
            loaded = json.loads(cp.read_text())
        except Exception as e:
            loaded = {}
            warnings.append(f"config {cp} is not readable JSON ({e}); using defaults")
        for key, value in loaded.items():
            if key not in DEFAULTS:
                warnings.append(f"unknown config key ignored: {key}")
                continue
            if isinstance(DEFAULTS[key], bool) and not isinstance(value, bool):
                warnings.append(f"config {key} must be a boolean; using default")
                continue
            if isinstance(DEFAULTS[key], int) and not isinstance(value, int):
                warnings.append(f"config {key} must be an integer; using default")
                continue
            if isinstance(DEFAULTS[key], str) and not isinstance(value, str):
                warnings.append(f"config {key} must be a string; using default")
                continue
            cfg[key] = value
    if cfg["worker_count"] > 5:
        warnings.append("worker_count above 5 exceeds the judging concurrency ceiling; clamped to 5")
        cfg["worker_count"] = 5
    if cfg["worker_count"] < 1:
        warnings.append("worker_count below 1; clamped to 1")
        cfg["worker_count"] = 1

    run(["gh", "auth", "status"])
    repos_raw = run([
        "gh", "repo", "list", args.org, "--limit", "1000",
        "--json", "name,nameWithOwner,url,isArchived,isFork,diskUsage"
    ]).stdout
    repos = json.loads(repos_raw)
    entries, eligible = [], []

    for r in repos:
        name = r.get("name", "")
        entry = {
            "full_name": r.get("nameWithOwner"),
            "name": name,
            "url": r.get("url"),
            "is_archived": bool(r.get("isArchived")),
            "is_fork": bool(r.get("isFork")),
            "disk_usage_kb": int(r.get("diskUsage") or 0),
            "branch": cfg["branch"],
            "commit_sha": None,
            "proposal_source": None,
            "proposal_readable_path": None,
            "proposal_error": None,
            "eligible": False,
            "status": "excluded",
            "reason": None
        }
        if not name.startswith(cfg["repository_prefix"]):
            entry["reason"] = "name_prefix_mismatch"
        elif cfg["exclude_archived"] and entry["is_archived"]:
            entry["reason"] = "archived"
        elif cfg["exclude_forks"] and entry["is_fork"]:
            entry["reason"] = "fork"
        elif entry["disk_usage_kb"] > int(cfg["max_repo_size_mb"]) * 1024:
            entry["status"], entry["reason"] = "manual_review", "repository_exceeds_size_limit"
        else:
            full = entry["full_name"]
            commit = run(["gh", "api", f"repos/{full}/commits/{cfg['branch']}", "--jq", ".sha"], check=False)
            if commit.returncode:
                entry["reason"] = "target_branch_missing_or_inaccessible"
            else:
                sha = commit.stdout.strip()
                if not sha:
                    entry["reason"] = "commit_sha_unavailable"
                else:
                    entry.update({
                        "commit_sha": sha, "eligible": True,
                        "status": "pending", "reason": None
                    })
                    eligible.append(entry)
        entries.append(entry)

    manifest = {
        "manifest_version": "1.0.0",
        "organization": args.org,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rubric_version": "1.1.0",
        "schema_version": "1.1.0",
        "config": cfg,
        "summary": {
            "discovered": len(entries),
            "eligible": len(eligible),
            "excluded": len(entries) - len(eligible)
        },
        "repositories": entries,
        "attempts": [],
        "warnings": warnings,
        "reused": []
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest["summary"]))
if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"discover: {e}", file=sys.stderr); sys.exit(1)
