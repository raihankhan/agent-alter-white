#!/usr/bin/env python3
"""Validate Alter White result structure, score arithmetic, and evidence paths."""
import argparse, json, sys
from pathlib import Path

TECH = {
 "functional_completeness": 5, "architecture_and_design": 4,
 "code_quality": 4, "reliability_and_security": 4,
 "integration_and_execution_evidence": 3
}
AI = {
 "ai_centrality_and_relevance": 4, "intelligence_and_ai_architecture": 4,
 "context_and_data_grounding": 3, "evaluation_and_guardrails": 2,
 "resilience_and_adaptability": 2
}
STATUSES = {"implemented", "partial", "mocked_or_hardcoded", "not_found", "unable_to_verify"}

def evidence_items(obj):
    for section in ("technical", "ai"):
        for criterion in obj["scores"][section].values():
            for ev in criterion["evidence"]:
                yield ev
    for group in ("strengths", "improvement_areas"):
        for finding in obj[group]:
            for ev in finding["evidence"]:
                yield ev

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", required=True)
    ap.add_argument("--repo", required=True)
    args = ap.parse_args()
    result_path, repo = Path(args.result), Path(args.repo).resolve()
    obj = json.loads(result_path.read_text())
    errors = []
    try:
        from jsonschema import Draft202012Validator
        schema_path = Path(__file__).resolve().parents[1] / ".claude/skills/alter-white/evaluation-schema.json"
        schema = json.loads(schema_path.read_text())
        errors.extend(f"schema: {e.message}" for e in Draft202012Validator(schema).iter_errors(obj))
    except ImportError:
        errors.append("jsonschema is not installed; run: python3 -m pip install -r requirements.txt")

    if obj.get("schema_version") != "1.0.0": errors.append("schema_version must be 1.0.0")
    if obj.get("rubric_version") != "1.0.0": errors.append("rubric_version must be 1.0.0")
    if obj.get("status") != "completed": errors.append("status must be completed")
    if obj.get("repository", {}).get("branch") != "main": errors.append("branch must be main")
    if obj.get("verification", {}).get("execution_status") != "not_run_static_review":
        errors.append("execution_status must be not_run_static_review")

    for group, maxima in (("technical", TECH), ("ai", AI)):
        scores = obj.get("scores", {}).get(group, {})
        for key, maximum in maxima.items():
            item = scores.get(key, {})
            if item.get("maximum") != maximum: errors.append(f"{group}.{key}: maximum must be {maximum}")
            if not isinstance(item.get("score"), int) or not 0 <= item.get("score", -1) <= maximum:
                errors.append(f"{group}.{key}: invalid score")
            if not item.get("rationale"): errors.append(f"{group}.{key}: rationale missing")
            if not item.get("evidence"): errors.append(f"{group}.{key}: evidence missing")

    st = sum(obj.get("scores", {}).get("technical", {}).get(k, {}).get("score", 0) for k in TECH)
    ai = sum(obj.get("scores", {}).get("ai", {}).get(k, {}).get("score", 0) for k in AI)
    sc = obj.get("scores", {})
    if sc.get("technical_total") != st: errors.append("technical_total mismatch")
    if sc.get("ai_total") != ai: errors.append("ai_total mismatch")
    if sc.get("total_score") != st + ai: errors.append("total_score mismatch")
    if sc.get("maximum_score") != 35: errors.append("maximum_score must be 35")

    summary = obj.get("review_summary", {})
    for k in ("technical_review", "ai_review", "final_verdict"):
        if not isinstance(summary.get(k), str) or len(summary[k].strip()) < 10:
            errors.append(f"review_summary.{k} missing or too short")

    for ev in evidence_items(obj):
        if ev.get("status") not in STATUSES: errors.append(f"invalid evidence status: {ev.get('status')}")
        raw_path = ev.get("path", "")
        # @repository-search is an explicit negative-evidence marker used when
        # a feature is absent after repository-wide static inspection.
        if raw_path == "@repository-search" and ev.get("status") == "not_found":
            p = None
        else:
            p = Path(raw_path)
            if p.is_absolute() or ".." in p.parts: errors.append(f"unsafe evidence path: {p}")
            else:
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
    print(f"VALID: {obj['repository']['full_name']} {sc['total_score']}/35")
if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"validate_result: {e}", file=sys.stderr); sys.exit(1)
