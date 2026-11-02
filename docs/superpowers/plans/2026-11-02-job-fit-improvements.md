# Job-fit evidence improvements implementation plan

> **For agentic workers:** Execute inline with superpowers:executing-plans; preserve human evidence and distinguish generated fixtures.

**Goal:** Address the four reviewed weaknesses without inventing applicant work or company results.

**Architecture:** Extend existing Python/SQL and Markdown. A versioned input policy changes only new operations studies. A separate synthetic subscription ledger demonstrates renewal denominators and payer/learner joins. Product alternatives remain conditional on evidence.

**Tech Stack:** Existing Python, DuckDB, pytest, Markdown; no added dependencies or UI redesign.

**Spec:** User's 2026-11-02 request to address assessment items 1–4 and the four-item scope announced in conversation. The user previously opted out of repeated confirmations; implementation choices below are Codex choices.

## Global constraints
- Do not modify historical human measurements or claim a new human comparison occurred.
- Applicant SQL is pending until actually submitted; do not prewrite their answer.
- OULAD/EdNet numbers remain unchanged; synthetic renewal results never become business results.
- New measurement policy requires a new study and cannot resume old fingerprints.
- No company data access, payments, messages to outsiders, or new paid services.

## Approaches and decisions
Retain existing analysis and add decision evidence rather than a churn model/new dashboard. Prefer a small hand-checkable synthetic billing contract over unsupported renewal claims from EdNet. Add explicit retry-input-v2 policy to the existing recorder rather than duplicate the pipeline; historical v1 remains available at its pinned commit. This reduces maintenance but requires audit tests for corrected inputs.

## Review focus
1. Corrected values must retain failed entries and their elapsed time, including interruption.
2. Unknown policy / edited protocol must not silently alter studies.
3. Renewal must not count unmatured cycles, late receipts, or refunded charges as retained.
4. Group membership joins must not multiply payer transactions.
5. Generated results and pending applicant work must remain labeled through README/report/docs.

### Task 1 — applicant evidence and product alternatives
- [x] Document one independent SQL brief with schema, submission/provenance rules, no answer.
- [x] Re-read official service pages; document alternative mechanisms, disconfirming evidence, decision gates and effort uncertainty in docs/product-decision.md.
- [x] Update experiment-plan to mark the chosen action conditional rather than empirically identified.

### Task 2 — subscription bridge
- [x] Write tests with hand-checkable generated contracts for renewal maturity, payer mapping, duplicate payments, refunds and temporal cutoff; observe RED.
- [x] Implement src/journey/subscription_bridge.py, sql/subscription_bridge.sql, scripts/check_subscription.py and a clearly labeled deterministic fixture.
- [x] Generate reports/subscription-bridge.json twice, compare digests, document exact metrics and remaining company-data requirements.

### Task 3 — operations policy v2
- [x] Write recorder tests proving typo correction stays in the same attempt without pipeline restart; preserve all input errors, command errors, pauses and aborts. Observe RED.
- [x] Add explicit input policy to init/protocol/record/audit. Default remains legacy-v1 for compatibility; v2 uses a new --study.
- [x] Audit corrected inputs against events; reject tampering. Keep fatal calculation/hash failures fatal.
- [x] Run original and new tests; developer-only full OULAD A/B confirms identical stages/results. No new human timing claim.

### Task 4 — closeout
- [x] Update README, evidence map, learning log and scope-specific completion document.
- [x] Run full pytest, existing build/verify, repeated new report generation, review diff and obtain fresh code review.
- [x] Publish authorized repository updates and verify CI. Record unfinished human submission/new measurements explicitly.

## Progress / rulings
- Existing isolated worktree validation/full-review at 06baabd, public base 3b9e995; identical trees. Clean before work.
- Independent SQL brief sent asynchronously; no applicant response yet.
- Human repetition will not be launched automatically: v2 preparation and developer validation are executable now; measured improvement requires new actual participation.

- Task 1: documents complete; independent applicant submission remains pending, not a completed skill assessment.
- Task 2: synthetic subscription contract/tests/report complete. Repeat report SHA256 8cab630e444e6677fe019dda8f2db0732a222b4baefdb01aa20ace6c953d6e1e.
- Task 3: v2 implemented. Final real OULAD automated A/B: 12 stages, 84 fields, identical hashes, audit PASS; 0 human measured rounds.
- Final fresh review found interrupted-record audit and mid-study policy-change problems; four RED regression cases became GREEN after fixes. Full suite 156 passed.
- Task 4: local full suite/build/verify and 18 deployed asset byte comparisons passed; code published as 966fbcabb511a07b9bdededd859b4917e394cfdd. Quality CI41416308854 and full reproduction CI41416308943 succeeded; Render dep-dbk4utrm8hqs738eb7l0 live. No product UI assets changed.
