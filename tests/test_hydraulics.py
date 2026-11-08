import copy

import numpy as np
import pytest
from conftest import read_golden_curves
from numpy.testing import assert_allclose, assert_array_equal

from bankfull_core import BankfullOptions, InvalidSectionError, hydraulic_curve
from bankfull_core.hydraulics import _hydraulic_curve

GOLDEN = read_golden_curves()


@pytest.mark.parametrize("key", sorted(GOLDEN), ids=lambda k: f"{k[0]}-{k[1]}")
def test_golden_curves(key, all_sections):
    gold = GOLDEN[key]
    curve = hydraulic_curve(all_sections[key])
    assert_allclose(curve.levels, gold["depth"], rtol=1e-9)
    assert_allclose(curve.hyd_depth, gold["hyd_depth"], rtol=1e-9)
    assert_allclose(curve.wet_area / curve.wet_perimeter, gold["hyd_radius"], rtol=1e-9)


def test_trapezoid_analytic(synthetic):
    # Synthetic 1: bottom width 10 m, side slopes 2H:1V, bank top at z = 3.
    curve = hydraulic_curve(synthetic[1])
    below = curve.levels < 3.0
    assert below.sum() > 50
    h = curve.levels[below]
    expected = (10 * h + 2 * h**2) / (10 + 4 * h)
    assert_allclose(curve.hyd_depth[below], expected, rtol=1e-9)


@pytest.mark.parametrize("mode", ["original", "thalweg"])
def test_top_extension_irrelevant(all_sections, mode):
    opts = BankfullOptions(multichannel=mode)
    for pts in all_sections.values():
        a = _hydraulic_curve(pts, opts, top_extension=1.0)
        b = _hydraulic_curve(pts, opts, top_extension=0.2)
        for field in ("levels", "hyd_depth", "wet_area", "wet_width",
                      "wet_perimeter", "n_wet_polygons", "n_used_polygons"):
            assert_array_equal(getattr(a, field), getattr(b, field))


def test_input_not_modified(synthetic):
    pts = list(synthetic[3])
    before = copy.deepcopy(pts)
    hydraulic_curve(pts)
    hydraulic_curve(pts, BankfullOptions(multichannel="thalweg"))
    assert pts == before

    arr = np.array(synthetic[3])
    arr_before = arr.copy()
    hydraulic_curve(arr)
    assert_array_equal(arr, arr_before)


def test_result_is_read_only(synthetic):
    curve = hydraulic_curve(synthetic[1])
    with pytest.raises(ValueError):
        curve.hyd_depth[0] = 0.0


@pytest.mark.parametrize(
    ("points", "match"),
    [
        ([(0, 1), (1, 0)], "at least 3 points"),
        ([], "at least 3 points|shape"),
        ([(0, 1), (1, 0), (1, 2)], "strictly increasing"),
        ([(0, 1), (2, 0), (1, 2)], "strictly increasing"),
        ([(0, 1), (1, 1), (2, 1)], "elevations are equal"),
        ([(0, 1), (1, float("nan")), (2, 1)], "non-finite"),
        ([(0, 1, 2), (1, 0, 2), (2, 1, 2)], "shape"),
        ([(0, 0.15), (1, 0.0), (2, 0.15)], "relief"),
    ],
)
def test_invalid_sections(points, match):
    with pytest.raises(InvalidSectionError, match=match):
        hydraulic_curve(points)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"n_levels": 1},
        {"n_levels": 10.0},
        {"n_levels": True},
        {"min_hyd_depth": 0},
        {"min_hyd_depth": float("nan")},
        {"multichannel": "all"},
    ],
)
def test_invalid_options(kwargs):
    with pytest.raises(ValueError):
        BankfullOptions(**kwargs)


def test_default_options():
    opts = BankfullOptions()
    assert (opts.n_levels, opts.min_hyd_depth, opts.multichannel) == (100, 1.0, "original")


def test_thalweg_uses_one_polygon(synthetic):
    pts = synthetic[3]  # two depressions separated by a bar
    orig = hydraulic_curve(pts)
    thal = hydraulic_curve(pts, BankfullOptions(multichannel="thalweg"))
    assert orig.n_wet_polygons.max() == 2
    assert_array_equal(orig.n_used_polygons, orig.n_wet_polygons)
    assert_array_equal(thal.n_wet_polygons, orig.n_wet_polygons)
    assert np.all(thal.n_used_polygons == 1)
    two = orig.n_wet_polygons == 2
    assert np.all(thal.wet_area[two] < orig.wet_area[two])
    assert_array_equal(thal.hyd_depth[~two], orig.hyd_depth[~two])
