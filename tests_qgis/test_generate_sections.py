"""Headless tests of bankfulldetection:generatesections."""

import math

import pytest
from conftest import memory_lines

pytestmark = pytest.mark.usefixtures("qgis_app")

FIELDS = ["sec_id", "axis_fid", "part", "chainage", "azimuth", "cross"]


def _features(layer):
    return sorted(layer.getFeatures(), key=lambda f: f["sec_id"])


def _ends(feat):
    line = feat.geometry().asPolyline()
    return (line[0].x(), line[0].y()), (line[-1].x(), line[-1].y())


def _semicircle(radius, n=200):
    return [(radius * math.cos(math.pi * (1 - k / n)), radius * math.sin(math.pi * (1 - k / n)))
            for k in range(n + 1)]


def test_provider_and_algorithm_registered():
    from qgis.core import QgsApplication

    provider = QgsApplication.processingRegistry().providerById("bankfulldetection")
    assert provider is not None
    assert "generatesections" in [a.name() for a in provider.algorithms()]


def test_straight_axis(run_alg):
    axis = memory_lines([[[(0, 0), (1000, 0)]]])
    res, _ = run_alg("generatesections", {"AXIS": axis, "STEP": 100, "WIDTH": 50,
                                          "OUTPUT": "TEMPORARY_OUTPUT"})
    out = res["OUTPUT"]
    assert out.crs().authid() == "EPSG:32632"
    assert out.fields().names() == FIELDS
    feats = _features(out)
    assert [f["sec_id"] for f in feats] == list(range(1, 11))
    for f in feats:
        c = f["chainage"]
        left, right = _ends(f)
        assert left == pytest.approx((c, 25.0))   # left of an eastward axis is north
        assert right == pytest.approx((c, -25.0))
        assert f["part"] == 0 and f["cross"] == 0
        assert f["azimuth"] == pytest.approx(90.0)
    assert [f["chainage"] for f in feats] == pytest.approx([50 + 100 * k for k in range(10)])


def test_default_width_is_total(run_alg):
    axis = memory_lines([[[(0, 0), (1000, 0)]]])
    res, _ = run_alg("generatesections", {"AXIS": axis, "OUTPUT": "TEMPORARY_OUTPUT"})
    f = _features(res["OUTPUT"])[0]
    assert f.geometry().length() == pytest.approx(500.0)
    assert f["chainage"] == pytest.approx(25.0)   # default step 50, offset step / 2


def test_multi_axis_and_several_features(run_alg):
    axis = memory_lines([[[(0, 0), (300, 0)], [(1000, 0), (1500, 0)]],
                         [[(0, 1000), (200, 1000)]]], multi=True)
    res, _ = run_alg("generatesections", {"AXIS": axis, "STEP": 100, "WIDTH": 50,
                                          "OUTPUT": "TEMPORARY_OUTPUT"})
    feats = _features(res["OUTPUT"])
    assert [f["sec_id"] for f in feats] == list(range(1, 11))
    fids = sorted({f["axis_fid"] for f in feats})
    assert len(fids) == 2
    first = [f for f in feats if f["axis_fid"] == fids[0]]
    assert [f["part"] for f in first] == [0] * 3 + [1] * 5
    assert len([f for f in feats if f["axis_fid"] == fids[1]]) == 2


def test_crossings_flagged_or_dropped(run_alg):
    axis = memory_lines([[_semicircle(100.0)]])
    params = {"AXIS": axis, "STEP": 20, "WIDTH": 300, "OUTPUT": "TEMPORARY_OUTPUT"}
    flagged, msgs = run_alg("generatesections", params)
    feats = _features(flagged["OUTPUT"])
    assert sum(f["cross"] for f in feats) > 0
    assert any(kind == "warning" and "cross" in text for kind, text in msgs)

    dropped, msgs = run_alg("generatesections", {**params, "CROSSING": 1})
    kept = _features(dropped["OUTPUT"])
    assert 0 < len(kept) < len(feats)
    assert all(f["cross"] == 0 for f in kept)
    assert any("dropped" in text for _, text in msgs)


def test_geographic_crs_rejected(run_alg):
    from qgis.core import QgsProcessingException

    axis = memory_lines([[[(12.0, 43.0), (12.01, 43.0)]]], crs="EPSG:4326")
    with pytest.raises(QgsProcessingException):
        run_alg("generatesections", {"AXIS": axis, "OUTPUT": "TEMPORARY_OUTPUT"})


def test_shapefile_output_keeps_field_names(run_alg, tmp_path):
    from qgis.core import QgsVectorLayer

    axis = memory_lines([[[(0, 0), (1000, 0)]]])
    path = str(tmp_path / "sections.shp")
    run_alg("generatesections", {"AXIS": axis, "STEP": 100, "WIDTH": 50, "OUTPUT": path})
    layer = QgsVectorLayer(path, "s", "ogr")
    assert layer.isValid()
    assert layer.fields().names() == FIELDS
    assert layer.featureCount() == 10
    assert layer.crs().authid() == "EPSG:32632"
