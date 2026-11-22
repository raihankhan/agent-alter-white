#!/usr/bin/env python3
"""Path-independent validation of an Alter White result.

Used when a prior result is considered for reuse: the checkout may no longer exist, so evidence
containment and existence cannot be checked here. Those checks live in `validate_result.py`, which
runs against a live evaluation.
"""
import json
from pathlib import Path

RUBRIC_VERSION = "1.1.0"
SCHEMA_VERSION = "1.1.0"

TECH = {
    "functional_completeness": 6,
    "architecture_and_design": 5,
    "code_quality": 5,
    "reliability_and_security": 5,
    "integration_and_execution_evidence": 4,
}
AI = {
    "ai_centrality_and_relevance": 5,
    "intelligence_and_ai_architecture": 6,
    "context_and_data_grounding": 5,
    "evaluation_and_guardrails": 4,
    "resilience_and_adaptability": 5,
}
STATUSES = {"implemented", "partial", "mocked_or_hardcoded", "not_found", "unable_to_verify"}

REVIEW_FIELDS = ("technical_review", "ai_review", "final_verdict")


def schema_path():
    """Locate the canonical schema next to this script, falling back to the .puku tree."""
    root = Path(__file__).resolve().parents[1]
    for candidate in (
        root / ".puku/skills/alter-white/evaluation-schema.json",
        root / ".claude/skills/alter-white/evaluation-schema.json",
    ):
        if candidate.exists():
            return candidate
    return root / ".puku/skills/alter-white/evaluation-schema.json"


def evidence_items(obj):
    for section in ("technical", "ai"):
        for criterion in obj.get("scores", {}).get(section, {}).values():
            for ev in criterion.get("evidence", []):
                yield ev
    for group in ("strengths", "improvement_areas"):
        for finding in obj.get(group, []):
            for ev in finding.get("evidence", []):
                yield ev


def check_result(obj):
    """Return a list of error strings for a parsed result object."""
    errors = []

    try:
        from jsonschema import Draft202012Validator

        schema = json.loads(schema_path().read_text())
        errors.extend(
            f"schema: {e.message}" for e in Draft202012Validator(schema).iter_errors(obj)
        )
    except ImportError:
        errors.append(
            "jsonschema is not installed; run: python3 -m pip install -r requirements.txt"
        )
    except Exception as e:
        errors.append(f"schema could not be loaded: {e}")

    if obj.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if obj.get("rubric_version") != RUBRIC_VERSION:
        errors.append(f"rubric_version must be {RUBRIC_VERSION}")
    if obj.get("status") != "completed":
        errors.append("status must be completed")

    scores = obj.get("scores", {})
    for group, maxima in (("technical", TECH), ("ai", AI)):
        section = scores.get(group, {})
        for key, maximum in maxima.items():
            item = section.get(key, {})
            if item.get("maximum") != maximum:
                errors.append(f"{group}.{key}: maximum must be {maximum}")
            value = item.get("score")
            if not isinstance(value, int) or not 0 <= value <= maximum:
                errors.append(f"{group}.{key}: invalid score")
            if not item.get("rationale"):
                errors.append(f"{group}.{key}: rationale missing")
            if not item.get("evidence"):
                errors.append(f"{group}.{key}: evidence missing")

    st = sum(scores.get("technical", {}).get(k, {}).get("score", 0) for k in TECH)
    ai = sum(scores.get("ai", {}).get(k, {}).get("score", 0) for k in AI)
    if scores.get("technical_total") != st:
        errors.append("technical_total mismatch")
    if scores.get("ai_total") != ai:
        errors.append("ai_total mismatch")
    if scores.get("total_score") != st + ai:
        errors.append("total_score mismatch")
    if scores.get("maximum_score") != 50:
        errors.append("maximum_score must be 50")

    summary = obj.get("review_summary", {})
    for key in REVIEW_FIELDS:
        value = summary.get(key)
        if not isinstance(value, str) or len(value.strip()) < 10:
            errors.append(f"review_summary.{key} missing or too short")

    for ev in evidence_items(obj):
        if ev.get("status") not in STATUSES:
            errors.append(f"invalid evidence status: {ev.get('status')}")
        raw_path = ev.get("path", "")
        if raw_path == "@repository-search" and ev.get("status") == "not_found":
            pass
        else:
            p = Path(raw_path)
            if p.is_absolute() or ".." in p.parts:
                errors.append(f"unsafe evidence path: {p}")
        a, b = ev.get("line_start"), ev.get("line_end")
        if a is not None and b is not None and b < a:
            errors.append(f"invalid line range for {raw_path}")

    verification = obj.get("verification", {})
    if verification.get("execution_status") != "not_run_static_review":
        errors.append("execution_status must be not_run_static_review")
    if not verification.get("limitations"):
        errors.append("verification.limitations missing")

    return errors


def check_file(path):
    """Return (errors, parsed_result_or_None) for a result file on disk."""
    try:
        obj = json.loads(Path(path).read_text())
    except Exception as e:
        return [f"result file is not readable JSON: {e}"], None
    return check_result(obj), obj


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--result", required=True)
    args = ap.parse_args()
    errs, _ = check_file(args.result)
    if errs:
        print("\n".join(f"- {e}" for e in errs), file=sys.stderr)
        sys.exit(1)
    print(f"VALID: {args.result}")
