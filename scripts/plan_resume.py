#!/usr/bin/env python3
"""Plan and apply resume of a prior Alter White run.

For every eligible repository in the current run's manifest, decide one of:

  reuse_score   a prior result is valid and matches the frozen inputs; copy it forward
  reuse_memory  no valid prior result, but the memory wiki holds matching context
  reevaluate    neither

Matching is keyed on the bare repository name plus an explicit organization check, because the
result JSON records `repository.full_name` as a bare name while the manifest records `org/repo`.
"""
import argparse, json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from result_checks import check_file  # noqa: E402

REUSE_SCORE = "reuse_score"
REUSE_MEMORY = "reuse_memory"
REEVALUATE = "reevaluate"


def bare_name(full_name):
    """`org/team_x` -> `team_x`; a bare name is returned unchanged."""
    if not full_name:
        return ""
    return full_name.rstrip("/").rsplit("/", 1)[-1]


def org_of(full_name):
    """`org/team_x` -> `org`; a bare name has no organization.

    Also accepts a repository URL, in which case the organization is the path segment
    after the host: `https://github.com/org/team_x` -> `org`.
    """
    if not full_name:
        return None
    value = full_name.rstrip("/")
    if "://" in value:
        parts = value.split("://", 1)[1].split("/")
        # parts[0] is the host; the organization is the next segment, if any.
        return parts[1] if len(parts) > 2 else None
    if "/" not in value:
        return None
    return value.rsplit("/", 1)[0]


def read_manifest(run_dir):
    path = Path(run_dir) / "manifest.json"
    if not path.exists():
        raise SystemExit(f"plan_resume: manifest not found: {path}")
    return json.loads(path.read_text())


def parse_memory_page(path):
    """Parse a memory page's front-matter. Returns a dict, or None if unusable."""
    try:
        text = path.read_text()
    except Exception:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    meta = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta or None


def memory_matches(meta, repo, org, rubric_version, schema_version):
    """A memory page is reusable only if it describes the same commit and the same rubric."""
    if not meta:
        return False
    if bare_name(meta.get("project", "")) != repo["name"]:
        return False
    if meta.get("commit_sha") != repo.get("commit_sha"):
        return False
    if meta.get("rubric_version") != rubric_version:
        return False
    if meta.get("schema_version") != schema_version:
        return False
    page_org = org_of(meta.get("repo_url", ""))
    if page_org and org and page_org != org:
        return False
    return True


def result_matches(obj, repo, org, rubric_version, schema_version):
    """A prior result is reusable only if identity, commit and versions all match."""
    if not obj:
        return False
    repository = obj.get("repository", {})
    if bare_name(repository.get("full_name", "")) != repo["name"]:
        return False
    if repository.get("commit_sha") != repo.get("commit_sha"):
        return False
    if repository.get("branch") != repo.get("branch"):
        return False
    if obj.get("rubric_version") != rubric_version:
        return False
    if obj.get("schema_version") != schema_version:
        return False
    if repository.get("url") and repo.get("url") and repository["url"] != repo["url"]:
        return False
    result_org = org_of(repository.get("full_name", ""))
    if result_org and org and result_org != org:
        return False
    return True


def find_prior_run(run_dir, explicit):
    if explicit:
        p = Path(explicit)
        if not (p / "manifest.json").exists():
            raise SystemExit(f"plan_resume: prior run has no manifest: {p}")
        return p
    results_root = Path(run_dir).resolve().parent
    candidates = sorted(
        (d for d in results_root.glob("*") if (d / "manifest.json").exists()),
        key=lambda d: d.name,
    )
    for d in reversed(candidates):
        if d.resolve() != Path(run_dir).resolve():
            return d
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--prior-run", default=None)
    ap.add_argument("--memory", default="memory")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).resolve()
    manifest = read_manifest(run_dir)
    org = manifest.get("organization")
    rubric_version = manifest.get("rubric_version")
    schema_version = manifest.get("schema_version")

    prior = find_prior_run(run_dir, args.prior_run)
    prior_manifest = read_manifest(prior) if prior else {"repositories": []}
    prior_by_name = {
        bare_name(r.get("full_name", "")): r
        for r in prior_manifest.get("repositories", [])
    }

    memory_root = Path(args.memory)
    teams_dir = run_dir / "teams"
    teams_dir.mkdir(parents=True, exist_ok=True)

    plan, reused = [], []
    for repo in manifest.get("repositories", []):
        if not repo.get("eligible"):
            continue
        name = repo["name"]
        decision, reason, source = REEVALUATE, None, None

        prior_entry = prior_by_name.get(name)
        if prior_entry and prior:
            prior_result = prior / "teams" / f"{name}.json"
            if prior_result.exists():
                errors, obj = check_file(prior_result)
                if errors:
                    reason = "prior result failed validation: " + errors[0]
                elif not result_matches(
                    obj, repo, org, rubric_version, schema_version
                ):
                    reason = "prior result does not match the frozen commit or versions"
                else:
                    decision, source = REUSE_SCORE, prior_result

        if decision == REEVALUATE:
            page = memory_root / "pages" / "teams" / f"{name}.md"
            meta = parse_memory_page(page) if page.exists() else None
            if meta and memory_matches(
                meta, repo, org, rubric_version, schema_version
            ):
                decision, source = REUSE_MEMORY, page
                reason = "matching memory page available"

        plan.append(
            {
                "repository": name,
                "decision": decision,
                "reason": reason,
                "source": str(source) if source else None,
            }
        )

        if args.apply and decision == REUSE_SCORE and source:
            target_json = teams_dir / f"{name}.json"
            shutil.copyfile(source, target_json)
            prior_md = source.with_suffix(".md")
            if prior_md.exists():
                shutil.copyfile(prior_md, teams_dir / f"{name}.md")
            reused.append(
                {
                    "repository": name,
                    "commit_sha": repo.get("commit_sha"),
                    "rubric_version": rubric_version,
                    "schema_version": schema_version,
                    "source_run": prior.name if prior else None,
                    "attempts": 1,
                }
            )
            repo["status"] = "completed"
            repo["reused"] = True

    counts = {
        REUSE_SCORE: sum(1 for p in plan if p["decision"] == REUSE_SCORE),
        REUSE_MEMORY: sum(1 for p in plan if p["decision"] == REUSE_MEMORY),
        REEVALUATE: sum(1 for p in plan if p["decision"] == REEVALUATE),
    }

    if args.apply:
        manifest["reused"] = reused
        manifest.setdefault("attempts", []).extend(reused)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    output = {
        "run_dir": str(run_dir),
        "prior_run": str(prior) if prior else None,
        "organization": org,
        "rubric_version": rubric_version,
        "schema_version": schema_version,
        "counts": counts,
        "applied": bool(args.apply),
        "plan": plan,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"plan_resume: {e}", file=sys.stderr)
        sys.exit(1)
