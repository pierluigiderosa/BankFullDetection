"""Tests of bankfull_core.smoothing against the golden data of the original R method.

Level 0: the spline fit and the CV table reproduce R's smooth.spline / cv.smooth.spline.
Level 1: maxima found from the grid sign changes of f' vs R's Newton-Raphson maxima.
Level 2: full chain (section -> A/W curve -> smoothing -> bankfull) with R's CV folds.
Level 3: synthetic sections, new behaviour.
Tables are printed by the tests selected with ``-k table`` (run with ``-s``).
"""

import csv
import time

import numpy as np
import pytest
from conftest import (
    DATA_DIR,
    read_golden_bankfull,
    read_golden_cv,
    read_golden_fitted,
    read_golden_fold_labels,
    read_golden_maxima,
    read_golden_summary,
)
from numpy.testing import assert_allclose, assert_array_equal

from bankfull_core import (
    STATUS_NO_MAXIMA,
    STATUS_OK,
    BankfullOptions,
    fit_smoothing_spline,
    folds_from_labels,
    hydraulic_curve,
    make_folds,
    smooth_curve,
)
from bankfull_core.smoothing import (
    _SplineSystem,
    cross_validate,
    find_maxima,
    select_spar,
    spar_grid,
)

FITTED = read_golden_fitted()
FOLDS = {k: folds_from_labels(v) for k, v in read_golden_fold_labels().items()}
R_CV = read_golden_cv()
R_MAXIMA = read_golden_maxima()
SUMMARY = read_golden_summary()
BANKFULL = read_golden_bankfull()
KEYS = sorted(FITTED)
MIN_HYD_DEPTHS = (1.0, 0.2)

TRAPEZOID = ("synthetic.csv", 1)
BENCH = ("synthetic.csv", 2)
TWO_DEPRESSIONS = ("synthetic.csv", 3)
PARABOLA = ("synthetic.csv", 4)

# Tolerance on levels [m] for the comparison with the golden data.
Z_TOL = 0.05

# Maxima found here and not by R: the candidate interval exists, but R's Newton-Raphson
# failed (converged to another root, to a minimum, or did not converge). Approximate levels.
EXTRA_MAXIMA = {
    ("arno.csv", 2): [13.315],
    ("arno.csv", 8): [17.005],
    BENCH: [1.438],
    TRAPEZOID: [2.972],
}

# Sections whose golden bankfull is affected by a maximum lost by Newton-Raphson.
NEWTON_LOST_BANKFULL = (("arno.csv", 2), BENCH)

# Intended differences (tested in level 3): no golden bankfull (trapezoid) or fallback
# to the last point (parabola).
LEVEL2_EXCLUDED = (TRAPEZOID, PARABOLA)
LEVEL2_KEYS = [k for k in KEYS if k not in LEVEL2_EXCLUDED + NEWTON_LOST_BANKFULL]


def _r_spar(key):
    return float(SUMMARY[key]["spar1se"])


def _r_maxima_dedup(key):
    """R maxima sorted by level, duplicates (|dz| <= 1e-6) removed."""
    m = R_MAXIMA.get(key, np.empty((0, 2)))
    m = m[np.argsort(m[:, 0], kind="stable")]
    keep = [i for i in range(len(m)) if i == 0 or m[i, 0] - m[i - 1, 0] > 1e-6]
    return m[keep]


def _match(levels, ref):
    """For each level, distance to the nearest ref level (inf if ref is empty)."""
    ref = np.asarray(ref, dtype=float)
    if ref.size == 0:
        return np.full(len(levels), np.inf)
    return np.array([np.min(np.abs(ref - z)) for z in levels])


def _golden_z(key, mv):
    text = BANKFULL[(key[0], key[1], mv)]["bankfull_z"]
    return float(text) if text else None


def _read_expert():
    with open(DATA_DIR / "expert" / "expert_bankfull.csv", newline="",
              encoding="utf-8") as f:
        return {(r["source_file"], int(r["section_id"])): r["z_expert"]
                for r in csv.DictReader(f)}


@pytest.fixture(scope="module")
def curves(all_sections):
    """{key: HydraulicCurve} computed from the test sections."""
    return {k: hydraulic_curve(all_sections[k]) for k in KEYS}


@pytest.fixture(scope="module")
def level2(curves):
    """{(key, mv): (SmoothingResult, seconds)} with R's folds and min_cv."""
    out = {}
    for key in KEYS:
        c = curves[key]
        for mv in MIN_HYD_DEPTHS:
            t0 = time.perf_counter()
            res = smooth_curve(c.levels, c.hyd_depth, BankfullOptions(min_hyd_depth=mv),
                               folds=FOLDS[key])
            out[(key, mv)] = (res, time.perf_counter() - t0)
    return out


# --------------------------------------------------------------------------- level 0


@pytest.mark.parametrize("key", KEYS, ids=str)
def test_level0_fit_matches_r(key):
    x, y, yhat = FITTED[key]
    spline = fit_smoothing_spline(x, y, _r_spar(key))
    assert np.max(np.abs(spline(x) - yhat)) <= 1e-6


@pytest.mark.parametrize(
    ("n", "ratio", "lam0", "lam1"),
    [
        (100, 1.1970405348608106e-06, 4.6759395893000413e-09, 0.078449248492638082),
        (90, 1.2517182331491644e-06, 4.8895243482389234e-09, 0.082032606127663638),
    ],
)
def test_level0_ratio_and_lambda(n, ratio, lam0, lam1):
    # Values printed by R 4.6.2: smooth.spline(seq(0, 1, length = n), y, spar)$ratio and
    # $lambda; they depend only on the (equally spaced) x, not on y or on the x range.
    for scale in (1.0, 11.0):
        x = np.linspace(0.0, scale, n)
        system = _SplineSystem(x, np.sin(6 * x / scale))
        assert_allclose(system.ratio, ratio, rtol=1e-9)
        assert_allclose(system.lam(0.0), lam0, rtol=1e-9)
        assert_allclose(system.lam(1.0), lam1, rtol=1e-9)


@pytest.mark.parametrize("key", KEYS, ids=str)
def test_level0_cv_table_matches_r(key):
    x, y, _ = FITTED[key]
    table = cross_validate(x, y, spar_grid(), FOLDS[key])
    ref = R_CV[key]
    assert_allclose(table.spar, ref["spar"], rtol=0, atol=1e-12)
    assert_allclose(table.cv_error, ref["cv_error"], rtol=1e-6)
    assert_allclose(table.se, ref["se"], rtol=1e-6)
    idx, _ = select_spar(table, "min_cv")
    assert table.spar[idx] == pytest.approx(float(SUMMARY[key]["sparmin"]), abs=1e-12)


def test_level0_table():
    print("\nLevel 0 - fit at R's spar vs r_fitted.yhat")
    print(f"{'section':<20}{'spar':>10}{'max|dy|':>12}")
    worst = 0.0
    for key in KEYS:
        x, y, yhat = FITTED[key]
        err = float(np.max(np.abs(fit_smoothing_spline(x, y, _r_spar(key))(x) - yhat)))
        worst = max(worst, err)
        print(f"{key[0] + ' ' + str(key[1]):<20}{_r_spar(key):>10.4f}{err:>12.2e}")
    print(f"max over sections: {worst:.2e}")


# --------------------------------------------------------------------------- level 1


@pytest.mark.parametrize("key", KEYS, ids=str)
def test_level1_maxima_vs_r(key):
    x, y, _ = FITTED[key]
    spline = fit_smoothing_spline(x, y, _r_spar(key))
    found = find_maxima(spline, x)
    r_max = _r_maxima_dedup(key)
    # Every R maximum is found.
    assert np.all(_match(r_max[:, 0], found[:, 0]) <= Z_TOL)
    # Extra maxima are exactly the expected ones (Newton-Raphson failures in R).
    extra = found[_match(found[:, 0], r_max[:, 0]) > Z_TOL, 0]
    expected = EXTRA_MAXIMA.get(key, [])
    assert len(extra) == len(expected)
    assert np.all(_match(extra, expected) <= Z_TOL)


def _prominence(spline, x, level):
    """Value at the maximum minus the higher adjacent minimum (curve end if none)."""
    st = spline.stationary_points()
    mins = st[spline(st, deriv=2) > 0]
    left = mins[mins < level]
    right = mins[mins > level]
    lv = spline(left[-1]) if left.size else spline(x[0])
    rv = spline(right[0]) if right.size else spline(x[-1])
    return float(spline(level) - max(lv, rv))


@pytest.mark.parametrize("key", [("arno.csv", 3), ("arno.csv", 9)], ids=str)
def test_level1_grid_filters_wiggles(key):
    """All exact roots of f' give one more maximum, paired with a minimum in the same
    grid interval and with negligible prominence: the grid search skips it."""
    x, y, _ = FITTED[key]
    spline = fit_smoothing_spline(x, y, _r_spar(key))
    st = spline.stationary_points()
    all_max = st[spline(st, deriv=2) < 0]
    found = find_maxima(spline, x)[:, 0]
    skipped = all_max[_match(all_max, found) > 1e-6]
    assert len(skipped) == 1
    z = skipped[0]
    nxt = st[st > z][0]
    assert np.searchsorted(x, z) == np.searchsorted(x, nxt)
    assert _prominence(spline, x, z) < 0.01


def test_level1_table():
    print("\nLevel 1 - maxima at R's spar: grid sign changes + brentq vs R Newton")
    print(f"{'section':<20}{'n R':>5}{'n new':>7}{'max|dz| matched':>17}  extra (z, A/W)")
    for key in KEYS:
        x, y, _ = FITTED[key]
        found = find_maxima(fit_smoothing_spline(x, y, _r_spar(key)), x)
        r_max = _r_maxima_dedup(key)
        d = _match(r_max[:, 0], found[:, 0])
        extra = found[_match(found[:, 0], r_max[:, 0]) > Z_TOL]
        dz = f"{np.max(d):.1e}" if d.size else "-"
        ex = ", ".join(f"({a:.3f}, {b:.3f})" for a, b in extra) or "-"
        print(f"{key[0] + ' ' + str(key[1]):<20}{len(r_max):>5}{len(found):>7}{dz:>17}  {ex}")


# --------------------------------------------------------------------------- level 2


@pytest.mark.parametrize("mv", MIN_HYD_DEPTHS)
@pytest.mark.parametrize("key", LEVEL2_KEYS, ids=str)
def test_level2_bankfull_vs_golden(level2, key, mv):
    res, _ = level2[(key, mv)]
    assert res.status == STATUS_OK
    assert abs(res.bankfull_level - _golden_z(key, mv)) <= Z_TOL


@pytest.mark.parametrize("key", KEYS, ids=str)
def test_level2_border_iff_r_spar_zero(level2, key):
    res, _ = level2[(key, 1.0)]
    assert res.spar_on_border == (_r_spar(key) == 0.0)


@pytest.mark.parametrize("mv", MIN_HYD_DEPTHS)
@pytest.mark.parametrize("key", NEWTON_LOST_BANKFULL, ids=str)
def test_level2_newton_lost_maximum(level2, key, mv):
    """The golden is the first maximum >= threshold among those R also found; the new
    bankfull is the maximum R lost."""
    res, _ = level2[(key, mv)]
    r_max = _r_maxima_dedup(key)
    shared = res.maxima[_match(res.maxima[:, 0], r_max[:, 0]) <= Z_TOL]
    first = shared[shared[:, 1] >= mv][0]
    assert abs(first[0] - _golden_z(key, mv)) <= Z_TOL
    assert abs(res.bankfull_level - EXTRA_MAXIMA[key][0]) <= Z_TOL


def test_level2_table(level2):
    expert = _read_expert()
    print("\nLevel 2 - full chain with R folds, min_cv")
    print(f"{'section':<20}{'mv':>5}{'spar':>8}{'border':>8}{'z new':>10}{'z golden':>10}"
          f"{'dz':>9}{'z expert':>10}{'time s':>8}  note")
    times = []
    for key in KEYS:
        for mv in MIN_HYD_DEPTHS:
            res, dt = level2[(key, mv)]
            times.append(dt)
            g = _golden_z(key, mv)
            z = res.bankfull_level
            dz = f"{z - g:+.3f}" if (z is not None and g is not None) else "-"
            zs = f"{z:.3f}" if z is not None else res.status
            gs = f"{g:.3f}" if g is not None else BANKFULL[(key[0], key[1], mv)]["error"]
            note = ("excluded" if key in LEVEL2_EXCLUDED
                    else "Newton lost max" if key in NEWTON_LOST_BANKFULL else "")
            print(f"{key[0] + ' ' + str(key[1]):<20}{mv:>5.1f}{res.spar:>8.4f}"
                  f"{res.spar_on_border!s:>8}{zs:>10}{gs:>10}{dz:>9}"
                  f"{expert.get(key, '') or '-':>10}{dt:>8.3f}  {note}")
    print(f"mean time per section run: {np.mean(times):.3f} s")


# --------------------------------------------------------------------------- level 3


@pytest.mark.parametrize("mv", MIN_HYD_DEPTHS)
def test_level3_trapezoid(curves, mv):
    c = curves[TRAPEZOID]
    res = smooth_curve(c.levels, c.hyd_depth, BankfullOptions(min_hyd_depth=mv))
    assert res.status == STATUS_OK
    assert abs(res.bankfull_level - 3.0) <= 0.1


def test_level3_parabola(curves):
    c = curves[PARABOLA]
    res = smooth_curve(c.levels, c.hyd_depth, BankfullOptions(no_max="explicit"))
    assert res.status == STATUS_NO_MAXIMA
    assert res.bankfull_level is None and not res.fallback
    res = smooth_curve(c.levels, c.hyd_depth, BankfullOptions(no_max="original"))
    assert res.status == STATUS_OK and res.fallback
    assert res.bankfull_level == pytest.approx(3.9, abs=1e-9)


@pytest.mark.parametrize("mv", MIN_HYD_DEPTHS)
def test_level3_two_depressions(curves, mv):
    c = curves[TWO_DEPRESSIONS]
    res = smooth_curve(c.levels, c.hyd_depth, BankfullOptions(min_hyd_depth=mv))
    assert abs(res.bankfull_level - _golden_z(TWO_DEPRESSIONS, mv)) <= Z_TOL


@pytest.mark.parametrize("mv", MIN_HYD_DEPTHS)
def test_level3_inner_bench(curves, mv):
    """The bank-top maximum of the golden is found, but the bankfull is the bench
    maximum (A/W ~1.19 >= both thresholds): known limit of the method."""
    c = curves[BENCH]
    res = smooth_curve(c.levels, c.hyd_depth, BankfullOptions(min_hyd_depth=mv))
    assert np.min(np.abs(res.maxima[:, 0] - _golden_z(BENCH, mv))) <= Z_TOL
    assert abs(res.bankfull_level - EXTRA_MAXIMA[BENCH][0]) <= Z_TOL


# ---------------------------------------------------------------- grid lower limit


@pytest.mark.parametrize("key", [("arno.csv", 2), ("arno.csv", 9)], ids=str)
def test_extended_spar_grid_is_stable(level2, curves, key):
    """Extending the spar grid below 0 does not change the maxima.

    On Arno 2 and 9 R's CV picks spar = 0, the border of its grid. The initial hypothesis
    was that spar = 0 acts as a brake against spurious maxima on these almost noise-free
    curves, so that a lower limit would give more maxima or a lower bankfull. It was
    disproved: with spar_min = -0.5 the CV picks an interior spar just below 0, no maximum
    is added and the maxima that can become the bankfull (A/W >= the lowest threshold,
    0.2) stay within 5 mm. Only the small in-channel maximum of Arno 9 (A/W 0.12) moves
    by about 3 cm. The brake is the limited number of knots of R's smooth.spline
    (64 coefficients for 100 levels), see docs/smoothing.md.
    """
    base, _ = level2[(key, 1.0)]
    c = curves[key]
    ext = smooth_curve(c.levels, c.hyd_depth, BankfullOptions(spar_min=-0.5),
                       folds=FOLDS[key])
    assert base.spar_on_border
    assert not ext.spar_on_border
    assert ext.spar < 0.0
    assert ext.maxima.shape == base.maxima.shape
    relevant = base.maxima[:, 1] >= min(MIN_HYD_DEPTHS)
    assert relevant.any()
    assert np.max(np.abs(ext.maxima[relevant, 0] - base.maxima[relevant, 0])) <= 0.005
    assert ext.bankfull_level == pytest.approx(base.bankfull_level, abs=0.005)


# --------------------------------------------------------------------------- others


def test_deterministic_with_seed(curves):
    c = curves[("arno.csv", 1)]
    a = smooth_curve(c.levels, c.hyd_depth, BankfullOptions(seed=7))
    b = smooth_curve(c.levels, c.hyd_depth, BankfullOptions(seed=7))
    for fa, fb in zip(a.folds, b.folds):
        assert_array_equal(fa, fb)
    assert a.spar == b.spar
    assert_array_equal(a.maxima, b.maxima)
    assert a.bankfull_level == b.bankfull_level
    other = make_folds(len(c.levels), 10, np.random.default_rng(8))
    assert any(not np.array_equal(fa, fo) for fa, fo in zip(a.folds, other))


@pytest.mark.parametrize(("n", "k"), [(100, 10), (95, 10), (7, 3), (10, 10), (11, 2)])
def test_folds_balanced(n, k):
    folds = make_folds(n, k, np.random.default_rng(0))
    sizes = [len(f) for f in folds]
    assert len(folds) == k
    assert max(sizes) - min(sizes) <= 1
    assert_array_equal(np.sort(np.concatenate(folds)), np.arange(n))
    assert all(np.all(np.diff(f) > 0) for f in folds)


@pytest.mark.parametrize("key", KEYS, ids=str)
def test_one_se_not_below_min_cv(level2, key):
    res, _ = level2[(key, 1.0)]
    idx, _ = select_spar(res.cv, "one_se")
    assert res.cv.spar[idx] >= res.spar


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cv_folds": 1}, {"cv_folds": 2.0}, {"cv_folds": True},
        {"spar_grid_size": 2}, {"spar_grid_size": 10.5},
        {"spar_min": float("nan")}, {"spar_max": float("inf")}, {"spar_min": "0"},
        {"spar_min": 1.0, "spar_max": 1.0}, {"spar_min": 1.5},
        {"selection": "1se"}, {"seed": -1}, {"seed": 1.0}, {"seed": False},
        {"no_max": "last"},
    ],
)
def test_invalid_smoothing_options(kwargs):
    with pytest.raises(ValueError):
        BankfullOptions(**kwargs)


@pytest.mark.parametrize(
    "labels",
    [[1, 1, 1, 1], [0, 1, 2, 1], [1, 3, 1, 3], [1.0, 2.0, 1.0, 2.0], [[1, 2], [1, 2]]],
)
def test_invalid_fold_labels(labels):
    with pytest.raises(ValueError):
        folds_from_labels(labels)


def test_invalid_external_folds():
    x = np.linspace(0.0, 1.0, 20)
    y = np.sin(3 * x)
    with pytest.raises(ValueError):
        smooth_curve(x, y, folds=[np.arange(10), np.arange(9, 20)])  # overlap
    with pytest.raises(ValueError):
        smooth_curve(x, y, folds=[np.arange(10), np.arange(10, 19)])  # missing index
    with pytest.raises(ValueError):
        smooth_curve(x, y, folds=[np.arange(20)])  # one fold
    with pytest.raises(ValueError):
        smooth_curve(x[:8], y[:8], BankfullOptions(cv_folds=10))  # cv_folds > n
    with pytest.raises(ValueError):
        make_folds(5, 10, np.random.default_rng(0))


def test_invalid_xy():
    with pytest.raises(ValueError):
        fit_smoothing_spline([0, 1, 1, 2, 3], [0, 1, 2, 3, 4], 0.5)
    with pytest.raises(ValueError):
        fit_smoothing_spline([0, 1, 2], [0, 1, 2], 0.5)
    with pytest.raises(ValueError):
        fit_smoothing_spline([0, 1, 2, np.nan], [0, 1, 2, 3], 0.5)
