"""Pure Python core of BankFullDetection (no QGIS, no R)."""

from .hydraulics import HydraulicCurve, InvalidSectionError, hydraulic_curve
from .options import MULTICHANNEL_MODES, BankfullOptions

__all__ = [
    "MULTICHANNEL_MODES",
    "BankfullOptions",
    "HydraulicCurve",
    "InvalidSectionError",
    "hydraulic_curve",
]
