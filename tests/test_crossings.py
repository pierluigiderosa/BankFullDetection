"""Tests for the crossing checks of bankfull_core.sections."""

import dataclasses
import math

import numpy as np
import pytest
from shapely.geometry import LineString

from bankfull_core.sections import (
    Crossing,
    crossing_flags,
    crossings_inside_banks,
    drop_crossing_sections,
    find_crossings,
    generate_sections,
)

# A horizontal and a vertical line crossing at (50, 0): 50 m along each.
H = [(0, 0), (100, 0)]
V = [(50, -50), (50, 50)]
FAR = [(500, -50), (500, 50)]


def _semicircle(radius, n=400):
    t = np.linspace(math.pi, 0, n)  # clockwise half circle, centre (0, 0)
    return LineString(np.column_stack([radius * np.cos(t), radius * np.sin(t)]))


# --- find_crossings ------------------------------------------------------------------

def test_parallel_sections_do_not_cross():
    lines = [[(x, -10), (x, 10)] for x in range(0, 100, 10)]
    assert find_crossings(lines) == ()


def test_single_crossing():
    (c,) = find_crossings([H, V, FAR])
    assert (c.first, c.second) == (0, 1)
    assert c.points == ((50.0, 0.0),)


def test_crossing_indices_sorted_and_first_lower():
    lines = [FAR, V, H, [(20, -5), (20, 5)]]  # H crosses V and the short line
    crossings = find_crossings(lines)
    assert [(c.first, c.second) for c in crossings] == [(1, 2), (2, 3)]


def test_polyline_crossing_twice_reports_both_points():
    zigzag = [(0, -10), (30, 10), (60, -10)]
    (c,) = find_crossings([H, zigzag])
    assert sorted(c.points) == [(15.0, 0.0), (45.0, 0.0)]


def test_collinear_overlap_is_a_crossing():
    (c,) = find_crossings([H, [(80, 0), (150, 0)]])
    assert sorted(c.points) == [(80.0, 0.0), (100.0, 0.0)]


def test_accepts_linestrings_and_sections():
    secs = generate_sections(LineString([(0, 0), (100, 0)]), step=50, width=20)
    assert find_crossings(secs) == ()
    assert find_crossings([LineString(H), LineString(V)])[0].points == ((50.0, 0.0),)


def test_crossing_is_frozen():
    (c,) = find_crossings([H, V])
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.first = 3


def test_tight_bend_sections_cross_only_when_wider_than_radius():
    axis = _semicircle(100.0)
    narrow = generate_sections(axis, step=20, width=150)  # 75 m per side < radius
    wide = generate_sections(axis, step=20, width=300)    # 150 m per side > radius
    assert find_crossings(narrow) == ()
    crossings = find_crossings(wide)
    assert crossings
    # Sections cross on the inner side of the bend (towards the centre), beyond the axis.
    for c in crossings:
        for x, y in c.points:
            assert math.hypot(x, y) < 100.0


# --- crossing_flags ------------------------------------------------------------------

def test_crossing_flags():
    lines = [H, V, FAR]
    assert crossing_flags(len(lines), find_crossings(lines)) == (True, True, False)
    assert crossing_flags(2, ()) == (False, False)


def test_crossing_flags_index_out_of_range():
    with pytest.raises(ValueError, match="out of range"):
        crossing_flags(1, find_crossings([H, V]))


# --- drop_crossing_sections ----------------------------------------------------------

def test_drop_greedy_in_input_order():
    a = [(0, 0), (100, 0)]
    b = [(50, -50), (50, 50)]       # crosses a
    c = [(0, 40), (100, 40)]        # crosses b only
    kept, dropped = drop_crossing_sections([a, b, c])
    assert kept == (0, 2)
    assert dropped == (1,)


def test_drop_keeps_the_earlier_section():
    kept, dropped = drop_crossing_sections([V, H])
    assert kept == (0,) and dropped == (1,)


def test_drop_without_crossings_keeps_everything():
    kept, dropped = drop_crossing_sections([H, FAR])
    assert kept == (0, 1) and dropped == ()


def test_drop_result_has_no_crossings():
    secs = generate_sections(_semicircle(100.0), step=20, width=300)
    kept, dropped = drop_crossing_sections(secs)
    assert dropped
    assert find_crossings([secs[i] for i in kept]) == ()
    assert sorted(kept + dropped) == list(range(len(secs)))


# --- crossings_inside_banks ----------------------------------------------------------

def test_crossing_inside_banks_of_one_section_flags_both():
    lines = [H, V, FAR]
    crossings = find_crossings(lines)
    flags = crossings_inside_banks(lines, crossings, [(40, 60), (0, 10), (0, 10)])
    assert flags == (True, True, False)


def test_crossing_outside_both_banks():
    lines = [H, V]
    flags = crossings_inside_banks(lines, find_crossings(lines), [(0, 10), (60, 100)])
    assert flags == (False, False)


def test_section_without_bankfull_uses_the_other():
    lines = [H, V]
    crossings = find_crossings(lines)
    assert crossings_inside_banks(lines, crossings, [None, (45, 55)]) == (True, True)
    assert crossings_inside_banks(lines, crossings, [None, None]) == (False, False)


def test_bank_interval_is_closed():
    lines = [H, V]
    flags = crossings_inside_banks(lines, find_crossings(lines), [(10, 50), None])
    assert flags == (True, True)


def test_any_of_several_points_inside():
    zigzag = [(0, -10), (30, 10), (60, -10)]
    lines = [H, zigzag]
    crossings = find_crossings(lines)
    # Points at 15 and 45 m along H: only the second is inside (40, 50).
    assert crossings_inside_banks(lines, crossings, [(40, 50), None]) == (True, True)
    assert crossings_inside_banks(lines, crossings, [(20, 40), None]) == (False, False)


def test_distance_measured_from_first_vertex_of_polyline():
    bent = [(0, 0), (40, 0), (40, 100)]   # 40 m then north
    cross = [(20, 50), (60, 50)]          # crosses at (40, 50): 90 m along bent
    lines = [bent, cross]
    crossings = find_crossings(lines)
    assert crossings_inside_banks(lines, crossings, [(85, 95), None]) == (True, True)
    assert crossings_inside_banks(lines, crossings, [(0, 45), None]) == (False, False)


def test_inside_banks_validation():
    lines = [H, V]
    crossings = find_crossings(lines)
    with pytest.raises(ValueError, match="bank_intervals"):
        crossings_inside_banks(lines, crossings, [(0, 10)])
    with pytest.raises(ValueError, match="left"):
        crossings_inside_banks(lines, crossings, [(60, 40), None])
    with pytest.raises(ValueError, match="finite"):
        crossings_inside_banks(lines, crossings, [(0, math.nan), None])
    with pytest.raises(ValueError, match="out of range"):
        crossings_inside_banks([H], crossings, [None])


# --- invalid lines -------------------------------------------------------------------

@pytest.mark.parametrize("bad", [[(0, 0)], [], [(0, 0), (0, 0)], "x", LineString()])
def test_invalid_section_line(bad):
    with pytest.raises(ValueError, match="section 1"):
        find_crossings([H, bad])
    with pytest.raises(ValueError, match="section 1"):
        drop_crossing_sections([H, bad])


def test_crossing_type():
    (c,) = find_crossings([H, V])
    assert isinstance(c, Crossing)
    assert all(isinstance(v, float) for p in c.points for v in p)
