# Accessibility Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Check every public page and complete interaction state against applicable WCAG 2.2 A/AA requirements, fix reproducible defects, and distinguish browser evidence from actual assistive-technology observations.

**Architecture:** Retain static HTML/JS and analysis payloads. Add small focus/semantic fixes only where reproduced. Browser checks cover routes, variants, errors, keyboard, spacing and reflow; a criterion matrix records applicability and remaining actual-device evidence.

**Tech Stack:** Existing JavaScript/HTML/CSS, Playwright 1.56, axe-core 4.11.0.

**Spec:** User requested remaining full accessibility verification. Existing documented boundaries in docs/device-check-results.md remain valid; no certification claim or invented human results.

## Global Constraints

- Do not change analysis numbers, timing scoring, measured records or source data.
- Cover index review/analysis/runs/plan/lab, external.html and operations-practice.html; include loading, bad data, empty, invalid input, pause and export.
- Report automated tests as automated; actual VoiceOver and device results require user responses.
- Existing user instruction to continue authorizes fixes and deployment; no repeat approval gate.

## Review Focus

- Retry removes the focused button: restore context after both success and failure.
- Repeated field labels lack row identity: retain visible label in accessible name.
- Invalid input only has aggregate counts: identify affected field and rule, keep immutable measurements.
- Narrow/expanded text hides actions: evaluate reflow, spacing, focus visibility, horizontal table navigation.
- Successful loading is not a human reading test: preserve pending actual-assistive checks explicitly.

## Tasks

- [x] Reproduce focus loss and missing field errors with behavior assertions before edits.
- [x] Fix main/external/experiment retry focus; independent practice fixes in its three files.
- [x] Exercise all route/state templates, keyboard tasks, text spacing, 320px reflow, contrast review and axe incomplete items.
- [x] Build 55-criterion A/AA applicability/evidence matrix, with manual/unverified statuses rather than universal pass.
- [ ] Run existing browser/product tests, publish, verify deployed bytes and flows, then request the bounded remaining real VoiceOver/zoom tasks.
