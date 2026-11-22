#!/usr/bin/env python3
"""Lint the Alter White memory wiki.

Checks the schema layer contract in `memory/AGENTS.md`:
front-matter validity, index coverage, log entry format, and — most importantly — that no page
leaks a score. Memory must never influence a score.
"""
import argparse, json, re, sys
from pathlib import Path

REQUIRED_TEAM_KEYS = (
    "project",
    "commit_sha",
    "branch",
    "rubric_version",
    "schema_version",
    "status",
    "proposal_source",
    "updated",
)
VALID_STATUS = {"proposed", "judged"}
LOG_HEADING = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] (ingest|update|lint) \| .+$")
SHA = re.compile(r"^[0-9a-f]{40}$")

# Score-shaped content. A page containing any of these is leaking a score.
SCORE_PATTERNS = (
    (re.compile(r"\b\d{1,2}\s*/\s*25\b"), "score out of 25"),
    (re.compile(r"\b\d{1,2}\s*/\s*50\b"), "score out of 50"),
    (re.compile(r"\btotal_score\b", re.I), "total_score field"),
    (re.compile(r"\btechnical_total\b", re.I), "technical_total field"),
    (re.compile(r"\bai_total\b", re.I), "ai_total field"),
    (re.compile(r"\bfunctional_completeness\b", re.I), "rubric dimension name"),
    (re.compile(r"\barchitecture_and_design\b", re.I), "rubric dimension name"),
    (re.compile(r"\bcode_quality\b", re.I), "rubric dimension name"),
    (re.compile(r"\breliability_and_security\b", re.I), "rubric dimension name"),
    (re.compile(r"\bintegration_and_execution_evidence\b", re.I), "rubric dimension name"),
    (re.compile(r"\bai_centrality_and_relevance\b", re.I), "rubric dimension name"),
    (re.compile(r"\bintelligence_and_ai_architecture\b", re.I), "rubric dimension name"),
    (re.compile(r"\bcontext_and_data_grounding\b", re.I), "rubric dimension name"),
    (re.compile(r"\bevaluation_and_guardrails\b", re.I), "rubric dimension name"),
    (re.compile(r"\bresilience_and_adaptability\b", re.I), "rubric dimension name"),
    (re.compile(r"\bscored\b", re.I), "scoring language"),
    (re.compile(r"\bfinal score\b", re.I), "scoring language"),
    (re.compile(r"\bquality score\b", re.I), "scoring language"),
)


def parse_front_matter(text):
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    meta = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, parts[2]


def lint_page(path, errors):
    text = path.read_text()
    if not text.strip():
        errors.append(f"{path}: page is empty")
        return None
    meta, body = parse_front_matter(text)
    if meta is None:
        errors.append(f"{path}: missing or unterminated front-matter block")
        return None

    if "teams" in path.parts:
        for key in REQUIRED_TEAM_KEYS:
            if key not in meta or not meta[key]:
                errors.append(f"{path}: front-matter missing '{key}'")
        sha = meta.get("commit_sha", "")
        if sha and not SHA.match(sha):
            errors.append(f"{path}: commit_sha is not a 40-character hex sha")
        status = meta.get("status", "")
        if status and status not in VALID_STATUS:
            errors.append(f"{path}: status must be one of {sorted(VALID_STATUS)}")

    for pattern, label in SCORE_PATTERNS:
        match = pattern.search(body)
        if match:
            errors.append(f"{path}: score leak ({label}): {match.group(0)!r}")
    return meta


def lint_index(memory_root, errors):
    index = memory_root / "index.md"
    if not index.exists():
        errors.append(f"{index}: missing")
        return
    text = index.read_text()
    linked = set(re.findall(r"\]\((pages/[^)]+)\)", text))
    for rel in sorted(linked):
        if not (memory_root / rel).exists():
            errors.append(f"{index}: row points at a missing page: {rel}")

    pages = {
        str(p.relative_to(memory_root))
        for p in (memory_root / "pages" / "teams").glob("*.md")
    } | {
        str(p.relative_to(memory_root))
        for p in (memory_root / "pages" / "concepts").glob("*.md")
    }
    for page in sorted(pages):
        if page not in linked:
            errors.append(f"{index}: page is not listed in the index: {page}")


def lint_log(memory_root, errors):
    log = memory_root / "log.md"
    if not log.exists():
        errors.append(f"{log}: missing")
        return
    for line in log.read_text().splitlines():
        if line.startswith("## "):
            if not LOG_HEADING.match(line):
                errors.append(f"{log}: malformed entry heading: {line!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--memory", default="memory")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    memory_root = Path(args.memory)
    errors = []
    if not memory_root.exists():
        errors.append(f"{memory_root}: memory directory does not exist")

    pages = []
    if memory_root.exists():
        for section in ("teams", "concepts"):
            directory = memory_root / "pages" / section
            if not directory.exists():
                continue
            for page in sorted(directory.glob("*.md")):
                pages.append(str(page))
                lint_page(page, errors)
        lint_index(memory_root, errors)
        lint_log(memory_root, errors)

    if args.json:
        print(json.dumps({"pages": len(pages), "errors": errors}, indent=2))
    else:
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        print(f"memory_lint: {len(pages)} pages, {len(errors)} errors")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"memory_lint: {e}", file=sys.stderr)
        sys.exit(1)
