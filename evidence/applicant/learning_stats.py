"""OULAD enrollment-level observational statistics and sensitivity checks.

Pure calculations: importing this module does not read/write files or run analysis.
Input frames must satisfy the 12-column mart contract; the CLI validates inputs.
Associations and cluster intervals are descriptive, not causal effects.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


BOOTSTRAP_SEED = 101
OVERALL_DRAWS = 1000
SUBGROUP_DRAWS = 500
CLICK_THRESHOLDS = (10, 20, 50)
KEY = ("code_module", "code_presentation", "id_student")


def ratio(numerator: int, denominator: int) -> float | None:
    """Fraction in [0, 1], never a percent. Empty denominator => null."""
    return numerator / denominator if denominator else None


def compare(frame: pd.DataFrame, exposure: str, draws: int) -> dict:
    """Two-group return difference with learner-cluster percentile bootstrap.

    A draw samples K learner indices with replacement, where K is the number
    of unique learners in THIS comparison. All enrollments of each sampled
    learner contribute on every selection, including repeated selections.
    Each call starts an independent RNG at seed 101, matching the fixed spec.
    """
    control = frame[frame[exposure] == 0]
    exposed = frame[frame[exposure] == 1]
    groups = []
    for portion in (control, exposed):
        n = len(portion)
        returned = int(portion["w2_active"].sum())
        groups.append({"n": n, "returned": returned, "rate": ratio(returned, n)})

    result = {
        "control": groups[0],
        "exposed": groups[1],
        "difference": None,
        "ci": None,
        "clusters": int(frame["id_student"].nunique()),
        "bootstrap_draws": draws,
        "valid_draws": 0,
    }
    if groups[0]["n"] == 0 or groups[1]["n"] == 0:
        return result
    result["difference"] = groups[1]["rate"] - groups[0]["rate"]

    # Each side must include at least two distinct learners for inference.
    if (control["id_student"].nunique() < 2
            or exposed["id_student"].nunique() < 2):
        return result

    working = frame[["id_student", "w2_active", exposure]].copy()
    working["n0"] = (working[exposure] == 0).astype(int)
    working["n1"] = (working[exposure] == 1).astype(int)
    working["y0"] = working["n0"] * working["w2_active"]
    working["y1"] = working["n1"] * working["w2_active"]

    # groupby(sort=True) fixes bootstrap mapping independently of CSV row order.
    # Float64 matches the prior project's reference implementation.
    per_learner = (
        working.groupby("id_student", sort=True)[["n0", "n1", "y0", "y1"]]
        .sum()
        .to_numpy(dtype=float)
    )
    k = len(per_learner)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    differences = []
    for _ in range(draws):
        n0, n1, y0, y1 = per_learner[rng.integers(0, k, k)].sum(axis=0)
        if n0 > 0 and n1 > 0:
            differences.append(float(y1 / n1 - y0 / n0))

    result["valid_draws"] = len(differences)
    if differences:
        result["ci"] = [float(x) for x in np.quantile(
            differences, [0.025, 0.975], method="linear"
        )]
    return result


def summarize(frame: pd.DataFrame, draws: int = OVERALL_DRAWS) -> dict:
    """Overall/cohort/time summary including D0 groups and both comparisons."""
    active = frame.loc[frame["w1_days"] >= 1].copy()
    active["repeat"] = (active["w1_days"] >= 2).astype(int)
    eligible = len(frame)
    active_count = len(active)
    returned = int(active["w2_active"].sum())

    days = []
    for d in range(8):
        section = frame.loc[frame["w1_days"] == d]
        n = len(section)
        y = int(section["w2_active"].sum())
        days.append({"days": d, "n": n, "returned": y, "rate": ratio(y, n)})
    return {
        "eligible": eligible,
        "w1_active": active_count,
        "w2_returned": returned,
        "return_rate": ratio(returned, active_count),
        "unique_learners": int(frame["id_student"].nunique()),
        "days": days,
        "repeat_comparison": compare(active, "repeat", draws),
        "content_comparison": compare(active, "first_content", draws),
    }


def temporal_summaries(mart: pd.DataFrame, prior_2013_learners: set[int]) -> list[dict]:
    """Use *all* historical registrations, including ineligible 2013 ones."""
    year = mart["code_presentation"]
    discovery = mart.loc[year.str.startswith("2013")]
    holdout = mart.loc[
        year.str.startswith("2014")
        & ~mart["id_student"].isin(prior_2013_learners)
    ]
    # This is a guard against erroneously substituting mart-only history.
    if set(discovery["id_student"]) & set(holdout["id_student"]):
        raise ValueError("탐색과 재확인 학습자 집합이 겹칩니다")
    return [
        {"id": "discovery", "label": "2013 탐색", **summarize(discovery, OVERALL_DRAWS)},
        {"id": "holdout", "label": "2014 신규 학습자 재확인", **summarize(holdout, OVERALL_DRAWS)},
    ]


def first_day_summaries(mart: pd.DataFrame) -> list[dict]:
    active = mart.loc[mart["w1_days"] >= 1]
    entries = []
    for first_day in sorted(int(d) for d in active["first_day"].dropna().unique()):
        section = active.loc[active["first_day"] == first_day].copy()
        section["repeat"] = (section["w1_days"] >= 2).astype(int)
        entries.append({"first_day": first_day, "comparison": compare(
            section, "repeat", SUBGROUP_DRAWS
        )})
    return entries


def click_sensitivities(mart: pd.DataFrame) -> list[dict]:
    active = mart.loc[mart["w1_days"] >= 1]
    result = []
    for threshold in CLICK_THRESHOLDS:
        raw = active["first_clicks_raw"] >= threshold
        exact = active["first_clicks_exact"] >= threshold
        maximum = active["first_clicks_max"] >= threshold
        result.append({
            "threshold": threshold,
            "raw_qualified": int(raw.sum()),
            "exact_qualified": int(exact.sum()),
            "max_qualified": int(maximum.sum()),
            "raw_vs_exact_changed": int((raw != exact).sum()),
            "raw_vs_max_changed": int((raw != maximum).sum()),
        })
    return result


def transitions(mart: pd.DataFrame) -> list[dict]:
    w1 = mart["w1_days"] >= 1
    result = []
    for first in (0, 1):
        for second in (0, 1):
            section = mart.loc[(w1 == bool(first)) & (mart["w2_active"] == second)]
            result.append({
                "w1": first, "w2": second, "n": len(section),
                "later_active": int(section["later_active"].sum()),
            })
    return result


def strict_sensitivity(mart: pd.DataFrame, strict: pd.DataFrame) -> dict:
    """The runner ensures one-to-one matching enrollment keys before this call."""
    key_cols = list(KEY)
    a = mart.set_index(key_cols).sort_index()
    b = strict.set_index(key_cols).reindex(a.index)
    active = b["w1_days"] >= 1
    return {
        "w1_active": int(active.sum()),
        "w2_returned": int(b.loc[active, "w2_active"].sum()),
        "changed_w1_enrollments": int((a["w1_days"] != b["w1_days"]).sum()),
        "changed_w2_enrollments": int((a["w2_active"] != b["w2_active"]).sum()),
    }


def calculate_statistics(
    mart: pd.DataFrame, strict: pd.DataFrame, prior_2013_learners: set[int],
) -> dict:
    """Return statistics fields; caller handles validation, hashes, and JSON IO."""
    cohorts = []
    for (module, term), section in mart.groupby(
        ["code_module", "code_presentation"], sort=True
    ):
        cohorts.append({
            "module": module, "term": term,
            **summarize(section, SUBGROUP_DRAWS),
        })
    return {
        "overall": summarize(mart, OVERALL_DRAWS),
        "cohorts": cohorts,
        "temporal": temporal_summaries(mart, prior_2013_learners),
        "first_day_strata": first_day_summaries(mart),
        "click_sensitivity": click_sensitivities(mart),
        "transition": transitions(mart),
        "strict_sensitivity": strict_sensitivity(mart, strict),
    }
