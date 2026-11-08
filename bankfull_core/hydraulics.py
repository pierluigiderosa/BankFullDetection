"""Hydraulic depth (A/W) curve of a cross-section.

For a sequence of water levels the wet polygon of the section is computed and the
hydraulic depth A/W (wet area / water surface width) is derived, as in the original
``mainFun`` of BankFullDetection (De Rosa et al. 2019, IJGI 8(11):480).
"""

from dataclasses import dataclass

import numpy as np
from shapely.geometry import LineString, Polygon, box

from .options import BankfullOptions

# The section polygon is closed at the top at maxY + _TOP_EXTENSION, as in the original
# mainFun (maxY + 1). Water levels never exceed maxY - _LEVEL_OFFSET (= maxY - 0.1), so the
# closing edge is always above every level and never enters the wet polygons: its height
# does not affect the curve as long as it is greater than 0.1 m. (Strictly, any positive
# value keeps the polygon valid and above the top level; it is not a method parameter.)
_TOP_EXTENSION = 1.0

# Levels go from minY + _LEVEL_OFFSET to maxY - _LEVEL_OFFSET, as in the original mainFun.
_LEVEL_OFFSET = 0.1


class InvalidSectionError(ValueError):
    """The cross-section cannot be processed."""


@dataclass(frozen=True)
class HydraulicCurve:
    """Hydraulic quantities of a section for each water level (read-only arrays).

    Attributes:
        levels: absolute water levels [m].
        hyd_depth: hydraulic depth A/W [m].
        wet_area: wet area A [m2].
        wet_width: water surface width W [m].
        wet_perimeter: wetted perimeter P [m] (A/P is the hydraulic radius).
        n_wet_polygons: number of disjoint wet polygons at the level.
        n_used_polygons: number of wet polygons used for A, W and P
            (equal to ``n_wet_polygons`` with "original", 1 with "thalweg").
        min_z, max_z: lowest and highest elevation of the section.
        multichannel: multichannel mode used.
    """

    levels: np.ndarray
    hyd_depth: np.ndarray
    wet_area: np.ndarray
    wet_width: np.ndarray
    wet_perimeter: np.ndarray
    n_wet_polygons: np.ndarray
    n_used_polygons: np.ndarray
    min_z: float
    max_z: float
    multichannel: str


def hydraulic_curve(points, options=None):
    """Compute the A/W curve of a cross-section.

    Args:
        points: sequence of (distance, z) pairs, distances strictly increasing.
            It is never modified.
        options: ``BankfullOptions``; defaults are used if None.

    Returns:
        HydraulicCurve.

    Raises:
        InvalidSectionError: if the section is not valid.
    """
    return _hydraulic_curve(points, options, top_extension=_TOP_EXTENSION)


def _hydraulic_curve(points, options, top_extension):
    if options is None:
        options = BankfullOptions()
    pts = _validate_points(points)
    pts_list = [(float(d), float(z)) for d, z in pts]

    # Same construction as the original mainFun (on a copy of the points).
    polygon_orig = Polygon(pts_list)
    border = LineString(pts_list)
    minx, min_z, maxx, max_z = polygon_orig.bounds
    top = max_z + top_extension
    polygon_xs = Polygon([(minx, top), *pts_list, (maxx, top)])

    levels = np.linspace(min_z + _LEVEL_OFFSET, max_z - _LEVEL_OFFSET, options.n_levels)
    n = len(levels)
    wet_area = np.empty(n)
    wet_width = np.empty(n)
    wet_perimeter = np.empty(n)
    n_wet = np.empty(n, dtype=int)
    n_used = np.empty(n, dtype=int)

    for i, h in enumerate(levels):
        water_box = box(minx, min_z, maxx, h)
        water_line = LineString([(minx, h), (maxx, h)])
        wet = polygon_xs.intersection(water_box)
        perimeter = border.intersection(water_box)
        surface = water_line.intersection(polygon_xs)

        parts = _polygon_parts(wet)
        n_wet[i] = len(parts)
        n_used[i] = len(parts)
        if options.multichannel == "thalweg" and len(parts) > 1:
            wet = _thalweg_polygon(parts, min_z)
            perimeter = wet.intersection(perimeter)
            surface = wet.intersection(surface)
            n_used[i] = 1

        wet_area[i] = wet.area
        wet_width[i] = surface.length
        wet_perimeter[i] = perimeter.length

    hyd_depth = wet_area / wet_width
    arrays = (levels, hyd_depth, wet_area, wet_width, wet_perimeter, n_wet, n_used)
    for a in arrays:
        a.flags.writeable = False
    return HydraulicCurve(*arrays, min_z=min_z, max_z=max_z,
                          multichannel=options.multichannel)


def _validate_points(points):
    """Return a float (N, 2) copy of ``points`` or raise InvalidSectionError."""
    try:
        pts = np.array(points, dtype=float)
    except (TypeError, ValueError) as exc:
        raise InvalidSectionError(
            f"section points must be a sequence of (distance, z) pairs: {exc}"
        ) from exc
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise InvalidSectionError(
            f"section points must be (distance, z) pairs, got array of shape {pts.shape}"
        )
    if len(pts) < 3:
        raise InvalidSectionError(f"section needs at least 3 points, got {len(pts)}")
    if not np.all(np.isfinite(pts)):
        raise InvalidSectionError("section contains non-finite values (NaN or inf)")
    steps = np.diff(pts[:, 0])
    bad = np.flatnonzero(steps <= 0)
    if bad.size:
        k = int(bad[0])
        raise InvalidSectionError(
            "section distances must be strictly increasing: "
            f"point {k + 1} (distance {pts[k + 1, 0]!r}) follows "
            f"point {k} (distance {pts[k, 0]!r})"
        )
    z = pts[:, 1]
    relief = z.max() - z.min()
    if relief == 0:
        raise InvalidSectionError(f"all section elevations are equal ({z[0]!r})")
    if relief <= 2 * _LEVEL_OFFSET:
        raise InvalidSectionError(
            f"section relief ({relief:.3f} m) must exceed {2 * _LEVEL_OFFSET} m: "
            "levels go from min z + 0.1 to max z - 0.1"
        )
    return pts


def _polygon_parts(geom):
    """Polygonal parts of an intersection result (Polygon, Multi or collection)."""
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        return [p for g in geom.geoms for p in _polygon_parts(g)]
    return []


def _thalweg_polygon(parts, min_z):
    """Wet polygon containing the lowest point of the section.

    If the lowest elevation occurs in more than one polygon, the first one
    (in Shapely's part order) is returned.
    """
    for p in parts:
        if p.bounds[1] == min_z:
            return p
    # Not expected: the lowest point is always wet. Fall back to the lowest part.
    return min(parts, key=lambda p: p.bounds[1])
