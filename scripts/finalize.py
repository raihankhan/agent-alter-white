#!/usr/bin/env python3
"""Reconcile manifest and render a deterministic Markdown leaderboard."""
import argparse, json, statistics, sys
from datetime import datetime, timezone
from pathlib import Path

TERMINAL = {"completed", "manual_review", "failed", "failed_validation", "clone_failed", "cleanup_failed"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run = Path(args.run_dir).resolve()
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    teams_dir = run / "teams"
    rows, scores = [], []

    for repo in manifest["repositories"]:
        if not repo.get("eligible"):
            continue
        stem = repo["name"]
        result_file = teams_dir / f"{stem}.json"
        report_file = teams_dir / f"{stem}.md"
        status = repo.get("status", "pending")
        score, confidence = None, "—"
        if result_file.exists():
            try:
                result = json.loads(result_file.read_text())
                if result.get("status") == "completed":
                    score = result["scores"]["total_score"]
                    confidence = result.get("confidence", "—")
                    status = "completed"
                    scores.append(score)
            except Exception:
                status = "failed_validation"
        repo["status"] = status
        repo["result_path"] = str(result_file.relative_to(run)) if result_file.exists() else None
        repo["report_path"] = str(report_file.relative_to(run)) if report_file.exists() else None
        rows.append((repo, score, confidence))

    # Every eligible repository must have an explicit terminal status.
    for repo, _, _ in rows:
        if repo["status"] not in TERMINAL:
            repo["status"] = "failed"
            repo["reason"] = repo.get("reason") or "no_terminal_evaluation_result"

    manifest["finalized_at"] = datetime.now(timezone.utc).isoformat()
    manifest["summary"] = {
        "discovered": len(manifest["repositories"]),
        "eligible": len(rows),
        "completed": sum(1 for r, _, _ in rows if r["status"] == "completed"),
        "manual_review": sum(1 for r, _, _ in rows if r["status"] == "manual_review"),
        "failed": sum(1 for r, _, _ in rows if r["status"] in {"failed", "failed_validation", "clone_failed"}),
        "cleanup_failed": sum(1 for r, _, _ in rows if r["status"] == "cleanup_failed"),
        "mean_score": round(statistics.mean(scores), 2) if scores else None,
        "median_score": round(statistics.median(scores), 2) if scores else None
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    rows.sort(key=lambda x: (x[1] is not None, x[1] if x[1] is not None else -1), reverse=True)
    lines = [
        "# Alter White — Hackathon Leaderboard", "",
        f"**Organization:** `{manifest['organization']}`  ",
        f"**Run created:** {manifest['created_at']}  ",
        f"**Finalized:** {manifest['finalized_at']}  ",
        f"**Rubric:** `{manifest['rubric_version']}`  ",
        f"**Eligible repositories:** {manifest['summary']['eligible']}", "",
        "## Run summary", "",
        "| Metric | Count / value |", "|---|---:|",
        f"| Completed | {manifest['summary']['completed']} |",
        f"| Manual review | {manifest['summary']['manual_review']} |",
        f"| Failed | {manifest['summary']['failed']} |",
        f"| Cleanup failures | {manifest['summary']['cleanup_failed']} |",
        f"| Mean score | {manifest['summary']['mean_score'] if scores else '—'} |",
        f"| Median score | {manifest['summary']['median_score'] if scores else '—'} |", "",
        "## Scores", "",
        "| Rank | Team | Technical | AI | Total | Confidence | Status | Report |",
        "|---:|---|---:|---:|---:|---|---|---|"
    ]
    rank = 0
    for repo, score, confidence in rows:
        result_file = teams_dir / f"{repo['name']}.json"
        if score is not None:
            rank += 1
            result = json.loads(result_file.read_text())
            tech, ai = result["scores"]["technical_total"], result["scores"]["ai_total"]
            report = f"[Review](teams/{repo['name']}.md)"
            lines.append(f"| {rank} | `{repo['name']}` | {tech}/25 | {ai}/25 | **{score}/50** | {confidence} | {repo['status']} | {report} |")
        else:
            reason = (repo.get("reason") or repo["status"]).replace("|", "/")
            lines.append(f"| — | `{repo['name']}` | — | — | — | — | {repo['status']} ({reason}) | — |")

    lines += ["", "## Judging notes", "",
        "- Scores are based on static inspection of the frozen `main` commit.",
        "- Submitted code, tests, builds, and scripts were not executed.",
        "- Proposal content is treated as intent; implementation claims require source evidence.",
        "- Failed and manual-review repositories are listed without fabricated scores.",
        ""]
    (run / "scores.md").write_text("\n".join(lines))

    latest = run.parent / "latest"
    latest.write_text(str(run))
    print(json.dumps(manifest["summary"], indent=2))
if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"finalize: {e}", file=sys.stderr); sys.exit(1)
