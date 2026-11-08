# Smoothing of the A/W curve (`bankfull_core/smoothing.py`)

Replaces the R code of the original method (Scrucca 2014, `tools/spline_withR.py`, copied in
`golden_tools/scrucca.R`). No R, no rpy2: numpy + scipy only. Validated against
`tests/data/golden/` by `tests/test_smoothing.py`.

## Decisions

| | Decision | Reason |
|---|---|---|
| A | Reproduce R's `smooth.spline` in numpy; spar grid `log(linspace(exp(spar_min), exp(spar_max), 100))`, defaults 0 and 1 (= R's `log(seq(1, e, length = 100))`) | Same smoothing as the original method, verifiable point by point against R. `make_smoothing_spline` is not suitable (below). |
| B | Balanced random folds (`folds()` of the R code) with `numpy.random.Generator` and a seed (default 0), or external folds | Deterministic results; external folds allow the comparison with R's folds. |
| C | Selection `"min_cv"` (default, first minimum as `which.min`) or `"one_se"` (largest spar with `cv_error <= min + se`) | `min_cv` is what R actually applied; `one_se` is the intended 1-SE rule, available as an option. |
| D | Maxima: candidates from the sign changes of f' on the level grid (as R), root with `brentq` in each candidate interval (instead of Newton–Raphson), keep f'' < 0 | Removes Newton's failures while keeping R's grid resolution (see below). |
| E | No maxima → explicit status `no_maxima`; `no_max="original"` uses the last curve point, for comparisons only | The original fallback silently returns a level that is not a bankfull. |

CV error and SE as `cv.smooth.spline`: squared errors summed per fold, `cv_error = total / n`,
`se = sqrt(var(fold SSE / fold size) / k)` with the sample variance.

## Why not `scipy.interpolate.make_smoothing_spline`
It puts a knot at every point. R's `smooth.spline` uses fewer knots (64 coefficients for
n = 100, 62 for the n = 90 training sets of 10-fold CV), and this limits the roughness of the fit.
The A/W curves are almost noise-free: with every point as a knot, the CV error (with R's folds)
decreases monotonically towards the least smoothing on Arno 1, 2, 5 and on the synthetic
trapezoid, with no interior minimum near R's choice (e.g. Arno 1: R picks spar 0.23, scipy's CV
keeps decreasing down to λ/h³ = 10⁻³). Any lower bound of the λ grid would then be selected,
also where R chose an interior value.

## R construction reproduced
Sources: `stats::smooth.spline`, `stats:::.nknots.smspl`, `stats:::predict.smooth.spline.fit`
printed by R 4.6.2; `sbart.c`, `sgram.f`, `stxwx.f`, `sslvrg.f` of R's `stats` sources.

1. x rescaled to [0, 1]: `xbar = (x − x₀) / (x_N − x₀)`; unit weights (R takes sqrt of the
   weights and squares them again in `stxwx`).
2. Number of inner knots `.nknots.smspl(n)` (n < 50: n; then `trunc(2^(...))` by ranges);
   knots `xbar[seq.int(1, n, length.out = nknots)]` with **truncated** fractional indices,
   end knots repeated three more times; `nk = nknots + 2` cubic B-splines.
3. `X'WX` and `X'Wy` with the B-spline design matrix (`scipy.interpolate.BSpline`).
4. Penalty Σ as `sgram.f`: B'' is linear on each knot interval, and each interval contributes
   `w·(a_i a_j + ½(b_i a_j + a_i b_j) + 0.3330·b_i b_j)` (a = B'' at the left end, b = its change
   over the interval). R uses the literal **0.3330**, not 1/3; it is kept.
5. `r = Σ hs0[3..nk−3] / Σ sg0[3..nk−3]` (1-based diagonal elements), `λ = r · 16^(6·spar − 2)
   = r · 256^(3·spar − 1)`.
6. `(X'WX + λΣ) c = X'Wy` solved by banded Cholesky (`scipy.linalg.solveh_banded`, as LINPACK
   `dpbfa`/`dpbsl`).
7. Evaluation: B-spline inside [0, 1]; outside, linear extrapolation with end values and slopes
   (used in CV when a fold holds the first or last level); derivatives divided by range^d.

With equally spaced x, r depends only on n (not on y or on the x range):

| n | r | λ at spar = 0 | λ at spar = 1 |
|---|---|---|---|
| 100 | 1.1970405348608106e-6 | 4.6759395893000413e-9 | 0.078449248492638082 |
| 90 | 1.2517182331491644e-6 | 4.8895243482389234e-9 | 0.082032606127663638 |

λ refers to the rescaled abscissa. Agreement with R: fitted curve at R's spar within 3e-15
(parabola 3e-13); CV table within 5e-11 relative (parabola 2e-8); same selected spar on all 12
golden sections.

## The lower limit spar = 0
spar = 0 is the least smoothing allowed by the original grid. On Arno 2 and 9 R's CV picked it
(the selected spar is on the border, flagged by `spar_on_border`). Extending the grid below 0
with R's construction, the CV finds an interior minimum just below the border (spar −0.08…−0.13,
stable for `spar_min` from −0.5 to −1.5). No maximum is added, the maxima with A/W ≥ 0.2 (those
that can become the bankfull) move by ≤ 2 mm and the bankfull level by ≤ 2 mm. Only the small
in-channel maximum of Arno 9 (A/W 0.12, below both thresholds) moves by 2.7 cm.
The initial hypothesis was that spar = 0 is a brake against spurious maxima. It was disproved:
with R's knot rule the limited number of knots, not spar = 0, is what prevents them. The limit is
kept to stay on the original method.

## Maxima from the grid candidates
R takes as candidates the levels where the sign of f' on the 100-level grid changes, then runs
Newton–Raphson from each candidate. Here the root is bracketed in the candidate interval and
found with `brentq`, so it cannot jump to another root or fail to converge.
A maximum and a minimum inside the same grid interval give no sign change and are not found.
This filters wiggles narrower than one level step. All exact roots of f' would add:

| Section | Level | A/W | Prominence* | Grid interval |
|---|---|---|---|---|
| Arno 3 | 14.271 | 4.152 | 0.0018 | 14.252–14.366 |
| Arno 9 | 13.096 | 3.224 | 0.0001 | 13.041–13.155 |

\* A/W at the maximum minus the higher adjacent minimum.

## Differences from the golden data (original method)

| Section | Golden (R) | New | Reason |
|---|---|---|---|
| Synthetic 1, trapezoid | no bankfull (`r_no_local_max`) | 2.972 | Newton converged only to roots with f'' ≥ 0. |
| Arno 2 | 13.881 | 13.315 | The candidate at 13.24 exists, but Newton jumped to 14.947 (duplicate in `r_maxima.csv`) and the maximum at 13.315 (A/W 3.06) was lost. The expert estimate is 13.54 m: the new value is closer (0.23 m vs 0.34 m). |
| Arno 8 | 12.658 | 12.658 | Extra maximum at 17.005 (Newton jumped to 15.089); above the bankfull, no effect. |
| Synthetic 2, inner bench | 2.967 | 1.438 | Newton did not converge from the candidate at 1.405. The bench maximum (A/W 1.19) is above both thresholds and becomes the bankfull. |
| Synthetic 4, parabola | 3.9 (fallback) | `no_maxima` | Explicit outcome; 3.9 with `no_max="original"`. |

In all other cases the maxima coincide with R within 2.4e-10 m and the bankfull level is
the same for `min_hyd_depth` 1.0 and 0.2.

**Known limit of the method (synthetic 2).** The bankfull is the first maximum, i.e. the lowest,
with A/W ≥ `min_hyd_depth`. An inner bench whose maximum exceeds the threshold is taken as the
bankfull even when the bank top gives a larger maximum. The original method shared this limit,
which was hidden on this section by Newton's failure. A different criterion is a future method
decision.

## Other deviations from the original method
- 1-SE rule: never applied in R (`spar1se == sparmin` always, see `tests/data/golden/README.md`);
  the default here is `min_cv`, the corrected rule is `selection="one_se"`.
- Folds: numpy's generator, not R's; with the same seed the folds differ from R's, so
  results with internal folds may differ slightly from the golden data (which used R's folds).
- R's outer `while(check)` loop (re-running CV when no Newton root converged) is not needed.
