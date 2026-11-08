"""Parameters of the bankfull detection method."""

import math
from dataclasses import dataclass
from numbers import Integral, Real

#: Allowed values of ``BankfullOptions.multichannel``.
#: - "original": all wet polygons at a level contribute to A and W (original mainFun).
#: - "thalweg": only the wet polygon containing the lowest point of the section is used
#:   (idea from HydXS, Garber & Thompson 2024).
MULTICHANNEL_MODES = ("original", "thalweg")


@dataclass(frozen=True)
class BankfullOptions:
    """Method parameters.

    Attributes:
        n_levels: number of water levels between ``minY + 0.1`` and ``maxY - 0.1``.
        min_hyd_depth: minimum hydraulic depth A/W [m] for a maximum to be accepted
            as bankfull.
        multichannel: how multiple wet polygons are handled, see ``MULTICHANNEL_MODES``.
    """

    n_levels: int = 100
    min_hyd_depth: float = 1.0
    multichannel: str = "original"

    def __post_init__(self):
        if (
            isinstance(self.n_levels, bool)
            or not isinstance(self.n_levels, Integral)
            or self.n_levels < 2
        ):
            raise ValueError(f"n_levels must be an integer >= 2, got {self.n_levels!r}")
        if (
            isinstance(self.min_hyd_depth, bool)
            or not isinstance(self.min_hyd_depth, Real)
            or not math.isfinite(self.min_hyd_depth)
            or self.min_hyd_depth <= 0
        ):
            raise ValueError(
                f"min_hyd_depth must be a finite number > 0, got {self.min_hyd_depth!r}"
            )
        if self.multichannel not in MULTICHANNEL_MODES:
            raise ValueError(
                f"multichannel must be one of {MULTICHANNEL_MODES}, "
                f"got {self.multichannel!r}"
            )
