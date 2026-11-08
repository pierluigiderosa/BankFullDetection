"""Tests for bankfull_core.sections.generate_sections (cross-sections along a river axis)."""

import dataclasses
import math

import numpy as np
import pytest
from shapely.geometry import LineString, MultiLineString, Point

from bankfull_core.sections import Section, generate_sections


def _length(sec):
    (xl, yl), (xr, yr) = sec.coords
    return math.hypot(xr - xl, yr - yl)


def _section_dir(sec):
    """Unit vector from the left to the right end of the section."""
    (xl, yl), (xr, yr) = sec.coords
    v = np.array([xr - xl, yr - yl])
    return v / np.linalg.norm(v)


def _tangent(sec):
    """Unit vector of the axis tangent from the azimuth (clockwise from north)."""
    a = math.radians(sec.azimuth)
    return np.array([math.sin(a), math.cos(a)])


# --- straight axis -------------------------------------------------------------------

def test_straight_axis_positions_and_geometry():
    secs = generate_sections(LineString([(0, 0), (1000, 0)]), step=100, width=50)
    assert len(secs) == 10
    assert [s.index for s in secs] == list(range(10))
    assert all(s.part == 0 for s in secs)
    np.testing.assert_allclose([s.chainage for s in secs], np.arange(50, 1000, 100))
    for s in secs:
        assert s.center == pytest.approx((s.chainage, 0.0))
        # Looking along the axis (east), left is north.
        assert s.coords[0] == pytest.approx((s.chainage, 25.0))
        assert s.coords[1] == pytest.approx((s.chainage, -25.0))
        assert _length(s) == pytest.approx(50.0)
        assert s.azimuth == pytest.approx(90.0)


def test_width_is_total_length_half_per_side():
    (s, *_) = generate_sections(LineString([(0, 0), (1000, 0)]), step=100, width=500)
    assert _length(s) == pytest.approx(500.0)
    cx, cy = s.center
    for x, y in s.coords:
        assert math.hypot(x - cx, y - cy) == pytest.approx(250.0)


def test_offset_zero_includes_both_ends():
    secs = generate_sections(LineString([(0, 0), (1000, 0)]), step=100, width=50, offset=0)
    np.testing.assert_allclose([s.chainage for s in secs], np.arange(0, 1001, 100))


def test_custom_offset():
    secs = generate_sections(LineString([(0, 0), (1000, 0)]), step=300, width=50, offset=100)
    np.testing.assert_allclose([s.chainage for s in secs], [100, 400, 700, 1000])


def test_northward_axis_left_is_west():
    (s, *_) = generate_sections(LineString([(0, 0), (0, 500)]), step=100, width=40)
    assert s.coords[0] == pytest.approx((-20.0, 50.0))
    assert s.coords[1] == pytest.approx((20.0, 50.0))
    assert s.azimuth == pytest.approx(0.0)


def test_reversed_axis_swaps_left_and_right():
    fwd = generate_sections(LineString([(0, 0), (1000, 0)]), step=100, width=50)
    rev = generate_sections(LineString([(1000, 0), (0, 0)]), step=100, width=50)
    by_x = {round(s.center[0], 6): s for s in rev}
    for s in fwd:
        r = by_x[round(s.center[0], 6)]
        assert r.coords[0] == pytest.approx(s.coords[1])
        assert r.coords[1] == pytest.approx(s.coords[0])


def test_sections_are_perpendicular_to_straight_axis():
    axis = LineString([(10, 20), (310, 420)])  # azimuth atan2(3, 4)
    for s in generate_sections(axis, step=50, width=100):
        assert abs(float(np.dot(_section_dir(s), _tangent(s)))) < 1e-12
        assert s.azimuth == pytest.approx(math.degrees(math.atan2(3, 4)))


# --- bends and tangent ---------------------------------------------------------------

def test_tangent_averaged_across_vertex():
    axis = LineString([(0, 0), (100, 0), (100, 100)])
    secs = generate_sections(axis, step=100, width=20, offset=100)
    s = secs[0]
    assert s.chainage == pytest.approx(100.0)
    # Window 100 m: from (50, 0) to (100, 50) -> direction (1, 1), azimuth 45.
    assert s.azimuth == pytest.approx(45.0)
    assert abs(float(np.dot(_section_dir(s), _tangent(s)))) < 1e-12
    # Left of a north-east direction is north-west.
    assert s.coords[0][0] < s.center[0] and s.coords[0][1] > s.center[1]


def test_azimuth_changes_gradually_around_vertex():
    axis = LineString([(0, 0), (200, 0), (200, 200)])
    secs = generate_sections(axis, step=10, width=20, tangent_length=60)
    az = np.array([s.azimuth for s in secs])
    # The 90-degree turn is spread over the sections within the window (about 19 degrees
    # at most between neighbours here), never a single jump, and is monotonic.
    assert np.max(np.abs(np.diff(az))) < 20.0
    assert np.all(np.diff(az) <= 1e-9)
    assert az[0] == pytest.approx(90.0) and az[-1] == pytest.approx(0.0)


def test_tangent_window_clamped_at_ends():
    axis = LineString([(0, 0), (100, 0), (100, 100)])
    s = generate_sections(axis, step=100, width=20, offset=0)[0]
    # At chainage 0 the window is [0, 50]: still along the first segment.
    assert s.azimuth == pytest.approx(90.0)


def test_jagged_axis_gives_stable_azimuth():
    x = np.arange(0, 1001, 1.0)
    y = np.where(np.arange(x.size) % 2 == 0, 1.0, -1.0)
    secs = generate_sections(LineString(np.column_stack([x, y])), step=50, width=100)
    az = np.array([s.azimuth for s in secs])
    # The per-segment direction would swing by +-63 degrees; the 50 m window by < 3.
    assert np.max(np.abs(az - 90.0)) < 3.0


def test_default_tangent_length_is_step():
    axis = LineString([(0, 0), (100, 0), (100, 100)])
    a = generate_sections(axis, step=80, width=20, offset=100)
    b = generate_sections(axis, step=80, width=20, offset=100, tangent_length=80)
    assert a == b


# --- multi-part axes -----------------------------------------------------------------

def test_contiguous_multi_is_merged():
    axis = MultiLineString([[(500, 0), (1000, 0)], [(0, 0), (500, 0)]])
    secs = generate_sections(axis, step=100, width=50)
    assert {s.part for s in secs} == {0}
    np.testing.assert_allclose([s.chainage for s in secs], np.arange(50, 1000, 100))
    np.testing.assert_allclose([s.center[0] for s in secs], np.arange(50, 1000, 100))


def test_disjoint_multi_gives_separate_parts_in_input_order():
    axis = MultiLineString([[(0, 0), (300, 0)], [(1000, 0), (1500, 0)]])
    secs = generate_sections(axis, step=100, width=50)
    assert [s.part for s in secs] == [0] * 3 + [1] * 5
    assert [s.index for s in secs] == list(range(8))
    np.testing.assert_allclose([s.chainage for s in secs],
                               [50, 150, 250, 50, 150, 250, 350, 450])
    assert secs[3].center == pytest.approx((1050.0, 0.0))


def test_part_order_follows_input_not_geometry():
    axis = MultiLineString([[(1000, 0), (1500, 0)], [(0, 0), (300, 0)]])
    secs = generate_sections(axis, step=100, width=50)
    assert secs[0].part == 0 and secs[0].center[0] == pytest.approx(1050.0)
    assert secs[-1].part == 1 and secs[-1].center[0] == pytest.approx(250.0)


def test_contiguous_parts_with_opposite_direction_are_not_merged():
    # Merging them would reverse one part and swap its left and right.
    axis = MultiLineString([[(0, 0), (500, 0)], [(1000, 0), (500, 0)]])
    secs = generate_sections(axis, step=100, width=50)
    assert {s.part for s in secs} == {0, 1}
    second = [s for s in secs if s.part == 1]
    assert second[0].center == pytest.approx((950.0, 0.0))
    assert second[0].azimuth == pytest.approx(270.0)


def test_part_shorter_than_step_gives_one_section_at_midpoint():
    secs = generate_sections(LineString([(0, 0), (30, 0)]), step=100, width=50)
    assert len(secs) == 1
    assert secs[0].chainage == pytest.approx(15.0)
    assert secs[0].center == pytest.approx((15.0, 0.0))


def test_offset_beyond_part_end_gives_one_section_at_midpoint():
    axis = MultiLineString([[(0, 0), (1000, 0)], [(2000, 0), (2150, 0)]])
    secs = generate_sections(axis, step=100, width=50, offset=200)
    second = [s for s in secs if s.part == 1]
    assert [s.chainage for s in second] == pytest.approx([75.0])


# --- input forms ---------------------------------------------------------------------

def test_coordinate_sequence_equals_linestring():
    coords = [(0, 0), (400, 0), (400, 300)]
    assert generate_sections(coords, 100, 50) == generate_sections(LineString(coords), 100, 50)


def test_z_coordinates_are_ignored():
    a = generate_sections(LineString([(0, 0, 5), (1000, 0, 9)]), step=100, width=50)
    b = generate_sections(LineString([(0, 0), (1000, 0)]), step=100, width=50)
    assert a == b


def test_input_not_modified():
    coords = [[0.0, 0.0], [400.0, 0.0], [400.0, 300.0]]
    copy = [list(p) for p in coords]
    generate_sections(coords, 100, 50)
    assert coords == copy


def test_result_types():
    secs = generate_sections(LineString([(0, 0), (1000, 0)]), step=100, width=50)
    assert isinstance(secs, tuple)
    s = secs[0]
    assert isinstance(s, Section)
    assert all(isinstance(v, float) for v in (*s.center, *s.coords[0], *s.coords[1]))
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.chainage = 1.0


# --- invalid input -------------------------------------------------------------------

AXIS = LineString([(0, 0), (1000, 0)])


@pytest.mark.parametrize("step", [0, -1, math.nan, math.inf, True, "10"])
def test_invalid_step(step):
    with pytest.raises(ValueError, match="step"):
        generate_sections(AXIS, step=step, width=50)


@pytest.mark.parametrize("width", [0, -5, math.nan, math.inf, False])
def test_invalid_width(width):
    with pytest.raises(ValueError, match="width"):
        generate_sections(AXIS, step=100, width=width)


@pytest.mark.parametrize("offset", [-1, math.nan, math.inf])
def test_invalid_offset(offset):
    with pytest.raises(ValueError, match="offset"):
        generate_sections(AXIS, step=100, width=50, offset=offset)


@pytest.mark.parametrize("tl", [0, -10, math.nan])
def test_invalid_tangent_length(tl):
    with pytest.raises(ValueError, match="tangent_length"):
        generate_sections(AXIS, step=100, width=50, tangent_length=tl)


@pytest.mark.parametrize("axis", [
    LineString(),
    MultiLineString(),
    LineString([(0, 0), (0, 0)]),
    MultiLineString([[(0, 0), (100, 0)], [(5, 5), (5, 5)]]),
    Point(0, 0),
    [(0, 0)],
    [],
    "not an axis",
])
def test_invalid_axis(axis):
    with pytest.raises(ValueError, match="axis"):
        generate_sections(axis, step=100, width=50)
