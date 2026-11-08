"""Pure Python core of BankFullDetection (no QGIS, no R)."""

from .detection import (
    BankfullDetection,
    BankGeometry,
    ChannelPolygon,
    bank_geometry,
    channel_polygon,
    detect_bankfull,
)
from .hydraulics import HydraulicCurve, InvalidSectionError, hydraulic_curve
from .level import BankfullLevel, compute_bankfull_level
from .options import (
    CRITERIA,
    MULTICHANNEL_MODES,
    NO_MAX_MODES,
    SELECTION_MODES,
    BankfullOptions,
)
from .smoothing import (
    STATUS_NO_MAX_GE_MIN,
    STATUS_NO_MAXIMA,
    STATUS_OK,
    CVTable,
    SmoothingResult,
    SmoothingSpline,
    fit_smoothing_spline,
    folds_from_labels,
    make_folds,
    smooth_curve,
)

__all__ = [
    "CRITERIA",
    "MULTICHANNEL_MODES",
    "NO_MAX_MODES",
    "SELECTION_MODES",
    "STATUS_NO_MAXIMA",
    "STATUS_NO_MAX_GE_MIN",
    "STATUS_OK",
    "BankGeometry",
    "BankfullDetection",
    "BankfullLevel",
    "BankfullOptions",
    "CVTable",
    "ChannelPolygon",
    "HydraulicCurve",
    "InvalidSectionError",
    "SmoothingResult",
    "SmoothingSpline",
    "bank_geometry",
    "channel_polygon",
    "compute_bankfull_level",
    "detect_bankfull",
    "fit_smoothing_spline",
    "folds_from_labels",
    "hydraulic_curve",
    "make_folds",
    "smooth_curve",
]
