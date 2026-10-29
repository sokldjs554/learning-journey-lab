# Evidence Extension Implementation Plan

> Execute independent research/experiment components in staging with parallel-agents; integrate and fresh-review entire change.

Goal: reduce the evidence gap without attributing generated or Codex work to actual service users or the applicant.
Spec: user request 2026-10-29, pasted full request in session. Explicitly authorizes investigate/select/implement/verify/deploy; applicant actions require actual replies.
Architecture: preserve OULAD report SHA256 675dfa6fa3126da0ba74b5a4b4c4222afff4d950297703f3314788f9135a30db. Separate supplementary public-data report, executable experiment-engineering checks, and tiny human operations task. Existing vanilla static UI consumes separate provenance-tagged artifacts. No backend or invented real outcomes.
Tech: existing Python/DuckDB/pandas/pytest, static HTML/JS/CSS, Playwright/axe.

## Choices and constraints
- Retain OULAD; supplementary EdNet preferred if official files obtainable and suitable. Replacing original violates preservation; generated substitutes cannot establish external validity.
- Actual public-data observational analysis is experiment route B; engineering test fixtures are separate synthetic work, never A/B treatment evidence.
- Human manual benchmark needs actual participant timing. Prepare same-input/same-output protocol and leave unmeasured values null until reply.
- Applicant will write a triple-repeat regression test on practice/repeat-rule; do not add it on their behalf.
- Git main clean c70ecd4, worktree feat/evidence-extension. Existing Render workspace/service authorized.

## Review focus
- Right censoring, per-user shifted clocks, selection sampling and complete-history coverage.
- Mislabeling pay/pass, refunds, first observation, no price/renewal fields.
- All-assigned ITT denominator, exactly D7/D14, watermark, cross-variant duplicates and missing telemetry.
- Honest user timing vs machine timing; matching task outputs and order/learning effects.
- Different source report failure cannot silently contaminate original OULAD UI; mobile/keyboard/errors and report validation.

## Tasks
- [ ] Baseline job/readme/code/CI/deployed flows, document gaps.
- [ ] Research >=4 real datasets; source metadata + observed download; choose additional actual analysis, tests + independent crosscheck + reproducibility, aggregate only.
- [ ] Implement/test experiment readiness and recruitment scenarios; official service evidence, no claimed human experiment.
- [ ] Prepare tiny manual/automatic review task, timing export + comparable outputs + pending human results, user-authored SQL regression instructions.
- [ ] Integrate additional evidence into existing tool and clarify denominator/%p/directions using actual guided-learning confusion as session evidence, not naive-user study.
- [ ] Browser local/deployed PC/mobile/error/keyboard/empty; fresh review and fixes; README/evidence/screenshots; CI and final deployment.
- [ ] On applicant response verify branch/run/measurements; preserve pending if absent.
