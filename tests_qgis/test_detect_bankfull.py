"""Headless tests of bankfulldetection:detectbankfull on a synthetic DTM."""

import numpy as np
import pytest
from conftest import memory_lines

pytestmark = pytest.mark.usefixtures("qgis_app")

X0, Y0 = 500000.0, 4800000.0     # UTM 32N, central Italy
BED, BANK_TOP = 10.0, 14.0
NODATA = -9999.0
ORIGINAL = 1                      # PRESET index of the original method (fast)

SECTION_FIELDS = ["sec_id", "axis_fid", "part", "chainage", "status", "bf_z", "bf_z_min",
                  "bf_z_max", "runs_ok", "n_runs", "left_d", "right_d", "width", "area",
                  "mean_dep", "max_dep", "thalweg_z", "n_wet", "edge_l", "edge_r", "cross",
                  "cross_in", "n_pts"]


def _channel_z(offset):
    a = np.abs(offset)
    return np.where(a < 10, BED,
                    np.where(a < 20, BED + (a - 10) * 0.4, BANK_TOP + (a - 20) * 0.005))


@pytest.fixture(scope="module")
def dtm_path(tmp_path_factory):
    """1 m DTM, 400 x 300 m, channel along y = Y0; NoData hole in the bed at x = X0 + 250."""
    from osgeo import gdal, osr

    gdal.UseExceptions()
    nx, ny = 400, 300
    xs = X0 + np.arange(nx) + 0.5
    ys = Y0 + 150 - np.arange(ny) - 0.5            # north-up rows
    z = np.tile(_channel_z(ys - Y0)[:, None], (1, nx))
    hole = (np.abs(xs - (X0 + 250)) < 3)[None, :] & (np.abs(ys - Y0) < 4)[:, None]
    z[hole] = NODATA
    path = str(tmp_path_factory.mktemp("dtm") / "dtm.tif")
    ds = gdal.GetDriverByName("GTiff").Create(path, nx, ny, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((X0, 1.0, 0.0, Y0 + 150, 0.0, -1.0))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32632)
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.SetNoDataValue(NODATA)
    band.WriteArray(z.astype(np.float32))
    ds = None
    return path


@pytest.fixture
def dtm(dtm_path):
    from qgis.core import QgsRasterLayer

    layer = QgsRasterLayer(dtm_path, "dtm")
    assert layer.isValid()
    return layer


def _axis(crs="EPSG:32632"):
    coords = [(X0, Y0), (X0 + 400, Y0)]
    if crs != "EPSG:32632":
        from qgis.core import (
            QgsCoordinateReferenceSystem,
            QgsCoordinateTransform,
            QgsPointXY,
            QgsProject,
        )
        tr = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:32632"),
                                    QgsCoordinateReferenceSystem(crs), QgsProject.instance())
        coords = [(p.x(), p.y()) for p in (tr.transform(QgsPointXY(*c)) for c in coords)]
    return memory_lines([[coords]], crs=crs)


def _params(dtm, **kw):
    params = {"DTM": dtm, "STEP": 100, "WIDTH": 200, "PRESET": ORIGINAL,
              "OUTPUT_SECTIONS": "TEMPORARY_OUTPUT", "OUTPUT_BANKS": "TEMPORARY_OUTPUT",
              "OUTPUT_CHANNEL": "TEMPORARY_OUTPUT"}
    params.update(kw)
    return params


def _by_id(layer):
    return sorted(layer.getFeatures(), key=lambda f: f["sec_id"])


def test_detect_from_axis(run_alg, dtm):
    res, msgs = run_alg("detectbankfull", _params(dtm, AXIS=_axis()))
    secs = _by_id(res["OUTPUT_SECTIONS"])
    assert res["OUTPUT_SECTIONS"].fields().names() == SECTION_FIELDS
    assert [f["chainage"] for f in secs] == pytest.approx([50, 150, 250, 350])
    assert [f["status"] for f in secs] == ["ok", "ok", "nodata", "ok"]
    for f in secs:
        if f["status"] != "ok":
            continue
        assert f["bf_z"] == pytest.approx(BANK_TOP, abs=0.15)
        assert f["n_runs"] == 1 and f["runs_ok"] == 1
        assert f["edge_l"] == 0 and f["edge_r"] == 0
        assert f["cross"] == 0 and f["cross_in"] == 0
        assert f["thalweg_z"] == pytest.approx(BED)
        assert f["width"] == pytest.approx(40.0, abs=2.0)
        assert f["left_d"] == pytest.approx(80.0, abs=1.0)   # 100 - 20 from the left end
    from qgis.core import NULL

    nodata = secs[2]
    assert nodata["bf_z"] == NULL and nodata["n_pts"] == NULL and nodata["cross"] == 0
    assert any(kind == "warning" and "Section 3" in text and "nodata" in text
               for kind, text in msgs)

    banks = list(res["OUTPUT_BANKS"].getFeatures())
    assert len(banks) == 6
    for b in banks:
        y = b.geometry().asPoint().y() - Y0
        assert y == pytest.approx(20.0 if b["side"] == "L" else -20.0, abs=1.0)

    (poly,) = list(res["OUTPUT_CHANNEL"].getFeatures())
    assert poly["valid"] == 1 and poly["n_used"] == 3 and poly["n_skip"] == 1
    assert poly.geometry().isGeosValid()


def test_axis_in_other_metric_crs_gives_same_levels(run_alg, dtm):
    ref, _ = run_alg("detectbankfull", _params(dtm, AXIS=_axis()))
    other, _ = run_alg("detectbankfull", _params(dtm, AXIS=_axis("EPSG:3003")))
    assert other["OUTPUT_SECTIONS"].crs().authid() == "EPSG:3003"
    a = [f["bf_z"] for f in _by_id(ref["OUTPUT_SECTIONS"]) if f["status"] == "ok"]
    b = [f["bf_z"] for f in _by_id(other["OUTPUT_SECTIONS"]) if f["status"] == "ok"]
    assert len(a) == len(b) == 3
    assert b == pytest.approx(a, abs=0.05)


def test_user_sections_with_order_field(run_alg, dtm):
    gen, _ = run_alg("generatesections", {"AXIS": _axis(), "STEP": 100, "WIDTH": 200,
                                          "OUTPUT": "TEMPORARY_OUTPUT"})
    ref, _ = run_alg("detectbankfull", _params(dtm, AXIS=_axis()))
    res, _ = run_alg("detectbankfull", _params(dtm, SECTIONS=gen["OUTPUT"],
                                               ORDER_FIELD="sec_id"))
    secs = _by_id(res["OUTPUT_SECTIONS"])
    assert [f["status"] for f in secs] == ["ok", "ok", "nodata", "ok"]
    assert [f["bf_z"] for f in secs if f["status"] == "ok"] == pytest.approx(
        [f["bf_z"] for f in _by_id(ref["OUTPUT_SECTIONS"]) if f["status"] == "ok"])
    (poly,) = list(res["OUTPUT_CHANNEL"].getFeatures())
    assert poly["valid"] == 1


def test_multipart_user_section(run_alg, dtm):
    sections = memory_lines([
        [[(X0 + 50, Y0 + 100), (X0 + 50, Y0 - 100)]],
        [[(X0 + 150, Y0 + 100), (X0 + 150, Y0 + 50)], [(X0 + 150, Y0), (X0 + 150, Y0 - 100)]],
    ], multi=True)
    res, msgs = run_alg("detectbankfull", _params(dtm, SECTIONS=sections))
    secs = _by_id(res["OUTPUT_SECTIONS"])
    assert [f["status"] for f in secs] == ["ok", "multipart"]
    assert any("multipart" in text for _, text in msgs)


def test_axis_xor_sections_required(run_alg, dtm):
    from qgis.core import QgsProcessingException

    with pytest.raises(QgsProcessingException):
        run_alg("detectbankfull", _params(dtm))
    with pytest.raises(QgsProcessingException):
        run_alg("detectbankfull", _params(dtm, AXIS=_axis(), SECTIONS=_axis()))


def test_geographic_axis_rejected(run_alg, dtm):
    from qgis.core import QgsProcessingException

    axis = memory_lines([[[(9.0, 43.3), (9.005, 43.3)]]], crs="EPSG:4326")
    with pytest.raises(QgsProcessingException):
        run_alg("detectbankfull", _params(dtm, AXIS=axis))


def _short_right_sections():
    """Two sections ending on the right bank slope, 15 m from the axis (left end north)."""
    return memory_lines([[[(X0 + x, Y0 + 100), (X0 + x, Y0 - 15)]] for x in (50, 150)])


def test_bank_on_section_edge(run_alg, dtm):
    res, msgs = run_alg("detectbankfull", _params(dtm, SECTIONS=_short_right_sections()))
    secs = _by_id(res["OUTPUT_SECTIONS"])
    assert [f["status"] for f in secs] == ["ok", "ok"]
    assert all(f["edge_l"] == 0 and f["edge_r"] == 1 for f in secs)
    assert any(kind == "warning" and "increase the section width" in text
               for kind, text in msgs)
    edge_banks = [b for b in res["OUTPUT_BANKS"].getFeatures() if b["edge"] == 1]
    assert {b["side"] for b in edge_banks} == {"R"}
    # Banks on the edge are left out of the channel polygon by default.
    assert res["OUTPUT_CHANNEL"].featureCount() == 0
    assert any("not built" in text for _, text in msgs)


def test_edge_banks_in_polygon_on_request(run_alg, dtm):
    res, _ = run_alg("detectbankfull", _params(dtm, SECTIONS=_short_right_sections(),
                                               EDGE_IN_POLYGON=True))
    (poly,) = list(res["OUTPUT_CHANNEL"].getFeatures())
    assert poly["n_used"] == 2 and poly["valid"] == 1


def test_cancel_after_first_section(qgis_app, dtm):
    import processing
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback

    class CancelAfterFirst(QgsProcessingFeedback):
        def setProgress(self, value):
            super().setProgress(value)
            if value > 5:
                self.cancel()

    res = processing.run("bankfulldetection:detectbankfull", _params(dtm, AXIS=_axis()),
                         context=QgsProcessingContext(), feedback=CancelAfterFirst())
    assert res["OUTPUT_SECTIONS"].featureCount() == 1


def test_recommended_preset(run_alg, dtm):
    res, _ = run_alg("detectbankfull", _params(dtm, AXIS=_axis(), PRESET=0, STEP=200))
    secs = _by_id(res["OUTPUT_SECTIONS"])
    assert [f["status"] for f in secs] == ["ok", "ok"]
    for f in secs:
        assert f["n_runs"] == 11 and f["runs_ok"] == 11
        assert f["bf_z"] == pytest.approx(BANK_TOP, abs=0.15)
        assert f["bf_z_min"] <= f["bf_z"] <= f["bf_z_max"]


def test_shapefile_outputs_keep_field_names(run_alg, dtm, tmp_path):
    from qgis.core import QgsVectorLayer

    paths = {k: str(tmp_path / f"{k.lower()}.shp")
             for k in ("OUTPUT_SECTIONS", "OUTPUT_BANKS", "OUTPUT_CHANNEL")}
    run_alg("detectbankfull", _params(dtm, AXIS=_axis(), **paths))
    sections = QgsVectorLayer(paths["OUTPUT_SECTIONS"], "s", "ogr")
    assert sections.fields().names() == SECTION_FIELDS
    statuses = sorted(f["status"] for f in sections.getFeatures())
    assert statuses == ["nodata", "ok", "ok", "ok"]
    banks = QgsVectorLayer(paths["OUTPUT_BANKS"], "b", "ogr")
    assert banks.fields().names() == ["sec_id", "side", "chainage", "dist", "bf_z", "edge"]
    channel = QgsVectorLayer(paths["OUTPUT_CHANNEL"], "c", "ogr")
    assert channel.fields().names() == ["axis_fid", "part", "n_used", "n_skip", "valid",
                                        "reason"]
    assert channel.featureCount() == 1