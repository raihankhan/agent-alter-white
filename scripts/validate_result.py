#!/usr/bin/env python3
"""Validate Alter White result structure, score arithmetic, and evidence paths."""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from result_checks import check_result, evidence_items  # noqa: E402

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", required=True)
    ap.add_argument("--repo", required=True)
    args = ap.parse_args()
    result_path, repo = Path(args.result), Path(args.repo).resolve()
    obj = json.loads(result_path.read_text())
    errors = check_result(obj)

    if obj.get("repository", {}).get("branch") != "master":
        errors.append("branch must be master")

    # Evidence containment and existence require a live checkout, so they are checked
    # here rather than in result_checks (which must work without a checkout).
    for ev in evidence_items(obj):
        raw_path = ev.get("path", "")
        # @repository-search is an explicit negative-evidence marker used when
        # a feature is absent after repository-wide static inspection.
        if raw_path == "@repository-search" and ev.get("status") == "not_found":
            p = None
        else:
            p = Path(raw_path)
            if p.is_absolute() or ".." in p.parts:
                continue  # already reported by check_result
            resolved = (repo / p).resolve()
            if repo != resolved and repo not in resolved.parents:
                errors.append(f"evidence path escapes repository: {p}")
            elif not resolved.exists():
                errors.append(f"evidence path does not exist: {p}")
        a, b = ev.get("line_start"), ev.get("line_end")
        if a is not None and b is not None and b < a:
            errors.append(f"invalid line range for {p}")

    if errors:
        print("\n".join(f"- {e}" for e in errors), file=sys.stderr)
        sys.exit(1)
    print(f"VALID: {obj['repository']['full_name']} {obj['scores']['total_score']}/50")
if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"validate_result: {e}", file=sys.stderr); sys.exit(1)
