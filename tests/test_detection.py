"""Tests of bankfull_core.detection (channel geometry from the bankfull level)."""

import copy
import dataclasses
import math

import numpy as np
import pytest
from conftest import read_golden_bankfull
from numpy.testing import assert_allclose, assert_array_equal
from shapely.geometry import LineString, Point

from bankfull_core import (
    STATUS_NO_MAXIMA,
    STATUS_OK,
    BankfullDetection,
    BankfullLevel,
    BankfullOptions,
    BankGeometry,
    ChannelPolygon,
    bank_geometry,
    channel_polygon,
    compute_bankfull_level,
    detect_bankfull,
)
from bankfull_core.detection import _map_point

# Trapezoid: bottom 12-22 at z = 0, side slopes 2H:1V, bank tops at z = 3.
TRAPEZOID = [(0, 3), (6, 3), (12, 0), (22, 0), (28, 3), (34, 3)]

# Two depressions: a wide shallow one (left) and a narrow deep one (right).
# At z = 1.0 the left polygon (area 7) is larger than the right one (area 4), but the
# lowest point of the section (z = -1 at d = 22) is in the right one.
TWO_DEPRESSIONS = [(0, 2), (2, 1), (4, 0), (10, 0), (12, 1), (14, 2),
                   (20, 1), (22, -1), (24, 1), (26, 2)]

# Water at z = 1.5 reaches the left end of the section (z = 1 there).
LEFT_EDGE = [(0, 1), (5, 0), (10, 3)]
RIGHT_EDGE = [(0, 3), (5, 0), (10, 1)]

GOLDEN_BANKFULL = {k: r for k, r in read_golden_bankfull().items() if not r["error"]}
PARABOLA = ("synthetic.csv", 4)


# --- bank_geometry -----------------------------------------------------------------------

def test_trapezoid_analytic():
    g = bank_geometry(TRAPEZOID, 2.0)
    assert isinstance(g, BankGeometry)
    assert g.level == 2.0
    assert g.left == pytest.approx(8.0, abs=1e-12)
    assert g.right == pytest.approx(26.0, abs=1e-12)
    assert g.width == pytest.approx(18.0, abs=1e-12)
    assert g.area == pytest.approx(10 * 2 + 2 * 2**2, abs=1e-12)
    assert g.mean_depth == pytest.approx(28 / 18, abs=1e-12)
    assert g.max_depth == pytest.approx(2.0, abs=1e-12)
    assert g.n_wet_polygons == 1
    assert not g.touches_left_edge and not g.touches_right_edge
    assert g.wet_polygon.geom_type == "Polygon"
    assert g.wet_polygon.area == pytest.approx(g.area)
    assert g.wet_polygon.bounds == pytest.approx((8.0, 0.0, 26.0, 2.0))


@pytest.mark.parametrize("mode", ["original", "thalweg"])
def test_two_depressions_choose_lowest_point(mode):
    g = bank_geometry(TWO_DEPRESSIONS, 1.0, BankfullOptions(multichannel=mode))
    assert g.n_wet_polygons == 2
    # Narrow deep depression (right), not the larger shallow one.
    assert g.left == pytest.approx(20.0, abs=1e-12)
    assert g.right == pytest.approx(24.0, abs=1e-12)
    assert g.area == pytest.approx(4.0, abs=1e-12)
    assert g.max_depth == pytest.approx(2.0, abs=1e-12)
    assert g.wet_polygon.bounds[1] == -1.0


def test_edge_flags():
    g = bank_geometry(LEFT_EDGE, 1.5)
    assert g.touches_left_edge and not g.touches_right_edge
    assert g.left == 0.0
    g = bank_geometry(RIGHT_EDGE, 1.5)
    assert g.touches_right_edge and not g.touches_left_edge
    assert g.right == 10.0


@pytest.mark.parametrize("level", [0.0, -1.0, 3.01, math.nan, math.inf])
def test_level_out_of_section(level):
    with pytest.raises(ValueError, match="level"):
        bank_geometry(TRAPEZOID, level)


def test_level_at_section_top():
    """At the bank-top elevation the water stops at the first point at that elevation."""
    g = bank_geometry(TRAPEZOID, 3.0)
    assert (g.left, g.right) == pytest.approx((6.0, 28.0), abs=1e-12)
    assert not g.touches_left_edge and not g.touches_right_edge


def test_input_not_modified():
    pts = list(TWO_DEPRESSIONS)
    before = copy.deepcopy(pts)
    bank_geometry(pts, 1.0)
    assert pts == before
    arr = np.array(TWO_DEPRESSIONS, dtype=float)
    arr_before = arr.copy()
    bank_geometry(arr, 1.0)
    assert_array_equal(arr, arr_before)


def test_geometry_is_frozen():
    g = bank_geometry(TRAPEZOID, 2.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        g.left = 0.0


@pytest.mark.parametrize("key", sorted(GOLDEN_BANKFULL), ids=str)
def test_golden_banks(all_sections, key):
    """Banks and number of wet polygons at the golden bankfull level (original mainFun)."""
    row = GOLDEN_BANKFULL[key]
    g = bank_geometry(all_sections[key[:2]], float(row["bankfull_z"]), BankfullOptions())
    assert_allclose(g.left, float(row["left_dist"]), rtol=1e-12)
    assert_allclose(g.right, float(row["right_dist"]), rtol=1e-12)
    assert g.n_wet_polygons == int(row["n_channels"])


# --- detect_bankfull ---------------------------------------------------------------------

def test_detect_matches_level_and_geometry(all_sections):
    pts = all_sections[("arno.csv", 1)]
    res = detect_bankfull(pts)
    assert isinstance(res, BankfullDetection)
    assert isinstance(res.level, BankfullLevel)
    assert res.status == STATUS_OK
    assert res.level == compute_bankfull_level(pts)
    assert res.geometry == bank_geometry(pts, res.level.level)
    assert res.left_xy is None and res.right_xy is None


def test_detect_without_bankfull(all_sections):
    res = detect_bankfull(all_sections[PARABOLA], line_coords=[(0, 0), (80, 0)])
    assert res.status == STATUS_NO_MAXIMA
    assert res.level.level is None
    assert res.geometry is None
    assert res.left_xy is None and res.right_xy is None


def test_detect_is_frozen(all_sections):
    res = detect_bankfull(all_sections[("arno.csv", 1)])
    with pytest.raises(dataclasses.FrozenInstanceError):
        res.geometry = None


@pytest.mark.parametrize(
    "line_coords",
    [
        [(1000.0, 2000.0), (1000.0 + 60 * 0.6, 2000.0 + 60 * 0.8)],          # straight, oblique
        [(0.0, 0.0), (15.0, 0.0), (15.0, 30.0), (40.0, 30.0)],               # polyline
    ],
    ids=["straight", "polyline"],
)
def test_map_coordinates_on_line(synthetic, line_coords):
    pts = synthetic[2]  # inner bench, bankfull with default options
    res = detect_bankfull(pts, line_coords=line_coords)
    assert res.status == STATUS_OK
    line = LineString(line_coords)
    for xy, d in ((res.left_xy, res.geometry.left), (res.right_xy, res.geometry.right)):
        p = Point(xy)
        assert line.distance(p) < 1e-9
        assert line.project(p) == pytest.approx(d, abs=1e-9)


def test_map_coordinates_polyline_explicit():
    """Banks 8 and 26 on an L line: first leg 10 m along x, then along y."""
    line = LineString([(0.0, 0.0), (10.0, 0.0), (10.0, 30.0)])
    g = bank_geometry(TRAPEZOID, 2.0)
    assert _map_point(line, g.left) == pytest.approx((8.0, 0.0))
    assert _map_point(line, g.right) == pytest.approx((10.0, 16.0))


def test_map_coordinates_line_too_short(synthetic):
    with pytest.raises(ValueError, match="line"):
        detect_bankfull(synthetic[2], line_coords=[(0, 0), (40, 0)])


@pytest.mark.parametrize("line_coords", [[(0, 0)], [(5, 5), (5, 5)]])
def test_map_coordinates_bad_line(synthetic, line_coords):
    with pytest.raises(ValueError, match="line"):
        detect_bankfull(synthetic[2], line_coords=line_coords)


# --- channel_polygon ---------------------------------------------------------------------

LEFTS = [(2.0, 0.0), (1.0, 10.0), (3.0, 20.0)]
RIGHTS = [(8.0, 0.0), (9.0, 10.0), (7.0, 20.0)]


def test_channel_polygon_three_sections():
    res = channel_polygon(LEFTS, RIGHTS)
    assert isinstance(res, ChannelPolygon)
    assert res.is_valid and res.invalid_reason is None
    assert res.polygon.is_valid
    # (6 + 8) / 2 * 10 + (8 + 4) / 2 * 10
    assert res.polygon.area == pytest.approx(130.0)
    assert res.used == (0, 1, 2)
    assert res.skipped == ()


def test_channel_polygon_skips_missing_section():
    lefts = [LEFTS[0], None, LEFTS[2]]
    rights = [RIGHTS[0], RIGHTS[1], RIGHTS[2]]
    res = channel_polygon(lefts, rights)
    assert res.skipped == (1,)
    assert res.used == (0, 2)
    assert res.is_valid
    # (6 + 4) / 2 * 20
    assert res.polygon.area == pytest.approx(100.0)


def test_channel_polygon_crossing_sections():
    """Banks swapped in the middle section: the outline crosses itself."""
    lefts = [LEFTS[0], RIGHTS[1], LEFTS[2]]
    rights = [RIGHTS[0], LEFTS[1], RIGHTS[2]]
    res = channel_polygon(lefts, rights)
    assert not res.is_valid
    assert "Self-intersection" in res.invalid_reason
    assert not res.polygon.is_valid  # returned as built, not repaired


def test_channel_polygon_too_few_sections():
    with pytest.raises(ValueError, match="at least 2"):
        channel_polygon([LEFTS[0], None], [RIGHTS[0], RIGHTS[1]])


def test_channel_polygon_length_mismatch():
    with pytest.raises(ValueError, match="same length"):
        channel_polygon(LEFTS, RIGHTS[:2])


# --- Arno with the recommended options ---------------------------------------------------

@pytest.fixture(scope="module")
def arno_recommended(all_sections):
    opts = BankfullOptions.recommended()
    return {k: (pts, detect_bankfull(pts, opts))
            for k, pts in all_sections.items() if k[0] == "arno.csv"}


def test_arno_recommended_banks_inside(arno_recommended):
    assert len(arno_recommended) == 8
    for key, (pts, res) in arno_recommended.items():
        d = [p[0] for p in pts]
        g = res.geometry
        assert res.status == STATUS_OK, key
        assert min(d) < g.left < g.right < max(d), key
        assert not g.touches_left_edge and not g.touches_right_edge, key
        assert g.level == res.level.level
