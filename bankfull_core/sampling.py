"""Sampling stations along a section line and NoData handling of the sampled profile.

The DTM itself is read in the QGIS layer; this module only decides where to sample and
how to treat missing values, so that both can be tested without QGIS.
See ``docs/sections.md``.
"""

import itertools
import math
from dataclasses import dataclass
from numbers import Real

import numpy as np


class NoDataError(ValueError):
    """The sampled section cannot be used because of NoData values.

    Attributes:
        n_interior: number of NoData values between the first and last valid value
            (0 if the section has fewer than 3 valid values in total).
    """

    def __init__(self, message, n_interior=0):
        super().__init__(message)
        self.n_interior = n_interior


@dataclass(frozen=True)
class SampledSection:
    """Result of ``trim_nodata``.

    Attributes:
        points: ((distance, z), ...) without NoData, distances still measured from the
            first vertex of the whole section line.
        n_trimmed_start, n_trimmed_end: NoData values removed at the start / end.
    """

    points: tuple
    n_trimmed_start: int
    n_trimmed_end: int


def stations(line_coords, spacing):
    """Sampling stations along a section line.

    Each segment is divided into ``ceil(length / spacing)`` equal parts and every vertex
    is kept, as ``QgsGeometry.densifyByDistance``. Repeated vertices are skipped so the
    distances are strictly increasing. Z values are ignored.

    Args:
        line_coords: (x, y) coordinates of the section line, at least 2 distinct points.
        spacing: maximum distance between stations [map units], > 0.

    Returns:
        (distances, xy): float arrays of shape (N,) and (N, 2); distances are the
        cumulative 2D distance from the first vertex.

    Raises:
        ValueError: on an invalid spacing or line.
    """
    if not isinstance(spacing, Real) or isinstance(spacing, bool) \
            or not math.isfinite(spacing) or spacing <= 0:
        raise ValueError(f"spacing must be a finite number > 0, got {spacing!r}")
    try:
        pts = np.array([tuple(p)[:2] for p in line_coords], dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"line must be a sequence of (x, y) coordinates: {exc}") from exc
    if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] != 2:
        raise ValueError(f"line needs at least 2 (x, y) points, got shape {pts.shape}")
    if not np.all(np.isfinite(pts)):
        raise ValueError("line contains non-finite coordinates")
    seg_len = np.hypot(*np.diff(pts, axis=0).T)
    keep = np.concatenate([[True], seg_len > 0])
    pts, seg_len = pts[keep], seg_len[seg_len > 0]
    if seg_len.size == 0:
        raise ValueError("line has zero length")

    xy = [pts[:1]]
    dist = [np.zeros(1)]
    start = 0.0
    for (p0, p1), length in zip(itertools.pairwise(pts), seg_len, strict=True):
        n = max(1, math.ceil(length / spacing))
        f = np.arange(1, n + 1) / n
        xy.append(p0 + np.outer(f, p1 - p0))
        dist.append(start + f * length)
        start += length
    return np.concatenate(dist), np.vstack(xy)


def trim_nodata(distances, z, valid):
    """Remove leading and trailing NoData from a sampled section.

    NoData at the ends (the section extends beyond the DTM) are removed. NoData between
    valid values are not interpolated: the section is rejected.

    Args:
        distances: station distances, as from ``stations``.
        z: sampled elevations; NaN counts as NoData.
        valid: per station, False if the sample is NoData.

    Returns:
        SampledSection.

    Raises:
        NoDataError: with interior NoData or fewer than 3 valid values.
        ValueError: if the inputs differ in length.
    """
    d = np.asarray(distances, dtype=float)
    zz = np.asarray(z, dtype=float)
    ok = np.asarray(valid, dtype=bool)
    if not d.shape == zz.shape == ok.shape or d.ndim != 1:
        raise ValueError(
            "distances, z and valid must be 1D with the same length, got shapes "
            f"{d.shape}, {zz.shape}, {ok.shape}"
        )
    ok = ok & np.isfinite(zz)
    idx = np.flatnonzero(ok)
    if idx.size == 0:
        raise NoDataError("section has no valid DTM values")
    first, last = int(idx[0]), int(idx[-1])
    n_interior = int((last - first + 1) - idx.size)
    if n_interior:
        raise NoDataError(f"section has {n_interior} interior NoData values",
                          n_interior=n_interior)
    if idx.size < 3:
        raise NoDataError(f"section has {idx.size} valid DTM values, at least 3 needed")
    points = tuple((float(a), float(b)) for a, b in zip(d[first:last + 1],
                                                         zz[first:last + 1], strict=True))
    return SampledSection(points=points, n_trimmed_start=first,
                          n_trimmed_end=int(d.size - 1 - last))