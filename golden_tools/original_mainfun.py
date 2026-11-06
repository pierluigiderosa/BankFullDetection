"""
Faithful Python 3 / Shapely 2 port of the geometric parts of the original mainFun
(original-master/tools/BankElevationDetection.py, QGIS 2.18 / Python 2.7).

Only syntax has been updated (cmp(), `.type is`, iteration over multi-geometries).
The logic is intentionally unchanged: this module exists only to generate golden data.
It is NOT part of the plugin and must not be "improved": style warnings that would
require rewriting the original code are silenced line by line with `noqa`.
"""
import numpy as np
from shapely.geometry import LineString, Polygon, box


def WTable(polygon, h):
    minx, miny, maxx, maxy = polygon.bounds  # noqa: RUF059
    WTLine = LineString([(minx, h), (maxx, h)])
    return WTLine


def hdepth(polygon, h):
    minx, miny, maxx, maxy = polygon.bounds  # noqa: RUF059
    b = box(minx, miny, maxx, h)
    return b


def diff_n(Harray, locMax, dist):
    leftIndex = max(locMax - dist, 0)
    rightIndex = min(locMax + dist, len(Harray) - 1)
    lGrad = Harray[locMax] - Harray[leftIndex]
    rGrad = Harray[rightIndex] - Harray[locMax]
    # cmp(lGrad, 0) > 0  ->  lGrad > 0 ; cmp(rGrad, 0) < 0  ->  rGrad < 0
    if (lGrad > 0) & (rGrad < 0) & (lGrad != rGrad):  # noqa: SIM103
        return True
    else:
        return False


def local_maxmin(Harray):
    gradients = np.diff(Harray)
    maxima_num = 0
    minima_num = 0
    max_locations = []
    min_locations = []
    count = 0
    ranks = []
    rank = 1
    for i in gradients[:-1]:
        count += 1  # noqa: SIM113
        if (i > 0) & (gradients[count] < 0) & (i != gradients[count]):
            maxima_num += 1
            max_locations.append(count)
            # NB: as in the original, `rank` is not reset between maxima.
            while diff_n(Harray, count, rank) and rank < len(Harray):
                rank += 1
            ranks.append(rank)
        if (i < 0) & (gradients[count] > 0) & (i != gradients[count]):
            minima_num += 1
            min_locations.append(count)
    turning_points = {
        "maxima_number": maxima_num,
        "minima_number": minima_num,
        "maxima_locations": max_locations,
        "minima_locations": min_locations,
        "maxima_ranks": ranks,
    }
    return turning_points


def build_polygons(pointList):
    """Return (polygonXSorig, borderXS, polygonXS) exactly as mainFun builds them.

    The original mutates `pointList` with insert/append; here a copy is used,
    which yields the same polygons without side effects on the caller.
    """
    pointList = list(pointList)
    polygonXSorig = Polygon(pointList)
    borderXS = LineString(pointList)
    maxY = polygonXSorig.bounds[-1]
    pointList.insert(0, (polygonXSorig.bounds[0], maxY + 1))
    pointList.append((polygonXSorig.bounds[2], maxY + 1))
    polygonXS = Polygon(pointList)
    return polygonXSorig, borderXS, polygonXS


def hydraulic_curve(pointList, nVsteps=100):
    """Depth -> hydraulic radius / hydraulic depth loop of mainFun.

    Returns (depts, HydRad, HydDept, polygons) with polygons = (orig, border, XS).
    """
    polygonXSorig, borderXS, polygonXS = build_polygons(pointList)
    minY = polygonXSorig.bounds[1]
    maxY = polygonXSorig.bounds[-1]
    depts = np.linspace(minY + 0.1, maxY - 0.1, nVsteps)

    HydRad = np.array([])
    HydDept = np.array([])
    for dept in depts:
        wdep = hdepth(polygonXSorig, dept)
        wdepLine = WTable(polygonXSorig, dept)
        wetArea = polygonXS.intersection(wdep)
        wetPerimeter = borderXS.intersection(wdep)
        wetWTLine = wdepLine.intersection(polygonXS)
        HydRad = np.append(HydRad, wetArea.area / wetPerimeter.length)
        HydDept = np.append(HydDept, wetArea.area / wetWTLine.length)
    return depts, HydRad, HydDept, (polygonXSorig, borderXS, polygonXS)


def terrace_index(HydDept):
    """The 'terrace' branch of mainFun (raises IndexError/ValueError as the original)."""
    turning_points = local_maxmin(HydDept)
    terrace = []
    for i in range(len(turning_points["maxima_locations"])):
        if turning_points["maxima_ranks"][i] == max(turning_points["maxima_ranks"]):
            terrace.append(turning_points["maxima_locations"][i])
    return terrace[0]


def wet_area_stats(polygonXSorig, polygonXS, h):
    """Wet area at level h: (left, right, nchannel, wetArea) as in mainFun."""
    wdep = hdepth(polygonXSorig, h)
    wetArea = polygonXS.intersection(wdep)
    boundsOK = ()
    Area = 0
    if wetArea.geom_type == "MultiPolygon":
        nchannel = str(len(wetArea.geoms))
        for wetPolygon in wetArea.geoms:
            if wetPolygon.area > Area:
                Area = wetPolygon.area
                boundsOK = wetPolygon.bounds
    else:
        boundsOK = wetArea.bounds
        nchannel = "1"
    return boundsOK[0], boundsOK[2], nchannel, wetArea
