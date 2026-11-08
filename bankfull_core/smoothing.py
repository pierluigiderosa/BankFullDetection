"""Smoothing of the A/W curve and search of its maxima (replaces R).

The original method (Scrucca 2014, R code in ``tools/spline_withR.py``) fits
``smooth.spline`` with the smoothing parameter chosen by 10-fold cross-validation over a
grid of ``spar`` values and looks for the local maxima of the fitted curve.

Here the fit of R's ``smooth.spline`` (R 4.6.2, ``stats``) is reproduced in numpy:
x rescaled to [0, 1], R's rule for the number of knots, cubic B-spline basis, penalty
matrix as computed by ``sgram.f``, ``lambda = r * 256^(3 spar - 1)`` with ``r`` from
``sbart.c``, banded Cholesky solution and linear extrapolation outside the data range as
in ``predict.smooth.spline.fit``.

Maxima: as in R, the candidates are the grid intervals where f' changes sign; instead of
Newton-Raphson, the root of f' in each such interval is found with ``brentq`` and only
roots with f'' < 0 are kept. scipy is used for the B-spline basis, the banded solver and
the root finding. See ``docs/smoothing.md``.
"""

import math
from dataclasses import dataclass
from numbers import Integral

import numpy as np
from scipy.interpolate import BSpline, PPoly
from scipy.linalg import solveh_banded
from scipy.optimize import brentq

from .options import BankfullOptions

#: ``SmoothingResult.status`` values.
STATUS_OK = "ok"
STATUS_NO_MAXIMA = "no_maxima"
STATUS_NO_MAX_GE_MIN = "no_max_ge_min_hyd_depth"

_DEGREE = 3

# Coefficient of yw2_i * yw2_j in sgram.f. The exact integral of the product of two linear
# functions would use 1/3; R uses the literal 0.3330 and it is kept to reproduce R's fit.
_SGRAM_C = 0.3330

# Relative tolerance (on the [0, 1] rescaled axis) under which two roots of f' are the same.
_ROOT_DEDUP_TOL = 1e-9

# Absolute tolerance [x units] of brentq on the roots of f'.
_ROOT_XTOL = 1e-12


def _nknots(n):
    """Number of inner knots, as ``stats:::.nknots.smspl`` (R 4.6.2)."""
    if n < 50:
        return n
    a1 = math.log2(50)
    a2 = math.log2(100)
    a3 = math.log2(140)
    a4 = math.log2(200)
    if n < 200:
        v = 2 ** (a1 + (a2 - a1) * (n - 50) / 150)
    elif n < 800:
        v = 2 ** (a2 + (a3 - a2) * (n - 200) / 600)
    elif n < 3200:
        v = 2 ** (a3 + (a4 - a3) * (n - 800) / 2400)
    else:
        v = 200 + (n - 3200) ** 0.2
    return math.trunc(v)


def _knot_vector(xbar):
    """Knot vector of ``smooth.spline`` for rescaled, strictly increasing x."""
    n = len(xbar)
    nknots = _nknots(n)
    # seq.int(1, n, length.out = nknots): from + i * by, last element set to `to`.
    # R truncates fractional indices.
    if nknots > 1:
        seq = 1.0 + np.arange(nknots) * ((n - 1) / (nknots - 1))
        seq[-1] = n
    else:
        seq = np.array([1.0])
    inner = xbar[np.trunc(seq).astype(int) - 1]
    return np.concatenate([np.repeat(xbar[0], 3), inner, np.repeat(xbar[-1], 3)])


def _validate_xy(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y):
        raise ValueError("x and y must be 1-D arrays of the same length")
    if len(x) < 4:
        raise ValueError(f"at least 4 points are needed, got {len(x)}")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise ValueError("x and y must be finite")
    if np.any(np.diff(x) <= 0):
        raise ValueError("x must be strictly increasing")
    return x, y


class _SplineSystem:
    """Parts of the ``smooth.spline`` problem that do not depend on spar."""

    def __init__(self, x, y):
        x, y = _validate_xy(x, y)
        self.x_min = float(x[0])
        self.x_range = float(x[-1] - x[0])
        xbar = (x - self.x_min) / self.x_range
        self.knots = _knot_vector(xbar)
        nk = len(self.knots) - _DEGREE - 1
        self.nk = nk

        # stxwx.f: weights are sqrt(w) and enter squared; here w = 1.
        basis = BSpline.design_matrix(xbar, self.knots, _DEGREE).toarray()
        self.xwy = basis.T @ y
        hs = basis.T @ basis

        sg = self._penalty()
        self.ratio = float(np.sum(np.diag(hs)[2:nk - 3]) / np.sum(np.diag(sg)[2:nk - 3]))

        # Upper banded storage (bandwidth 3) for solveh_banded.
        self._hs_band = self._to_band(hs)
        self._sg_band = self._to_band(sg)

    def _penalty(self):
        """Gram matrix of B'' as in sgram.f (B'' is linear on each knot interval)."""
        t = self.knots
        nk = self.nk
        d2 = BSpline(t, np.eye(nk), _DEGREE, extrapolate=False).derivative(2)
        left = t[:-1]
        width = np.diff(t)
        keep = width > 0
        left = left[keep]
        width = width[keep]
        yw1 = d2(left)
        yw2 = 2.0 * (d2(left + 0.5 * width) - yw1)
        yw1 = np.nan_to_num(yw1)
        yw2 = np.nan_to_num(yw2)
        sg = np.zeros((nk, nk))
        for w, a, b in zip(width, yw1, yw2):
            sg += w * (np.outer(a, a) + 0.5 * (np.outer(b, a) + np.outer(a, b))
                       + _SGRAM_C * np.outer(b, b))
        return sg

    def _to_band(self, m):
        band = np.zeros((_DEGREE + 1, self.nk))
        for d in range(_DEGREE + 1):
            band[_DEGREE - d, d:] = np.diagonal(m, d)
        return band

    def lam(self, spar):
        # sbart.c: ratio * R_pow(16., spar * 6. - 2.)
        return self.ratio * 16.0 ** (spar * 6.0 - 2.0)

    def fit(self, spar):
        lam = self.lam(spar)
        coef = solveh_banded(self._hs_band + lam * self._sg_band, self.xwy)
        return SmoothingSpline(self.knots, coef, self.x_min, self.x_range,
                               spar=float(spar), lam=lam, ratio=self.ratio)


class SmoothingSpline:
    """Fitted smoothing spline, evaluated as R's ``predict.smooth.spline.fit``.

    Inside the data range the cubic B-spline is evaluated; outside it the curve is
    extended linearly with the end values and slopes.
    """

    def __init__(self, knots, coef, x_min, x_range, spar, lam, ratio):
        self.knots = knots
        self.coef = coef
        self.x_min = x_min
        self.x_range = x_range
        self.spar = spar
        self.lam = lam
        self.ratio = ratio
        self._bs = BSpline(knots, coef, _DEGREE, extrapolate=False)

    def _eval_scaled(self, xs, deriv):
        bs = self._bs if deriv == 0 else self._bs.derivative(deriv)
        return bs(xs)

    def __call__(self, x, deriv=0):
        if deriv < 0 or int(deriv) != deriv:
            raise ValueError("deriv must be a non-negative integer")
        x = np.asarray(x, dtype=float)
        scalar = x.ndim == 0
        xs = np.atleast_1d((x - self.x_min) / self.x_range)
        out = np.empty_like(xs)
        left = xs < 0
        right = xs > 1
        inside = ~(left | right)
        if inside.any():
            out[inside] = self._eval_scaled(xs[inside], deriv)
        if (left | right).any():
            ends = np.array([0.0, 1.0])
            slopes = self._eval_scaled(ends, 1)
            if deriv == 0:
                values = self._eval_scaled(ends, 0)
                out[left] = values[0] + slopes[0] * xs[left]
                out[right] = values[1] + slopes[1] * (xs[right] - 1.0)
            elif deriv == 1:
                out[left] = slopes[0]
                out[right] = slopes[1]
            else:
                out[left | right] = 0.0
        if deriv > 0:
            out = out / self.x_range ** deriv
        return out[0] if scalar else out

    def stationary_points(self):
        """All exact roots of f' inside the data range (duplicates removed), ascending.

        Diagnostic only: unlike ``find_maxima`` it also returns pairs of roots that lie
        within a single grid interval.
        """
        pp = PPoly.from_spline(self._bs.derivative(1))
        roots = pp.roots(discontinuity=False, extrapolate=False)
        roots = roots[np.isfinite(roots)]
        roots = np.sort(roots[(roots >= 0.0) & (roots <= 1.0)])
        if roots.size:
            keep = np.concatenate([[True], np.diff(roots) > _ROOT_DEDUP_TOL])
            roots = roots[keep]
        return self.x_min + roots * self.x_range


def fit_smoothing_spline(x, y, spar):
    """Fit ``smooth.spline(x, y, spar = spar)`` as R 4.6.2 does (unit weights).

    Args:
        x: strictly increasing abscissae (at least 4).
        y: ordinates.
        spar: smoothing parameter on R's scale.

    Returns:
        SmoothingSpline.
    """
    return _SplineSystem(x, y).fit(spar)


@dataclass(frozen=True)
class CVTable:
    """Cross-validation table (read-only arrays), as ``cv.smooth.spline``.

    Attributes:
        spar: spar grid (increasing).
        cv_error: sum over folds of the squared prediction errors, divided by n.
        se: standard error of the per-fold mean squared errors.
    """

    spar: np.ndarray
    cv_error: np.ndarray
    se: np.ndarray


@dataclass(frozen=True)
class SmoothingResult:
    """Result of ``smooth_curve``.

    Attributes:
        spar: selected spar.
        lam: lambda of the final fit (on the [0, 1] rescaled abscissa, as R).
        spar_index: index of ``spar`` in the CV grid.
        spar_on_border: True if the selected spar is the first or the last of the grid.
        cv: CVTable.
        folds: tuple of index arrays (0-based) used for cross-validation.
        spline: final SmoothingSpline.
        maxima: (N, 2) read-only array of (level, smoothed value) at the local maxima,
            ascending level.
        bankfull_level, bankfull_value: bankfull level and smoothed A/W (raw A/W if
            ``fallback``), or None.
        status: STATUS_OK, STATUS_NO_MAXIMA or STATUS_NO_MAX_GE_MIN.
        fallback: True if the last curve point was used because there were no maxima
            (``no_max = "original"``).
    """

    spar: float
    lam: float
    spar_index: int
    spar_on_border: bool
    cv: CVTable
    folds: tuple
    spline: SmoothingSpline
    maxima: np.ndarray
    bankfull_level: float | None
    bankfull_value: float | None
    status: str
    fallback: bool


def spar_grid(options=None):
    """spar grid ``log(linspace(exp(spar_min), exp(spar_max), spar_grid_size))``."""
    if options is None:
        options = BankfullOptions()
    return np.log(np.linspace(math.exp(options.spar_min), math.exp(options.spar_max),
                              options.spar_grid_size))


def make_folds(n, k, rng):
    """Balanced random folds as ``folds()`` of the original R code.

    The labels ``0..k-1`` are repeated to length n and randomly permuted, so fold sizes
    differ by at most 1.

    Returns:
        tuple of k ascending arrays of 0-based indices.
    """
    if not isinstance(n, Integral) or not isinstance(k, Integral) or k < 2 or n < k:
        raise ValueError(f"need integers 2 <= k <= n, got n={n!r}, k={k!r}")
    labels = rng.permutation(np.resize(np.arange(k), n))
    return tuple(np.flatnonzero(labels == i) for i in range(k))


def folds_from_labels(labels):
    """Folds from 1-based fold labels per point (e.g. exported from R)."""
    labels = np.asarray(labels)
    if labels.ndim != 1 or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("fold labels must be a 1-D integer sequence")
    k = int(labels.max()) if labels.size else 0
    if labels.size == 0 or labels.min() < 1 or k < 2:
        raise ValueError("fold labels must be integers 1..k with k >= 2")
    folds = tuple(np.flatnonzero(labels == i) for i in range(1, k + 1))
    if any(f.size == 0 for f in folds):
        raise ValueError("every fold label 1..k must be used")
    return folds


def _check_folds(folds, n):
    folds = tuple(np.asarray(f, dtype=int) for f in folds)
    if len(folds) < 2:
        raise ValueError("at least 2 folds are needed")
    if any(f.ndim != 1 or f.size == 0 for f in folds):
        raise ValueError("folds must be non-empty 1-D index arrays")
    allidx = np.sort(np.concatenate(folds))
    if allidx.size != n or not np.array_equal(allidx, np.arange(n)):
        raise ValueError(f"folds must be a partition of the indices 0..{n - 1}")
    return tuple(np.sort(f) for f in folds)


def cross_validate(x, y, spars, folds):
    """CV error and SE for each spar, as ``cv.smooth.spline`` of the original R code."""
    x, y = _validate_xy(x, y)
    n = len(x)
    folds = _check_folds(folds, n)
    spars = np.asarray(spars, dtype=float)
    err = np.empty((len(spars), len(folds)))
    for j, test in enumerate(folds):
        train = np.ones(n, dtype=bool)
        train[test] = False
        system = _SplineSystem(x[train], y[train])
        for s, spar in enumerate(spars):
            pred = system.fit(spar)(x[test])
            err[s, j] = np.sum((y[test] - pred) ** 2)
    cv_error = err.sum(axis=1) / n
    sizes = np.array([len(f) for f in folds], dtype=float)
    mse = err / sizes
    se = np.sqrt(np.var(mse, axis=1, ddof=1) / len(folds))
    arrays = (spars.copy(), cv_error, se)
    for a in arrays:
        a.flags.writeable = False
    return CVTable(*arrays)


def select_spar(table, selection="min_cv"):
    """Index of the selected spar and whether it lies on the border of the grid.

    "min_cv": first spar with the minimum CV error (R's ``which.min``).
    "one_se": largest spar with ``cv_error <= min(cv_error) + se`` at the minimum.
    """
    i_min = int(np.argmin(table.cv_error))
    if selection == "min_cv":
        idx = i_min
    elif selection == "one_se":
        threshold = table.cv_error[i_min] + table.se[i_min]
        idx = int(np.flatnonzero(table.cv_error <= threshold)[-1])
    else:
        raise ValueError(f"unknown selection {selection!r}")
    return idx, idx in (0, len(table.spar) - 1)


def find_maxima(spline, x):
    """Local maxima of the spline, searched from the sign changes of f' on the grid x.

    As in the original R code, the candidates are the intervals ``[x[i], x[i+1]]`` where
    the sign of f' changes; the root of f' in each interval is found with ``brentq``
    (instead of Newton-Raphson from ``x[i]``) and only roots with f'' < 0 are kept.
    A maximum and a minimum within the same grid interval give no sign change and are
    not found: the grid filters out wiggles narrower than one level step.

    Returns:
        (N, 2) array of (level, f(level)), ascending level.
    """
    x = np.asarray(x, dtype=float)
    d1 = spline(x, deriv=1)
    sign = np.sign(d1)
    roots = []
    for i in np.flatnonzero(sign[:-1] != sign[1:]):
        if d1[i] == 0:
            roots.append(x[i])
        elif d1[i + 1] == 0:
            roots.append(x[i + 1])
        else:
            roots.append(brentq(lambda t: spline(t, deriv=1), x[i], x[i + 1],
                                xtol=_ROOT_XTOL))
    roots = np.array(roots, dtype=float)
    if roots.size:
        keep = np.concatenate(
            [[True], np.diff(roots) > _ROOT_DEDUP_TOL * (x[-1] - x[0])]
        )
        roots = roots[keep]
        roots = roots[spline(roots, deriv=2) < 0]
    return np.column_stack([roots, spline(roots)]) if roots.size else np.empty((0, 2))


def pick_bankfull(maxima, x, y, min_hyd_depth, no_max="explicit"):
    """First maximum (lowest level) with value >= min_hyd_depth.

    With no maxima: STATUS_NO_MAXIMA if ``no_max == "explicit"``; with
    ``no_max == "original"`` the last raw point ``(x[-1], y[-1])`` is used as the only
    candidate, as in the original method.

    Returns:
        (level or None, value or None, status, fallback).
    """
    maxima = np.asarray(maxima, dtype=float).reshape(-1, 2)
    fallback = False
    if maxima.shape[0] == 0:
        if no_max == "explicit":
            return None, None, STATUS_NO_MAXIMA, False
        if no_max != "original":
            raise ValueError(f"unknown no_max {no_max!r}")
        maxima = np.array([[float(x[-1]), float(y[-1])]])
        fallback = True
    ok = np.flatnonzero(maxima[:, 1] >= min_hyd_depth)
    if ok.size == 0:
        return None, None, STATUS_NO_MAX_GE_MIN, fallback
    level, value = maxima[ok[0]]
    return float(level), float(value), STATUS_OK, fallback


def smooth_curve(x, y, options=None, folds=None):
    """Smooth the A/W curve, choose spar by CV and pick the bankfull level.

    Args:
        x: water levels, strictly increasing.
        y: hydraulic depth A/W at each level.
        options: BankfullOptions (defaults if None).
        folds: optional external CV folds (sequence of 0-based index arrays that
            partition ``range(len(x))``); if None, balanced random folds are drawn with
            ``numpy.random.default_rng(options.seed)``.

    Returns:
        SmoothingResult.
    """
    if options is None:
        options = BankfullOptions()
    x, y = _validate_xy(x, y)
    if folds is None:
        if options.cv_folds > len(x):
            raise ValueError(
                f"cv_folds ({options.cv_folds}) exceeds the number of points ({len(x)})"
            )
        folds = make_folds(len(x), options.cv_folds, np.random.default_rng(options.seed))
    else:
        folds = _check_folds(folds, len(x))

    table = cross_validate(x, y, spar_grid(options), folds)
    idx, on_border = select_spar(table, options.selection)
    spline = _SplineSystem(x, y).fit(table.spar[idx])
    maxima = find_maxima(spline, x)
    maxima.flags.writeable = False
    level, value, status, fallback = pick_bankfull(
        maxima, x, y, options.min_hyd_depth, options.no_max
    )
    return SmoothingResult(
        spar=float(table.spar[idx]), lam=spline.lam, spar_index=idx,
        spar_on_border=on_border, cv=table, folds=folds, spline=spline, maxima=maxima,
        bankfull_level=level, bankfull_value=value, status=status, fallback=fallback,
    )
