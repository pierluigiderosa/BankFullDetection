"""Tests of bankfull_core.level (bankfull level from multiple CV runs)."""

import csv
import dataclasses

import numpy as np
import pytest
from conftest import DATA_DIR

from bankfull_core import (
    STATUS_NO_MAXIMA,
    STATUS_OK,
    BankfullLevel,
    BankfullOptions,
    compute_bankfull_level,
    hydraulic_curve,
    smooth_curve,
)

REPO = DATA_DIR.parents[1]
COMPARISON_CSV = REPO / "docs" / "confronto-opzioni.csv"
EXPERT_CSV = DATA_DIR / "expert" / "expert_bankfull.csv"

# docs/confronto-opzioni.csv stores levels with 3 decimals.
CSV_TOL = 5e-4 + 1e-9

ARNO_7 = ("arno.csv", 7)
PARABOLA = ("synthetic.csv", 4)


def _expert_keys():
    with open(EXPERT_CSV, newline="", encoding="utf-8") as f:
        return [(r["source_file"], int(r["section_id"])) for r in csv.DictReader(f)
                if r["z_expert_low"].strip() or r["z_expert_high"].strip()]


def _reference_rows():
    """{key: row} of the comparison CSV for thalweg / min_cv / highest (threshold 1.0)."""
    with open(COMPARISON_CSV, newline="", encoding="utf-8") as f:
        return {(r["source_file"], int(r["section_id"])): r for r in csv.DictReader(f)
                if (r["multichannel"], r["selection"], r["criterion"],
                    float(r["min_hyd_depth"])) == ("thalweg", "min_cv", "highest", 1.0)}


EXPERT_KEYS = _expert_keys()
REFERENCE = _reference_rows()


@pytest.fixture(scope="module")
def recommended_levels(all_sections):
    """{key: BankfullLevel} with the recommended options, for the expert sections."""
    opts = BankfullOptions.recommended()
    return {k: compute_bankfull_level(all_sections[k], opts) for k in EXPERT_KEYS}


def test_recommended_options():
    opts = BankfullOptions.recommended()
    assert (opts.multichannel, opts.selection, opts.criterion, opts.n_runs) == (
        "thalweg", "min_cv", "highest", 11)
    default = BankfullOptions()
    assert dataclasses.replace(opts, multichannel="original", criterion="first",
                               n_runs=1) == default
    assert (default.criterion, default.n_runs) == ("first", 1)


@pytest.mark.parametrize("key", [("arno.csv", 1), ARNO_7, ("synthetic.csv", 2)], ids=str)
@pytest.mark.parametrize(
    "opts",
    [BankfullOptions(), BankfullOptions(multichannel="thalweg", criterion="highest", seed=3)],
    ids=["default", "thalweg-highest-seed3"],
)
def test_single_run_matches_smooth_curve(all_sections, key, opts):
    pts = all_sections[key]
    curve = hydraulic_curve(pts, opts)
    ref = smooth_curve(curve.levels, curve.hyd_depth, opts)
    res = compute_bankfull_level(pts, opts)
    assert isinstance(res, BankfullLevel)
    assert res.status == ref.status == STATUS_OK
    assert res.level == res.level_min == res.level_max == ref.bankfull_level
    assert res.run_levels == (ref.bankfull_level,)
    assert res.n_runs_ok == 1
    assert res.options is opts


def test_runs_use_consecutive_seeds(all_sections):
    pts = all_sections[ARNO_7]
    opts = BankfullOptions.recommended()
    res = compute_bankfull_level(pts, dataclasses.replace(opts, n_runs=4, seed=5))
    singles = [compute_bankfull_level(pts, dataclasses.replace(opts, n_runs=1, seed=s))
               for s in range(5, 9)]
    assert res.run_levels == tuple(s.level for s in singles)


def test_deterministic_with_seed(all_sections):
    pts = all_sections[ARNO_7]
    opts = dataclasses.replace(BankfullOptions.recommended(), n_runs=5)
    assert compute_bankfull_level(pts, opts) == compute_bankfull_level(pts, opts)


def test_different_seeds_give_different_runs(recommended_levels):
    """On Arno 7 the level changes with the CV folds (seed)."""
    res = recommended_levels[ARNO_7]
    assert res.n_runs_ok == 11
    assert len(set(res.run_levels)) > 1
    assert res.level_max - res.level_min > 0.1
    assert res.level_min <= res.level <= res.level_max
    assert res.level == float(np.median(res.run_levels))


def test_no_bankfull_reports_first_run_status(all_sections):
    res = compute_bankfull_level(all_sections[PARABOLA], BankfullOptions(n_runs=3))
    assert res.status == STATUS_NO_MAXIMA
    assert res.level is None and res.level_min is None and res.level_max is None
    assert res.n_runs_ok == 0
    assert res.run_levels == (None, None, None)


def test_result_is_frozen(all_sections):
    res = compute_bankfull_level(all_sections[("arno.csv", 1)])
    with pytest.raises(dataclasses.FrozenInstanceError):
        res.level = 0.0


def test_reference_rows_present():
    assert len(EXPERT_KEYS) == 8
    assert sorted(REFERENCE) == sorted(EXPERT_KEYS)


@pytest.mark.parametrize("key", EXPERT_KEYS, ids=str)
def test_recommended_reproduces_comparison(recommended_levels, key):
    """Median, minimum and maximum over seeds 0-10 as in docs/confronto-opzioni.csv
    (thalweg / min_cv / highest), within the 3-decimal rounding of the CSV."""
    res = recommended_levels[key]
    ref = REFERENCE[key]
    assert res.status == STATUS_OK
    assert res.n_runs_ok == int(ref["n_seeds_ok"]) == 11
    assert abs(res.level - float(ref["level_median"])) <= CSV_TOL
    assert abs(res.level_min - float(ref["level_min"])) <= CSV_TOL
    assert abs(res.level_max - float(ref["level_max"])) <= CSV_TOL
