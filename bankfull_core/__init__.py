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
from .sampling import NoDataError, SampledSection, stations, trim_nodata
from .sections import (
    Crossing,
    Section,
    crossing_flags,
    crossings_inside_banks,
    drop_crossing_sections,
    find_crossings,
    generate_sections,
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
    "Crossing",
    "HydraulicCurve",
    "InvalidSectionError",
    "NoDataError",
    "SampledSection",
    "Section",
    "SmoothingResult",
    "SmoothingSpline",
    "bank_geometry",
    "channel_polygon",
    "compute_bankfull_level",
    "crossing_flags",
    "crossings_inside_banks",
    "detect_bankfull",
    "drop_crossing_sections",
    "find_crossings",
    "fit_smoothing_spline",
    "folds_from_labels",
    "generate_sections",
    "hydraulic_curve",
    "make_folds",
    "smooth_curve",
    "stations",
    "trim_nodata",
]
