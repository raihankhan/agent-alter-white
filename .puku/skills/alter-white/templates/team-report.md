# {{repository.full_name}} — Alter White Evaluation

**Repository:** {{repository.url}}  
**Branch:** `{{repository.branch}}`  
**Commit:** `{{repository.commit_sha}}`  
**Evaluated:** {{evaluation.evaluated_at}}  
**Confidence:** {{confidence}}

## Scores

| Criteria | Score |
|---|---:|
| Technical Implementation | {{scores.technical_total}}/25 |
| AI Integration & Intelligence | {{scores.ai_total}}/25 |
| **Total** | **{{scores.total_score}}/50** |

## Three-Line Review

- **Technical Review:** {{review_summary.technical_review}}
- **AI Review:** {{review_summary.ai_review}}
- **Final Verdict:** {{review_summary.final_verdict}}

## Key Strengths

{{strengths}}

## Areas for Improvement

{{improvement_areas}}

## Detailed Scoring

### Technical Implementation

| Dimension | Score |
|---|---:|
| Functional completeness | {{scores.technical.functional_completeness.score}}/6 |
| Architecture and design | {{scores.technical.architecture_and_design.score}}/5 |
| Code quality | {{scores.technical.code_quality.score}}/5 |
| Reliability and security | {{scores.technical.reliability_and_security.score}}/5 |
| Integration and execution evidence | {{scores.technical.integration_and_execution_evidence.score}}/4 |

### AI Integration & Intelligence

| Dimension | Score |
|---|---:|
| AI centrality and relevance | {{scores.ai.ai_centrality_and_relevance.score}}/5 |
| Intelligence and AI architecture | {{scores.ai.intelligence_and_ai_architecture.score}}/6 |
| Context and data grounding | {{scores.ai.context_and_data_grounding.score}}/5 |
| Evaluation and guardrails | {{scores.ai.evaluation_and_guardrails.score}}/4 |
| Resilience and adaptability | {{scores.ai.resilience_and_adaptability.score}}/5 |

## Verification

- **Mode:** Static source inspection only
- **Runtime execution:** Not performed
- **Proposal:** {{verification.project_proposal_status}}{{#if verification.proposal_source}} (`{{verification.proposal_source}}`){{/if}}

### Limitations

{{verification.limitations}}

## Evaluation Metadata

- Evaluator: {{evaluation.evaluator}}
- Model: {{evaluation.model}}
- Rubric version: `{{rubric_version}}`
- Schema version: `{{schema_version}}`
