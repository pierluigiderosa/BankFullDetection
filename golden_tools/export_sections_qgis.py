"""
Export cross-section profiles (section_id, distance, z) for BankFullDetection golden data.

Run inside QGIS 3.34+: Plugins > Python Console > Show Editor > Open script > Run.
Writes a CSV into <plugin>/tests/data/sections/.
"""
import csv
import os

from qgis.core import (
    QgsApplication,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
)

# === Parameters to adapt ===================================================
SECTIONS_LAYER = "sezioni_test"  # name of the line layer in the Layers panel
DTM_LAYER = "dtm"                # name of the DTM raster layer
ID_FIELD = "section_id"          # integer field with the section id
OUTPUT_NAME = "paglia.csv"       # output CSV file name
STEP = None                      # sampling step in metres; None = DTM pixel size
# ===========================================================================

project = QgsProject.instance()
sections = project.mapLayersByName(SECTIONS_LAYER)[0]
dtm = project.mapLayersByName(DTM_LAYER)[0]
provider = dtm.dataProvider()
step = STEP or min(dtm.rasterUnitsPerPixelX(), dtm.rasterUnitsPerPixelY())

xform = None
if sections.crs() != dtm.crs():
    xform = QgsCoordinateTransform(sections.crs(), dtm.crs(), project)

out_dir = os.path.join(
    QgsApplication.qgisSettingsDirPath(),
    "python", "plugins", "BankFullDetection", "tests", "data", "sections",
)
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, OUTPUT_NAME)

problems = []
n_written = 0
with open(out_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["section_id", "distance", "z"])
    for feat in sections.getFeatures():
        sid = feat[ID_FIELD]
        if sid is None or str(sid) == "NULL":
            problems.append(f"feature {feat.id()}: {ID_FIELD} is empty, skipped")
            continue
        geom = QgsGeometry(feat.geometry())
        if xform:
            geom.transform(xform)
        if geom.isMultipart():
            parts = geom.asMultiPolyline()
            if len(parts) != 1:
                problems.append(f"section {sid}: {len(parts)} parts, skipped")
                continue
            geom = QgsGeometry.fromPolylineXY(parts[0])

        dense = geom.densifyByDistance(step)
        rows, dist, prev, nodata = [], 0.0, None, 0
        for v in dense.vertices():
            p = QgsPointXY(v.x(), v.y())
            if prev is not None:
                dist += prev.distance(p)
            prev = p
            value, ok = provider.sample(p, 1)
            if not ok:
                nodata += 1
                continue
            rows.append((int(sid), round(dist, 3), round(value, 3)))

        if nodata:
            problems.append(f"section {sid}: {nodata} NoData points, skipped")
            continue
        writer.writerows(rows)
        n_written += 1

print(f"Written {n_written} sections to {out_path} (step {step:.2f} m)")
for msg in problems:
    print("WARNING:", msg)
