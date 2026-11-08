"""QGIS helpers of the Processing algorithms: CRS checks, fields, geometry conversion.

No computation here: everything geometric is in ``bankfull_core``.
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingException,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QCoreApplication
from shapely.geometry import LineString, MultiLineString

# QgsField accepts QMetaType.Type only from QGIS 3.38; QVariant.Type is deprecated there.
if Qgis.QGIS_VERSION_INT >= 33800:
    from qgis.PyQt.QtCore import QMetaType

    _FIELD_TYPES = {"int": QMetaType.Int, "long": QMetaType.LongLong,
                    "double": QMetaType.Double, "string": QMetaType.QString}
else:
    from qgis.PyQt.QtCore import QVariant

    _FIELD_TYPES = {"int": QVariant.Int, "long": QVariant.LongLong,
                    "double": QVariant.Double, "string": QVariant.String}


def tr(message):
    return QCoreApplication.translate("BankFullDetection", message)


def make_field(name, kind, length=0):
    """QgsField of kind "int", "long", "double" or "string" (``length`` for strings)."""
    field = QgsField(name, _FIELD_TYPES[kind])
    if length:
        field.setLength(length)
    return field


def check_metric_crs(crs, what):
    """Raise QgsProcessingException unless ``crs`` is valid, projected and in metres.

    Args:
        crs: QgsCoordinateReferenceSystem of a layer.
        what: layer description for the message (e.g. "River axis").
    """
    if not isinstance(crs, QgsCoordinateReferenceSystem) or not crs.isValid():
        raise QgsProcessingException(tr(f"{what}: the layer has no valid CRS."))
    if crs.isGeographic() or crs.mapUnits() != Qgis.DistanceUnit.Meters:
        raise QgsProcessingException(tr(
            f"{what}: the CRS {crs.authid() or crs.description()} is not projected in "
            "metres. Reproject the layer to a metric projected CRS (e.g. UTM)."
        ))


def line_geometry_to_shapely(geometry):
    """2D Shapely LineString / MultiLineString of a QGIS line geometry, or None if empty.

    Curves are segmentized; Z and M values are dropped.
    """
    if geometry is None or geometry.isNull() or geometry.isEmpty():
        return None
    geom = QgsGeometry(geometry)
    if QgsWkbTypes.isCurvedType(geom.wkbType()):
        geom.convertToStraightSegment()
    if geom.isMultipart():
        parts = [[(p.x(), p.y()) for p in part] for part in geom.asMultiPolyline()]
        parts = [p for p in parts if len(p) >= 2]
        if not parts:
            return None
        return MultiLineString(parts) if len(parts) > 1 else LineString(parts[0])
    coords = [(p.x(), p.y()) for p in geom.asPolyline()]
    return LineString(coords) if len(coords) >= 2 else None


def polyline_geometry(coords):
    """QgsGeometry polyline from (x, y) coordinates."""
    return QgsGeometry.fromPolylineXY([QgsPointXY(float(x), float(y)) for x, y in coords])
