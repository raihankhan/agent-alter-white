# Alter White judging rubric

**Rubric version:** 1.1.0  
**Maximum score:** 50 points  
**Evaluation mode:** Static repository inspection; no submitted code is executed.

## Judging philosophy

1. The proposal describes what the team intended to build; source code is evidence of what was implemented.
2. Score the frozen `main` commit only.
3. Reward coherent implementation and demonstrated engineering, not ambition, complexity, or technology branding.
4. A named AI framework, vector database, agent framework, or model provider earns no points by itself.
5. Multi-agent orchestration is optional. A focused single-agent or model-assisted design can score highly.
6. Distinguish implemented, partially implemented, mocked/hardcoded, not found, and unable to verify.
7. Do not claim runtime verification when code was only inspected statically.
8. Avoid double-penalizing one weakness across criteria unless its consequences are distinct.
9. Use evidence paths and symbols for every material finding. Include line ranges when the inspection tool exposes them.
10. If evidence is incomplete, reflect that in confidence and limitations.

---

## 1. Technical Implementation — 25 points

| Dimension | Max | What to assess |
|---|---:|---|
| Functional completeness | 6 | Are the core proposal workflows implemented? Are important paths connected rather than represented by placeholders? |
| Architecture and design | 5 | Are responsibilities, modules, interfaces, and data flows coherent? Is the design appropriate to the problem? |
| Code quality | 5 | Is the code understandable, maintainable, consistent, and appropriately structured? |
| Reliability and security | 5 | Are errors, validation, secrets, authorization, input handling, and failure cases addressed in the code? |
| Integration and execution evidence | 4 | Are UI/API/data/model/provider/infrastructure integrations connected in source? Is there credible evidence of a runnable project setup? |

### Technical score anchors

| Score | Anchor |
|---:|---|
| 0–5 | Mostly scaffolding, placeholders, or a very incomplete implementation; core workflow is absent. |
| 6–11 | Basic implementation exists, but important workflows are incomplete, disconnected, or fragile. |
| 12–17 | Main functionality appears implemented from source; architecture is reasonable, with notable weaknesses. |
| 18–21 | Strong, coherent implementation; good architecture and maintainability; important failure cases are considered. |
| 22–25 | Exceptional completeness and engineering quality, with convincing evidence of robust, integrated implementation. |

### Technical scoring notes

- Do not award full functional completeness merely because UI screens or API routes exist. Trace the actual flow.
- For integration evidence, distinguish source-level wiring from verified execution. Runtime is not executed in this workflow.
- A README, screenshots, or demo description may support context but cannot substitute for implementation evidence.
- Security should be judged against the app's actual threat model. Do not penalize a prototype for lacking enterprise controls unless the proposal or data sensitivity makes them relevant.

---

## 2. AI Integration & Intelligence — 25 points

| Dimension | Max | What to assess |
|---|---:|---|
| AI centrality and relevance | 5 | Is AI essential or materially useful to the proposed product, rather than decorative? |
| Intelligence and AI architecture | 6 | Is there meaningful reasoning, orchestration, tool use, planning, structured generation, or stateful workflow design? |
| Context and data grounding | 5 | Does the AI receive relevant user/application/domain context? Is retrieval or grounding appropriate and traceable where needed? |
| Evaluation and guardrails | 4 | Are outputs validated? Are safety, permissions, uncertainty, evaluation, or human review addressed where appropriate? |
| Resilience and adaptability | 5 | Are failures, provider errors, retries, fallbacks, context limits, or changing inputs handled thoughtfully? |

### AI score anchors

| Score | Anchor |
|---:|---|
| 0–4 | AI is absent, superficial, hardcoded, or unrelated to the core value. |
| 5–10 | Basic model/API integration exists, but intelligence, grounding, or workflow depth is limited. |
| 11–16 | Meaningful AI integration with useful context and intelligent workflows; some design gaps remain. |
| 17–21 | Strong AI architecture, grounding, orchestration, validation, and thoughtful failure handling. |
| 22–25 | Exceptional, demonstrable intelligence with robust grounding, evaluation, safety, and resilience. |

### AI scoring notes

- A prompt string or model API wrapper alone is not a sophisticated AI system.
- Agent frameworks and multi-agent designs are not inherently better than a simpler architecture.
- Assess the quality and relevance of the actual AI workflow, not the number of AI-related dependencies.
- For retrieval systems, inspect whether retrieved context is actually connected to generation and whether sources can be traced.
- For tool-using systems, inspect tool schemas, authorization boundaries, error handling, and result handling.
- Do not assume model quality, latency, or accuracy without runtime evaluation. Mark these as unverified.

---

## Evidence quality

Each finding should include:
- `path`: repository-relative path.
- `line_start` and `line_end` where visible; otherwise `null`.
- `symbol`: function, class, component, route, or module name where possible.
- `observation`: what the code demonstrates.
- `status`: one of `implemented`, `partial`, `mocked_or_hardcoded`, `not_found`, `unable_to_verify`.

Avoid vague evidence such as “good architecture” without a concrete code reference.

## Confidence

- **high:** Proposal and key implementation paths are inspectable; major score claims have direct evidence.
- **medium:** Some relevant paths are missing, ambiguous, or only partially traceable.
- **low:** Repository is incomplete, unusually opaque, or evidence is too limited for a confident assessment.

## Three-line review summary

Every completed evaluation must contain exactly these three fields, rendered as exactly three Markdown bullets:

1. **Technical Review:** Summarize implementation quality, architecture, and completeness.
2. **AI Review:** Summarize AI relevance, intelligence, and integration quality.
3. **Final Verdict:** State the strongest aspect and most significant weakness.

Each line should be evidence-based, concise (ideally 20–30 words), and must not repeat numerical scores or make unsupported claims.

## Final score

`technical_total` is out of 25.  
`ai_total` is out of 25.  
`total_score = technical_total + ai_total`, out of 50.

Do not round fractional scores. Use integer scores per dimension. Totals must reconcile exactly.
