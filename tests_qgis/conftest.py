"""Headless QGIS fixtures for the Processing algorithms.

Run with the QGIS environment (not collected by the plain ``pytest -q``):
    & "C:\\Program Files\\QGIS 3.34.7\\bin\\python-qgis-ltr.bat" -m pytest tests_qgis -q
"""

import os
import sys
from pathlib import Path

import pytest

PLUGIN_DIR = Path(__file__).resolve().parent.parent
PLUGIN_PACKAGE = PLUGIN_DIR.name

# The plugin is imported as a package (as QGIS does), from its parent folder.
sys.path.insert(0, str(PLUGIN_DIR.parent))

qgis_core = pytest.importorskip("qgis.core")


@pytest.fixture(scope="session")
def qgis_app():
    """QgsApplication with Processing and the plugin provider registered via the plugin."""
    from qgis.core import QgsApplication

    app = QgsApplication([], False)
    app.initQgis()
    sys.path.append(os.path.join(QgsApplication.prefixPath(), "python", "plugins"))
    from processing.core.Processing import Processing

    Processing.initialize()

    package = __import__(PLUGIN_PACKAGE)
    plugin = package.classFactory(None)  # iface is used only by initGui
    plugin.initProcessing()
    yield app
    plugin.unload()


@pytest.fixture
def run_alg(qgis_app):
    """Run an algorithm of the provider; returns (results, feedback messages)."""
    import processing
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback

    class Feedback(QgsProcessingFeedback):
        def __init__(self):
            super().__init__()
            self.messages = []

        def pushInfo(self, info):
            self.messages.append(("info", info))

        def pushWarning(self, warning):
            self.messages.append(("warning", warning))

    def run(name, params):
        feedback = Feedback()
        context = QgsProcessingContext()
        results = processing.run(f"bankfulldetection:{name}", params,
                                 context=context, feedback=feedback)
        return results, feedback.messages

    return run


def memory_lines(parts_per_feature, crs="EPSG:32632", multi=False):
    """Memory line layer; each feature is a list of parts, each part a list of (x, y)."""
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsVectorLayer

    geom_type = "MultiLineString" if multi else "LineString"
    layer = QgsVectorLayer(f"{geom_type}?crs={crs}", "axis", "memory")
    feats = []
    for parts in parts_per_feature:
        f = QgsFeature()
        pts = [[QgsPointXY(x, y) for x, y in part] for part in parts]
        f.setGeometry(QgsGeometry.fromMultiPolylineXY(pts) if multi
                      else QgsGeometry.fromPolylineXY(pts[0]))
        feats.append(f)
    layer.dataProvider().addFeatures(feats)
    return layer