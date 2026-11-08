"""Bankfull level of a cross-section from one or more cross-validation runs.

The random CV folds change the selected spar and, on some sections, the bankfull level
(up to about 0.8 m on the Arno test sections with the recommended options). With
``options.n_runs > 1`` the smoothing is repeated with seeds
``options.seed .. options.seed + n_runs - 1`` and the median level is returned, with its
spread over the runs.
"""

import dataclasses
from dataclasses import dataclass

import numpy as np

from .hydraulics import hydraulic_curve
from .options import BankfullOptions
from .smoothing import STATUS_OK, smooth_curve


@dataclass(frozen=True)
class BankfullLevel:
    """Result of ``compute_bankfull_level``.

    Attributes:
        level: median bankfull level over the runs that give one, or None. With an even
            number of such runs it is the mean of the two central levels, which need not
            be a maximum of any run.
        level_min, level_max: lowest and highest bankfull level over those runs, or None.
        n_runs_ok: number of runs that give a bankfull level.
        run_levels: bankfull level of each run (None if the run gives none), in seed order.
        status: STATUS_OK if at least one run gives a bankfull level, otherwise the
            status of the first run.
        options: BankfullOptions used.
    """

    level: float | None
    level_min: float | None
    level_max: float | None
    n_runs_ok: int
    run_levels: tuple
    status: str
    options: BankfullOptions


def compute_bankfull_level(points, options=None):
    """Bankfull level of a section: A/W curve, then ``options.n_runs`` smoothing runs.

    Args:
        points: sequence of (distance, z) pairs, distances strictly increasing.
        options: BankfullOptions (defaults if None). The CV folds of run i are drawn with
            seed ``options.seed + i``.

    Returns:
        BankfullLevel. With ``n_runs == 1`` the level is the one of ``smooth_curve``.

    Raises:
        InvalidSectionError: if the section is not valid.
    """
    if options is None:
        options = BankfullOptions()
    curve = hydraulic_curve(points, options)
    results = [
        smooth_curve(curve.levels, curve.hyd_depth,
                     dataclasses.replace(options, seed=options.seed + i))
        for i in range(options.n_runs)
    ]
    run_levels = tuple(r.bankfull_level for r in results)
    ok = [z for z in run_levels if z is not None]
    if ok:
        level = float(np.median(ok))
        level_min, level_max = float(min(ok)), float(max(ok))
        status = STATUS_OK
    else:
        level = level_min = level_max = None
        status = results[0].status
    return BankfullLevel(level=level, level_min=level_min, level_max=level_max,
                         n_runs_ok=len(ok), run_levels=run_levels, status=status,
                         options=options)
