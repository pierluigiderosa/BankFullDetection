"""Tests for bankfull_core.sampling (stations along a section line, NoData trimming)."""

import dataclasses
import math

import numpy as np
import pytest

from bankfull_core import BankfullOptions, detect_bankfull, generate_sections
from bankfull_core.sampling import NoDataError, SampledSection, stations, trim_nodata

# --- stations ------------------------------------------------------------------------

def test_stations_straight_line_exact_multiple():
    d, xy = stations([(0, 0), (10, 0)], 2.5)
    np.testing.assert_allclose(d, [0, 2.5, 5, 7.5, 10])
    np.testing.assert_allclose(xy, [[0, 0], [2.5, 0], [5, 0], [7.5, 0], [10, 0]])


def test_stations_segment_split_in_equal_parts():
    # 10 m with spacing 3: ceil(10 / 3) = 4 equal parts of 2.5 m (as densifyByDistance).
    d, _ = stations([(0, 0), (10, 0)], 3.0)
    np.testing.assert_allclose(d, [0, 2.5, 5, 7.5, 10])


def test_stations_keep_vertices_and_cumulate_distance():
    d, xy = stations([(0, 0), (3, 0), (3, 4)], 2.0)
    # First segment 3 m -> 2 parts of 1.5; second 4 m -> 2 parts of 2.
    np.testing.assert_allclose(d, [0, 1.5, 3, 5, 7])
    np.testing.assert_allclose(xy, [[0, 0], [1.5, 0], [3, 0], [3, 2], [3, 4]])


def test_stations_spacing_larger_than_line():
    d, xy = stations([(0, 0), (1, 1)], 100.0)
    np.testing.assert_allclose(d, [0, math.sqrt(2)])
    assert xy.shape == (2, 2)


def test_stations_skip_duplicate_vertices():
    d, _ = stations([(0, 0), (2, 0), (2, 0), (4, 0)], 1.0)
    np.testing.assert_allclose(d, [0, 1, 2, 3, 4])
    assert np.all(np.diff(d) > 0)


def test_stations_ignore_z():
    d, xy = stations([(0, 0, 5), (4, 0, 9)], 2.0)
    np.testing.assert_allclose(d, [0, 2, 4])
    assert xy.shape == (3, 2)


def test_stations_input_not_modified():
    coords = [[0.0, 0.0], [10.0, 0.0]]
    stations(coords, 1.0)
    assert coords == [[0.0, 0.0], [10.0, 0.0]]


@pytest.mark.parametrize("spacing", [0, -1, math.nan, math.inf, True])
def test_stations_invalid_spacing(spacing):
    with pytest.raises(ValueError, match="spacing"):
        stations([(0, 0), (1, 0)], spacing)


@pytest.mark.parametrize("coords", [[], [(0, 0)], [(1, 1), (1, 1)], [(0, 0), (math.nan, 1)],
                                    "abc"])
def test_stations_invalid_line(coords):
    with pytest.raises(ValueError, match="line"):
        stations(coords, 1.0)


# --- trim_nodata ---------------------------------------------------------------------

D = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
Z = [5.0, 4.0, 3.0, 3.5, 4.5, 6.0]


def test_trim_nothing_to_trim():
    s = trim_nodata(D, Z, [True] * 6)
    assert isinstance(s, SampledSection)
    assert s.points == tuple(zip(D, Z, strict=True))
    assert (s.n_trimmed_start, s.n_trimmed_end) == (0, 0)


def test_trim_leading_and_trailing_nodata_keeps_distances():
    valid = [False, True, True, True, True, False]
    s = trim_nodata(D, Z, valid)
    assert s.points == ((1.0, 4.0), (2.0, 3.0), (3.0, 3.5), (4.0, 4.5))
    assert (s.n_trimmed_start, s.n_trimmed_end) == (1, 1)


def test_nan_counts_as_nodata():
    z = [math.nan, 4.0, 3.0, 3.5, 4.5, math.nan]
    s = trim_nodata(D, z, [True] * 6)
    assert (s.n_trimmed_start, s.n_trimmed_end) == (1, 1)


def test_interior_nodata_raises():
    valid = [True, True, False, False, True, True]
    with pytest.raises(NoDataError, match="2 interior NoData") as exc:
        trim_nodata(D, Z, valid)
    assert exc.value.n_interior == 2


def test_all_nodata_raises():
    with pytest.raises(NoDataError, match="no valid") as exc:
        trim_nodata(D, Z, [False] * 6)
    assert exc.value.n_interior == 0


def test_fewer_than_three_valid_points_raises():
    with pytest.raises(NoDataError, match="3"):
        trim_nodata(D, Z, [False, False, True, True, False, False])


def test_nodata_error_is_value_error():
    assert issubclass(NoDataError, ValueError)


def test_trim_length_mismatch():
    with pytest.raises(ValueError, match="same length"):
        trim_nodata(D, Z[:-1], [True] * 6)


def test_sampled_section_is_frozen():
    s = trim_nodata(D, Z, [True] * 6)
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.n_trimmed_start = 3


# --- integration: generate, sample an analytic DTM, detect ---------------------------

BED, BANK_TOP = 10.0, 14.0


def _channel_z(offset):
    """Trapezoidal channel: flat bed |y| < 10, banks to 14 m at |y| = 20, rising plain."""
    a = np.abs(offset)
    return np.where(a < 10, BED,
                    np.where(a < 20, BED + (a - 10) * 0.4, BANK_TOP + (a - 20) * 0.005))


@pytest.mark.parametrize("angle", [0.0, 30.0])
def test_generate_sample_detect_on_synthetic_channel(angle):
    t = np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
    n_left = np.array([-t[1], t[0]])  # left of the axis direction
    axis = [(0.0, 0.0), tuple(1000 * t)]
    secs = generate_sections(axis, step=250, width=200)
    assert len(secs) == 4
    opts = BankfullOptions()  # original method, one run: fast
    for sec in secs:
        d, xy = stations(sec.coords, 1.0)
        offset = (xy - np.array(sec.center)) @ n_left  # signed distance, left > 0
        z = _channel_z(offset)
        # The DTM ends 90 m to the left: leading NoData (offsets 100..91) on the left side.
        sampled = trim_nodata(d, z, offset <= 90.5)
        assert sampled.n_trimmed_start == 10 and sampled.n_trimmed_end == 0
        res = detect_bankfull(sampled.points, opts, line_coords=sec.coords)
        assert res.status == "ok"
        assert res.level.level == pytest.approx(BANK_TOP, abs=0.15)
        g = res.geometry
        assert not g.touches_left_edge and not g.touches_right_edge
        # Banks about 20 m left and right of the axis, in map coordinates.
        left_off = (np.array(res.left_xy) - np.array(sec.center)) @ n_left
        right_off = (np.array(res.right_xy) - np.array(sec.center)) @ n_left
        assert left_off == pytest.approx(20.0, abs=1.0)
        assert right_off == pytest.approx(-20.0, abs=1.0)