"""Channel geometry at the bankfull level.

From the bankfull level of a cross-section (``level.compute_bankfull_level``) this module
derives the banks, width, area and depths of the channel, optionally the bank points in map
coordinates, and the channel polygon built from several sections.
See ``docs/detection.md``.
"""

import math
from dataclasses import dataclass

from shapely.geometry import LineString, Polygon, box
from shapely.validation import explain_validity

from .hydraulics import (
    _TOP_EXTENSION,
    _polygon_parts,
    _thalweg_polygon,
    _validate_points,
)
from .level import BankfullLevel, compute_bankfull_level
from .options import BankfullOptions

# Tolerance [section distance units] for the flags touches_left_edge / touches_right_edge.
_EDGE_TOL = 1e-9

# Tolerance [map units] for bank distances beyond the ends of the section line. Section
# distances are usually rounded (1 mm in golden_tools/export_sections_qgis.py), so the last
# distance can slightly exceed the line length.
_LINE_TOL = 1e-3


@dataclass(frozen=True)
class BankGeometry:
    """Channel geometry at a water level (result of ``bank_geometry``).

    Attributes:
        level: water level [m].
        left, right: section distance of the left and right bank [m] (ends of the chosen
            wet polygon).
        width: ``right - left`` [m].
        area: area of the chosen wet polygon [m2].
        mean_depth: ``area / width`` [m].
        max_depth: ``level - min z`` of the section [m].
        n_wet_polygons: number of disjoint wet polygons in the section at the level.
        touches_left_edge, touches_right_edge: the chosen wet polygon reaches the first /
            last point of the section: the bank on that side is not inside the section.
        wet_polygon: chosen wet polygon (Shapely) in section coordinates (distance, z).
    """

    level: float
    left: float
    right: float
    width: float
    area: float
    mean_depth: float
    max_depth: float
    n_wet_polygons: int
    touches_left_edge: bool
    touches_right_edge: bool
    wet_polygon: Polygon


@dataclass(frozen=True)
class BankfullDetection:
    """Result of ``detect_bankfull``.

    Attributes:
        level: BankfullLevel of ``compute_bankfull_level``.
        geometry: BankGeometry at ``level.level``, or None if there is no bankfull level.
        left_xy, right_xy: map coordinates (x, y) of the banks, or None if no section line
            was given or there is no bankfull level.
    """

    level: BankfullLevel
    geometry: BankGeometry | None
    left_xy: tuple | None
    right_xy: tuple | None

    @property
    def status(self):
        """Status of the bankfull level (``STATUS_OK`` if a level was found)."""
        return self.level.status


@dataclass(frozen=True)
class ChannelPolygon:
    """Result of ``channel_polygon``.

    Attributes:
        polygon: Shapely polygon of the channel, as built (never repaired).
        used: indices of the sections used, in input order.
        skipped: indices of the sections skipped because a bank is missing.
        is_valid: ``polygon.is_valid``.
        invalid_reason: ``shapely.validation.explain_validity`` if not valid, else None.
    """

    polygon: Polygon
    used: tuple
    skipped: tuple
    is_valid: bool
    invalid_reason: str | None


def bank_geometry(points, level, options=None):
    """Channel geometry of a section at a water level.

    The wet polygons are built as in ``hydraulics.hydraulic_curve``. The chosen polygon is
    the one containing the lowest point of the section, whatever ``options.multichannel``
    (if the lowest elevation occurs in more than one polygon, the first in Shapely's order).

    Args:
        points: sequence of (distance, z) pairs, distances strictly increasing.
            It is never modified.
        level: water level [m], with ``min z < level <= max z``.
        options: BankfullOptions; accepted for a uniform signature, the geometry does not
            depend on it.

    Returns:
        BankGeometry.

    Raises:
        InvalidSectionError: if the section is not valid.
        ValueError: if the level is not finite or outside ``(min z, max z]``.
    """
    if options is None:
        options = BankfullOptions()
    pts = _validate_points(points)
    pts_list = [(float(d), float(z)) for d, z in pts]
    minx, maxx = pts_list[0][0], pts_list[-1][0]
    min_z = float(pts[:, 1].min())
    max_z = float(pts[:, 1].max())
    level = float(level)
    if not math.isfinite(level):
        raise ValueError(f"level must be finite, got {level!r}")
    if not min_z < level <= max_z:
        raise ValueError(
            f"level {level!r} must be above the section minimum ({min_z!r}) "
            f"and not above its maximum ({max_z!r})"
        )

    top = max_z + _TOP_EXTENSION
    polygon_xs = Polygon([(minx, top), *pts_list, (maxx, top)])
    parts = _polygon_parts(polygon_xs.intersection(box(minx, min_z, maxx, level)))
    wet = _thalweg_polygon(parts, min_z)

    left, _, right, _ = wet.bounds
    width = right - left
    area = wet.area
    return BankGeometry(
        level=level,
        left=left,
        right=right,
        width=width,
        area=area,
        mean_depth=area / width,
        max_depth=level - min_z,
        n_wet_polygons=len(parts),
        touches_left_edge=left - minx <= _EDGE_TOL,
        touches_right_edge=maxx - right <= _EDGE_TOL,
        wet_polygon=wet,
    )


def detect_bankfull(points, options=None, line_coords=None):
    """Bankfull level and channel geometry of a section.

    Args:
        points: sequence of (distance, z) pairs, distances strictly increasing.
        options: BankfullOptions (defaults if None).
        line_coords: optional (x, y) coordinates of the section line, from the first to the
            last point of the section; a section distance is the distance along this line.

    Returns:
        BankfullDetection. Without a bankfull level, ``geometry``, ``left_xy`` and
        ``right_xy`` are None and ``status`` tells why.

    Raises:
        InvalidSectionError: if the section is not valid.
        ValueError: if the line is degenerate or shorter than the bank distances.
    """
    if options is None:
        options = BankfullOptions()
    line = _section_line(line_coords) if line_coords is not None else None
    lev = compute_bankfull_level(points, options)
    if lev.level is None:
        return BankfullDetection(level=lev, geometry=None, left_xy=None, right_xy=None)
    geom = bank_geometry(points, lev.level, options)
    left_xy = right_xy = None
    if line is not None:
        left_xy = _map_point(line, geom.left)
        right_xy = _map_point(line, geom.right)
    return BankfullDetection(level=lev, geometry=geom, left_xy=left_xy, right_xy=right_xy)


def channel_polygon(left_points, right_points):
    """Channel polygon from the bank points of consecutive sections.

    The outline joins the left banks in order, then the right banks in reverse order.
    Sections must be ordered along the river and all drawn in the same direction,
    otherwise the outline can cross itself: the polygon is returned as built, with
    ``is_valid`` False and the reason.

    Args:
        left_points, right_points: sequences of the same length with the (x, y) map
            coordinates of the left and right bank of each section, or None for a section
            without bankfull (it is skipped if either bank is None).

    Returns:
        ChannelPolygon.

    Raises:
        ValueError: if the sequences differ in length or fewer than 2 sections have both banks.
    """
    lefts = list(left_points)
    rights = list(right_points)
    if len(lefts) != len(rights):
        raise ValueError(
            "left_points and right_points must have the same length, "
            f"got {len(lefts)} and {len(rights)}"
        )
    used = tuple(i for i, (lp, rp) in enumerate(zip(lefts, rights, strict=True))
                 if lp is not None and rp is not None)
    skipped = tuple(i for i in range(len(lefts)) if i not in used)
    if len(used) < 2:
        raise ValueError(
            f"a channel polygon needs at least 2 sections with both banks, got {len(used)} "
            f"(skipped sections: {list(skipped)})"
        )
    outline = [_xy(lefts[i]) for i in used] + [_xy(rights[i]) for i in reversed(used)]
    polygon = Polygon(outline)
    valid = polygon.is_valid
    return ChannelPolygon(polygon=polygon, used=used, skipped=skipped, is_valid=valid,
                          invalid_reason=None if valid else explain_validity(polygon))


def _xy(p):
    x, y = p
    return float(x), float(y)


def _section_line(line_coords):
    """LineString of the section line, or ValueError if degenerate."""
    coords = [_xy(p) for p in line_coords]
    if len(coords) < 2:
        raise ValueError(f"section line needs at least 2 points, got {len(coords)}")
    line = LineString(coords)
    if line.length == 0:
        raise ValueError("section line has zero length")
    return line


def _map_point(line, distance, tol=_LINE_TOL):
    """(x, y) of the point at ``distance`` along ``line``.

    Distances up to ``tol`` beyond the ends are clamped; farther ones raise ValueError
    (Shapely would clamp them silently).
    """
    length = line.length
    if distance < -tol or distance > length + tol:
        raise ValueError(
            f"bank distance {distance!r} is outside the section line (length {length!r})"
        )
    p = line.interpolate(min(max(distance, 0.0), length))
    return p.x, p.y
