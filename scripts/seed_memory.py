#!/usr/bin/env python3
"""Create the Alter White memory tree (LLM Wiki layers) if it does not exist."""
import argparse, json, sys
from pathlib import Path

AGENTS_MD = """# Alter White Memory — Schema Layer

This directory is an **LLM Wiki** in the Karpathy format: raw sources, a wiki of interlinked
markdown pages, and a schema (this file) that governs both.

The memory layer is a **context** layer. It exists so a crashed or interrupted judging run can
resume from where it stopped instead of re-reading every proposal from scratch.

## Layers

| Layer | Path | Mutability | Owner |
|---|---|---|---|
| Raw sources | `sources/` | immutable once written, rewritten per run | memory worker |
| The wiki | `index.md`, `log.md`, `overview.md`, `pages/` | rewritten in place | memory worker |
| The schema | `AGENTS.md` | stable | humans |

## Non-negotiable rules

1. **Memory never scores.** No page may contain a score, a score total, a rubric dimension name,
   a verdict, or a ranking. `scripts/memory_lint.py` enforces this. The score layer
   (`results/<run>/teams/`) is authoritative; memory only describes *what was found*.
2. **Memory never writes outside `memory/`.** The memory worker has no Bash access, so this is
   structural, not merely instructed.
3. **`index.md` is the entry point.** Read it first on any query; it lists every page.
4. **`log.md` is append-only.** Never edit or delete an existing entry.
5. **Every page carries front-matter** matching the contract below. `commit_sha`,
   `rubric_version`, and `schema_version` together decide whether a page may be reused across runs.
6. **Raw sources are never edited by hand.** They are the extracted proposal text.

## Front-matter contract

Every page under `pages/` starts with:

```yaml
---
project: team_YorHa              # bare repository name
repo_url: https://github.com/<org>/team_YorHa
commit_sha: 328afc02d1a6d69b05373b821edf5282cf043625
branch: master
rubric_version: 1.1.0
schema_version: 1.1.0
status: proposed | judged
proposal_source: project.pdf | project.docx | missing | unreadable
updated: 2026-11-22T19:28:05Z
---
```

`status` semantics:

- `proposed` — the proposal was read and the context captured, but judging had not produced a
  terminal result when the page was written. **This is the crash-resilience guarantee**: if the run
  dies during judging, the context already exists.
- `judged` — a terminal result exists in `results/<run>/teams/<project>.json` and the page was
  upgraded with a score-neutral description of what was found.

## Page structure

A team page uses these sections, in this order:

```markdown
# team_YorHa

<one-paragraph summary of the intended product>

## Problem and users

## Intended AI approach

## Named technologies

## Evaluation plan

## Risks and open questions

## What was found in the repository     (status: judged only)
```

Concept pages under `pages/concepts/` describe a pattern that recurs across projects. They use
front-matter with `concept: <slug>` plus `projects: [...]` listing the teams it applies to.

## `index.md` format

A table, one row per page. Updated on every ingest. Sorted by project name.

```markdown
| Project | Status | Proposal | Commit | Page |
|---|---|---|---|---|
| `team_YorHa` | judged | project.pdf | 328afc0 | [page](pages/teams/team_YorHa.md) |
```

## `log.md` format

Append-only. Each entry begins with exactly `## [YYYY-MM-DD] <op> | <title>` so that
`grep "^## \\[" memory/log.md | tail -5` yields the last five operations. Operations are
`ingest`, `update`, and `lint`.

## Lint rules

`python3 scripts/memory_lint.py --memory memory` checks:

1. Every page under `pages/` has valid front-matter with all required keys.
2. `commit_sha` is a 40-character hex string.
3. `status` is one of `proposed`, `judged`.
4. Every page appears in `index.md`, and every `index.md` row points at an existing page.
5. Every `log.md` heading matches `## [YYYY-MM-DD] <op> | <title>`.
6. **Score leak**: no page contains a score pattern (`/25`, `/50`, `total_score`, `technical_total`,
   `ai_total`, or a rubric dimension name). A violation is an error, because memory must never
   influence a score.
7. Page files are non-empty and their front-matter block is closed.

## Operations

- **Ingest** — read a proposal, write the raw source, write the page, update the index, append the log.
- **Query** — read `index.md`, follow links to pages, read raw sources when exact wording matters.
- **Lint** — run `scripts/memory_lint.py`.
"""

INDEX_MD = """# Memory Index

Content catalog for the Alter White memory wiki. **Read this file first** when querying the memory.

| Project | Status | Proposal | Commit | Page |
|---|---|---|---|---|

<!-- Rows are appended by the memory worker. One row per ingested project. -->
"""

LOG_MD = """# Memory Log

Append-only operation log. Each entry starts with `## [YYYY-MM-DD] <op> | <title>` so that
`grep "^## \\[" memory/log.md | tail -5` yields the five most recent operations.

<!-- Entries are appended by the memory worker. Never edit an existing entry. -->
"""

OVERVIEW_MD = """# Overview

Cross-project synthesis for the Alter White memory wiki.

This page holds patterns that recur across submissions: recurring architecture choices, recurring
evaluation plans, recurring gaps. It is written by the memory worker after ingesting pages, and it
is **descriptive only** — it contains no scores and no rankings.

## Conventions

- One page per project under `pages/teams/`.
- One page per recurring concept under `pages/concepts/`.
- Raw proposal text under `sources/`.

## Recurring patterns

<!-- Filled in by the memory worker as concepts emerge across projects. -->
"""

DEFAULT_FILES = {
    "AGENTS.md": AGENTS_MD,
    "index.md": INDEX_MD,
    "log.md": LOG_MD,
    "overview.md": OVERVIEW_MD,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--memory", default="memory")
    args = ap.parse_args()

    root = Path(args.memory)
    created = []
    for sub in ("pages/teams", "pages/concepts", "sources", "state"):
        d = root / sub
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))
    for name, content in DEFAULT_FILES.items():
        p = root / name
        if not p.exists():
            p.write_text(content)
            created.append(str(p))

    print(json.dumps({"memory_root": str(root.resolve()), "created": created}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"seed_memory: {e}", file=sys.stderr)
        sys.exit(1)
