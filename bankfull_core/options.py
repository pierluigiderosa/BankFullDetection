"""Parameters of the bankfull detection method."""

import math
from dataclasses import dataclass
from numbers import Integral, Real

#: Allowed values of ``BankfullOptions.multichannel``.
#: - "original": all wet polygons at a level contribute to A and W (original mainFun).
#: - "thalweg": only the wet polygon containing the lowest point of the section is used
#:   (idea from HydXS, Garber & Thompson 2024).
MULTICHANNEL_MODES = ("original", "thalweg")

#: Allowed values of ``BankfullOptions.selection`` (choice of spar from the CV table).
#: - "min_cv": first spar with the minimum CV error (what the original R code applied).
#: - "one_se": largest spar (strongest smoothing) with CV error <= minimum + its SE.
SELECTION_MODES = ("min_cv", "one_se")

#: Allowed values of ``BankfullOptions.no_max`` (smoothed curve without local maxima).
#: - "explicit": no bankfull, with an explicit status.
#: - "original": the last point of the curve is used, as in the original method.
NO_MAX_MODES = ("explicit", "original")


def _is_int(value):
    return isinstance(value, Integral) and not isinstance(value, bool)


def _is_finite_real(value):
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


@dataclass(frozen=True)
class BankfullOptions:
    """Method parameters.

    Attributes:
        n_levels: number of water levels between ``minY + 0.1`` and ``maxY - 0.1``.
        min_hyd_depth: minimum hydraulic depth A/W [m] for a maximum to be accepted
            as bankfull.
        multichannel: how multiple wet polygons are handled, see ``MULTICHANNEL_MODES``.
        cv_folds: number of cross-validation folds.
        spar_grid_size: number of spar values in the CV grid.
        spar_min, spar_max: ends of the spar grid. The grid is
            ``log(linspace(exp(spar_min), exp(spar_max), spar_grid_size))``; the defaults
            give the grid of the original R code, ``log(seq(1, e, length = 100))``.
            ``spar_min = 0`` is the minimum smoothing of the original method.
        selection: how spar is chosen from the CV table, see ``SELECTION_MODES``.
        seed: seed of the random CV folds (``numpy.random.default_rng``).
        no_max: behaviour when the smoothed curve has no maxima, see ``NO_MAX_MODES``.
    """

    n_levels: int = 100
    min_hyd_depth: float = 1.0
    multichannel: str = "original"
    cv_folds: int = 10
    spar_grid_size: int = 100
    spar_min: float = 0.0
    spar_max: float = 1.0
    selection: str = "min_cv"
    seed: int = 0
    no_max: str = "explicit"

    def __post_init__(self):
        if not _is_int(self.n_levels) or self.n_levels < 2:
            raise ValueError(f"n_levels must be an integer >= 2, got {self.n_levels!r}")
        if not _is_finite_real(self.min_hyd_depth) or self.min_hyd_depth <= 0:
            raise ValueError(
                f"min_hyd_depth must be a finite number > 0, got {self.min_hyd_depth!r}"
            )
        if self.multichannel not in MULTICHANNEL_MODES:
            raise ValueError(
                f"multichannel must be one of {MULTICHANNEL_MODES}, "
                f"got {self.multichannel!r}"
            )
        if not _is_int(self.cv_folds) or self.cv_folds < 2:
            raise ValueError(f"cv_folds must be an integer >= 2, got {self.cv_folds!r}")
        if not _is_int(self.spar_grid_size) or self.spar_grid_size < 3:
            raise ValueError(
                f"spar_grid_size must be an integer >= 3, got {self.spar_grid_size!r}"
            )
        for name in ("spar_min", "spar_max"):
            if not _is_finite_real(getattr(self, name)):
                raise ValueError(
                    f"{name} must be a finite number, got {getattr(self, name)!r}"
                )
        if self.spar_min >= self.spar_max:
            raise ValueError(
                f"spar_min ({self.spar_min!r}) must be smaller than "
                f"spar_max ({self.spar_max!r})"
            )
        if self.selection not in SELECTION_MODES:
            raise ValueError(
                f"selection must be one of {SELECTION_MODES}, got {self.selection!r}"
            )
        if not _is_int(self.seed) or self.seed < 0:
            raise ValueError(f"seed must be an integer >= 0, got {self.seed!r}")
        if self.no_max not in NO_MAX_MODES:
            raise ValueError(f"no_max must be one of {NO_MAX_MODES}, got {self.no_max!r}")
