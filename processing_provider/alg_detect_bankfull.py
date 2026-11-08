"""Processing algorithm: bankfull detection on cross-sections sampled from a DTM.

QGIS side only: reading the inputs, sampling the DTM at the stations given by the core,
writing the outputs. The method is in ``bankfull_core``.
"""

import dataclasses
import math
from collections import Counter

from qgis.core import (
    NULL,
    Qgis,
    QgsCoordinateTransform,
    QgsCsException,
    QgsFeature,
    QgsFeatureSink,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBand,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsWkbTypes,
)

from ..bankfull_core.detection import channel_polygon, detect_bankfull
from ..bankfull_core.hydraulics import InvalidSectionError
from ..bankfull_core.options import BankfullOptions
from ..bankfull_core.sampling import NoDataError, stations, trim_nodata
from ..bankfull_core.sections import (
    crossing_flags,
    crossings_inside_banks,
    find_crossings,
)
from ..bankfull_core.smoothing import STATUS_OK
from .alg_generate_sections import (
    add_section_parameters,
    generate_from_axis,
    section_options,
)
from .qgis_io import (
    check_metric_crs,
    line_geometry_to_shapely,
    make_field,
    polyline_geometry,
    tr,
)
from .texts import (
    AXIS_DIRECTION_HELP,
    CITATION_HELP,
    USER_SECTIONS_HELP,
    WIDTH_HELP,
)

# Statuses added by the QGIS side to those of the core (STATUS_OK, no_maxima, ...).
STATUS_NODATA = "nodata"
STATUS_INVALID = "invalid"
STATUS_MULTIPART = "multipart"

PRESETS = ("Recommended (thalweg, min_cv, highest, 11 runs)",
           "Original method (original, min_cv, first, 1 run)")
FROM_PRESET = "From preset"
MULTICHANNEL_CHOICES = (FROM_PRESET, "original", "thalweg")
CRITERION_CHOICES = (FROM_PRESET, "first", "highest")
SELECTION_CHOICES = (FROM_PRESET, "min_cv", "one_se")

# Indicative cost of one CV run per section with the QGIS Python (docs/smoothing.md).
SECONDS_PER_RUN = 0.15

SECTION_FIELDS = (
    ("sec_id", "int"), ("axis_fid", "long"), ("part", "int"), ("chainage", "double"),
    ("status", "string", 32), ("bf_z", "double"), ("bf_z_min", "double"),
    ("bf_z_max", "double"), ("runs_ok", "int"), ("n_runs", "int"), ("left_d", "double"),
    ("right_d", "double"), ("width", "double"), ("area", "double"), ("mean_dep", "double"),
    ("max_dep", "double"), ("thalweg_z", "double"), ("n_wet", "int"), ("edge_l", "int"),
    ("edge_r", "int"), ("cross", "int"), ("cross_in", "int"), ("n_pts", "int"),
)
BANK_FIELDS = (
    ("sec_id", "int"), ("side", "string", 1), ("chainage", "double"), ("dist", "double"),
    ("bf_z", "double"), ("edge", "int"),
)
CHANNEL_FIELDS = (
    ("axis_fid", "long"), ("part", "int"), ("n_used", "int"), ("n_skip", "int"),
    ("valid", "int"), ("reason", "string", 254),
)


def _fields(spec):
    fields = QgsFields()
    for name, kind, *length in spec:
        fields.append(make_field(name, kind, *length))
    return fields


def _advanced(param):
    param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
    return param


def _given(value):
    return value is not None and value != "" and value != NULL


def _is_metric(crs):
    return crs.isValid() and not crs.isGeographic() \
        and crs.mapUnits() == Qgis.DistanceUnit.Meters


class DetectBankfullAlgorithm(QgsProcessingAlgorithm):
    """Bankfull level, banks and channel polygon from a DTM and an axis or sections."""

    def __init__(self):
        super().__init__()
        self._dtm_provider = None
        self._dtm_crs = None
        self._dtm_pixel = None

    def name(self):
        return "detectbankfull"

    def displayName(self):
        return tr("Detect bankfull")

    def group(self):
        return ""

    def groupId(self):
        return ""

    def shortHelpString(self):
        return tr(
            "<p>Detects the bankfull level of river cross-sections sampled from a DTM with "
            "the maximum hydraulic depth method (A/W). Give either the river axis (the "
            "sections are generated as in <i>Generate cross-sections</i>) or a layer of "
            "sections.</p>"
            "<p>Outputs: the sections with the result (field <i>status</i> tells why a "
            "section has no bankfull: nodata, invalid, multipart, no_maxima, "
            "no_max_ge_min_hyd_depth), the bank points, and the channel polygon (never "
            "repaired: <i>valid</i> = 0 and <i>reason</i> if it is not valid, usually "
            "because of crossings between the banks, field <i>cross_in</i>).</p>"
            "<p><i>Recommended</i> options: best agreement with expert estimates on 8 Arno "
            "sections (indicative, not a calibration); about 1.7 s per section. "
            "<i>Original method</i>: about 0.15 s per section. DTM elevations must be in "
            "metres. Sections with interior NoData are skipped; NoData at the section ends "
            "are trimmed.</p>"
            "<p><i>Edge flags</i>: edge_l / edge_r = 1 when the bank is on the section "
            "edge, i.e. not inside the section. " + WIDTH_HELP + "</p>"
        ) + tr(AXIS_DIRECTION_HELP) + tr(USER_SECTIONS_HELP) + tr(CITATION_HELP)

    def createInstance(self):
        return DetectBankfullAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer("DTM", tr("DTM")))
        self.addParameter(QgsProcessingParameterBand("BAND", tr("DTM band"), 1, "DTM"))
        self.addParameter(QgsProcessingParameterFeatureSource(
            "AXIS", tr("River axis (digitised from upstream to downstream)"),
            [QgsProcessing.TypeVectorLine], optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            "SECTIONS", tr("Or: cross-sections (each from the left to the right bank)"),
            [QgsProcessing.TypeVectorLine], optional=True))
        self.addParameter(QgsProcessingParameterField(
            "ORDER_FIELD", tr("Order of the sections along the river (field of the sections)"),
            parentLayerParameterName="SECTIONS", type=QgsProcessingParameterField.Numeric,
            optional=True))
        add_section_parameters(self)

        self.addParameter(_advanced(QgsProcessingParameterEnum(
            "PRESET", tr("Method options"), options=[tr(p) for p in PRESETS], defaultValue=0)))
        for name, label, choices in (
                ("MULTICHANNEL", "Multiple wet polygons", MULTICHANNEL_CHOICES),
                ("CRITERION", "Criterion among the maxima", CRITERION_CHOICES),
                ("SELECTION", "Choice of the smoothing (spar)", SELECTION_CHOICES)):
            self.addParameter(_advanced(QgsProcessingParameterEnum(
                name, tr(label), options=[tr(c) for c in choices], defaultValue=0)))
        self.addParameter(_advanced(QgsProcessingParameterNumber(
            "N_RUNS", tr("Number of CV runs (0 = from preset)"),
            QgsProcessingParameterNumber.Integer, defaultValue=0, minValue=0)))
        self.addParameter(_advanced(QgsProcessingParameterNumber(
            "MIN_HYD_DEPTH", tr("Minimum hydraulic depth A/W [m]"),
            QgsProcessingParameterNumber.Double, defaultValue=1.0, minValue=0.001)))
        self.addParameter(_advanced(QgsProcessingParameterNumber(
            "N_LEVELS", tr("Number of water levels"),
            QgsProcessingParameterNumber.Integer, defaultValue=100, minValue=2)))
        self.addParameter(_advanced(QgsProcessingParameterNumber(
            "SEED", tr("Seed of the CV folds"),
            QgsProcessingParameterNumber.Integer, defaultValue=0, minValue=0)))
        self.addParameter(_advanced(QgsProcessingParameterNumber(
            "SAMPLE_STEP", tr("DTM sampling step [m] (0 = DTM pixel size)"),
            QgsProcessingParameterNumber.Double, defaultValue=0.0, minValue=0.0)))
        self.addParameter(_advanced(QgsProcessingParameterBoolean(
            "EDGE_IN_POLYGON", tr("Use banks on the section edge in the channel polygon"),
            defaultValue=False)))

        self.addParameter(QgsProcessingParameterFeatureSink(
            "OUTPUT_SECTIONS", tr("Sections with bankfull"), QgsProcessing.TypeVectorLine))
        self.addParameter(QgsProcessingParameterFeatureSink(
            "OUTPUT_BANKS", tr("Bank points"), QgsProcessing.TypeVectorPoint))
        self.addParameter(QgsProcessingParameterFeatureSink(
            "OUTPUT_CHANNEL", tr("Channel polygon"), QgsProcessing.TypeVectorPolygon))

    def checkParameterValues(self, parameters, context):
        has_axis = _given(parameters.get("AXIS"))
        has_sections = _given(parameters.get("SECTIONS"))
        if has_axis == has_sections:
            return False, tr("Give either the river axis or the sections layer, not both.")
        return super().checkParameterValues(parameters, context)

    def prepareAlgorithm(self, parameters, context, feedback):
        # Runs in the main thread: clone the raster provider for the worker thread.
        dtm = self.parameterAsRasterLayer(parameters, "DTM", context)
        if dtm is None or not dtm.isValid():
            raise QgsProcessingException(self.invalidRasterError(parameters, "DTM"))
        self._dtm_provider = dtm.dataProvider().clone()
        self._dtm_crs = dtm.crs()
        self._dtm_pixel = min(dtm.rasterUnitsPerPixelX(), dtm.rasterUnitsPerPixelY())
        return True

    # --- options ---------------------------------------------------------------------

    def _options(self, parameters, context):
        preset = (BankfullOptions.recommended()
                  if self.parameterAsEnum(parameters, "PRESET", context) == 0
                  else BankfullOptions())
        changes = {
            "min_hyd_depth": self.parameterAsDouble(parameters, "MIN_HYD_DEPTH", context),
            "n_levels": self.parameterAsInt(parameters, "N_LEVELS", context),
            "seed": self.parameterAsInt(parameters, "SEED", context),
        }
        for name, field, choices in (("MULTICHANNEL", "multichannel", MULTICHANNEL_CHOICES),
                                     ("CRITERION", "criterion", CRITERION_CHOICES),
                                     ("SELECTION", "selection", SELECTION_CHOICES)):
            k = self.parameterAsEnum(parameters, name, context)
            if k > 0:
                changes[field] = choices[k]
        n_runs = self.parameterAsInt(parameters, "N_RUNS", context)
        if n_runs > 0:
            changes["n_runs"] = n_runs
        try:
            return dataclasses.replace(preset, **changes)
        except ValueError as exc:
            raise QgsProcessingException(str(exc)) from exc

    # --- inputs ----------------------------------------------------------------------

    def _records_from_axis(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, "AXIS", context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, "AXIS"))
        check_metric_crs(source.sourceCrs(), tr("River axis"))
        step, width, offset, tangent, drop = section_options(self, parameters, context)
        sub = _SilentProgress(feedback)
        generated, _, n_dropped = generate_from_axis(source, step, width, offset, tangent,
                                                     drop, sub)
        if drop:
            feedback.pushInfo(tr(f"{n_dropped} crossing sections dropped."))
        records = [{"axis_fid": g["axis_fid"], "part": g["section"].part,
                    "chainage": g["section"].chainage, "coords": g["section"].coords,
                    "geometry": polyline_geometry(g["section"].coords), "status": None}
                   for g in generated]
        return records, source.sourceCrs()

    def _records_from_sections(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, "SECTIONS", context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, "SECTIONS"))
        check_metric_crs(source.sourceCrs(), tr("Sections"))
        order_field = self.parameterAsString(parameters, "ORDER_FIELD", context)
        feats = list(source.getFeatures())
        if order_field:
            def key(f):
                v = f[order_field]
                return (1, 0, f.id()) if not _given(v) else (0, v, f.id())
            feats.sort(key=key)
        records = []
        for f in feats:
            # The output layer is a 2D LineString: multi-part or empty sections are
            # written without geometry (their status and sec_id identify them).
            rec = {"axis_fid": None, "part": 0, "chainage": None, "coords": None,
                   "geometry": QgsGeometry(), "status": None}
            line = line_geometry_to_shapely(f.geometry())
            if line is None:
                rec["status"] = STATUS_INVALID
                rec["message"] = f"feature {f.id()}: empty geometry"
            elif line.geom_type != "LineString":
                rec["status"] = STATUS_MULTIPART
                rec["message"] = (f"feature {f.id()}: {len(line.geoms)} parts, written "
                                  "without geometry")
            else:
                rec["coords"] = tuple(line.coords)
                rec["geometry"] = polyline_geometry(rec["coords"])
            records.append(rec)
        return records, source.sourceCrs()

    # --- sampling --------------------------------------------------------------------

    def _sample(self, coords, spacing, band, transform):
        """(distances, z, valid) of the DTM along a section."""
        distances, xy = stations(coords, spacing)
        z, valid = [], []
        for x, y in xy:
            point = QgsPointXY(float(x), float(y))
            if transform is not None:
                try:
                    point = transform.transform(point)
                except QgsCsException:
                    z.append(math.nan)
                    valid.append(False)
                    continue
            value, ok = self._dtm_provider.sample(point, band)
            z.append(value if ok else math.nan)
            valid.append(bool(ok) and not math.isnan(value))
        return distances, z, valid

    # --- main ------------------------------------------------------------------------

    def processAlgorithm(self, parameters, context, feedback):
        options = self._options(parameters, context)
        band = self.parameterAsInt(parameters, "BAND", context)
        edge_in_polygon = self.parameterAsBool(parameters, "EDGE_IN_POLYGON", context)
        from_axis = _given(parameters.get("AXIS"))
        if from_axis:
            records, crs = self._records_from_axis(parameters, context, feedback)
        else:
            records, crs = self._records_from_sections(parameters, context, feedback)

        spacing = self.parameterAsDouble(parameters, "SAMPLE_STEP", context)
        if spacing <= 0:
            if not _is_metric(self._dtm_crs):
                raise QgsProcessingException(tr(
                    "The DTM CRS is not in metres: set the DTM sampling step explicitly."))
            spacing = self._dtm_pixel
        transform = None
        if self._dtm_crs != crs:
            transform = QgsCoordinateTransform(crs, self._dtm_crs, context.transformContext())

        n = len(records)
        feedback.pushInfo(tr(
            f"{n} sections; options: multichannel={options.multichannel}, "
            f"selection={options.selection}, criterion={options.criterion}, "
            f"n_runs={options.n_runs}, min_hyd_depth={options.min_hyd_depth}, "
            f"n_levels={options.n_levels}, seed={options.seed}; sampling step "
            f"{spacing:.3f} m. Estimated time: about "
            f"{n * options.n_runs * SECONDS_PER_RUN / 60:.1f} min."))

        processed = []
        for k, rec in enumerate(records):
            if feedback.isCanceled():
                break
            self._process_section(rec, options, spacing, band, transform)
            rec["sec_id"] = k + 1
            if rec["status"] != STATUS_OK:
                where = (f" (chainage {rec['chainage']:.1f} m)"
                         if rec["chainage"] is not None else "")
                feedback.pushWarning(tr(
                    f"Section {k + 1}{where}: {rec['status']} - {rec.get('message', '')}"))
            processed.append(rec)
            feedback.setProgress(5 + 90 * (k + 1) / max(n, 1))
        canceled = feedback.isCanceled()

        self._crossing_flags(processed)
        sections_id = self._write_sections(parameters, context, processed, crs)
        banks_id = self._write_banks(parameters, context, processed, crs)
        channel_id, polygons = self._write_channel(parameters, context, processed, crs,
                                                   from_axis, edge_in_polygon, feedback)
        feedback.setProgress(100)
        self._summary(feedback, processed, polygons, canceled)
        return {"OUTPUT_SECTIONS": sections_id, "OUTPUT_BANKS": banks_id,
                "OUTPUT_CHANNEL": channel_id}

    def _process_section(self, rec, options, spacing, band, transform):
        rec.update(result=None, n_pts=None, thalweg_z=None)
        if rec["status"] is not None:
            return
        distances, z, valid = self._sample(rec["coords"], spacing, band, transform)
        try:
            sampled = trim_nodata(distances, z, valid)
        except NoDataError as exc:
            rec["status"], rec["message"] = STATUS_NODATA, str(exc)
            return
        rec["n_pts"] = len(sampled.points)
        rec["thalweg_z"] = min(p[1] for p in sampled.points)
        try:
            result = detect_bankfull(sampled.points, options, line_coords=rec["coords"])
        except (InvalidSectionError, ValueError) as exc:
            rec["status"], rec["message"] = STATUS_INVALID, str(exc)
            return
        rec["result"] = result
        rec["status"] = result.status
        if result.status != STATUS_OK:
            rec["message"] = "no bankfull level"

    @staticmethod
    def _crossing_flags(records):
        idx = [i for i, r in enumerate(records) if r["coords"] is not None]
        lines = [records[i]["coords"] for i in idx]
        crossings = find_crossings(lines)
        intervals = []
        for i in idx:
            res = records[i]["result"]
            g = res.geometry if res is not None else None
            intervals.append((g.left, g.right) if g is not None else None)
        cross = crossing_flags(len(lines), crossings)
        cross_in = crossings_inside_banks(lines, crossings, intervals)
        for r in records:
            r["cross"] = r["cross_in"] = None
        for i, c, ci in zip(idx, cross, cross_in, strict=True):
            records[i]["cross"], records[i]["cross_in"] = int(c), int(ci)

    def _sink(self, parameters, context, name, spec, wkb_type, crs):
        fields = _fields(spec)
        sink, dest_id = self.parameterAsSink(parameters, name, context, fields, wkb_type, crs)
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, name))
        return sink, dest_id, fields

    def _write_sections(self, parameters, context, records, crs):
        sink, dest_id, fields = self._sink(parameters, context, "OUTPUT_SECTIONS",
                                           SECTION_FIELDS, QgsWkbTypes.LineString, crs)
        for r in records:
            res = r["result"]
            lev = res.level if res is not None else None
            g = res.geometry if res is not None else None
            feat = QgsFeature(fields)
            feat.setGeometry(r["geometry"])
            feat.setAttributes([
                r["sec_id"], r["axis_fid"], r["part"], r["chainage"], r["status"],
                lev.level if lev else None, lev.level_min if lev else None,
                lev.level_max if lev else None, lev.n_runs_ok if lev else None,
                lev.options.n_runs if lev else None,
                g.left if g else None, g.right if g else None, g.width if g else None,
                g.area if g else None, g.mean_depth if g else None,
                g.max_depth if g else None, r["thalweg_z"],
                g.n_wet_polygons if g else None,
                int(g.touches_left_edge) if g else None,
                int(g.touches_right_edge) if g else None,
                r["cross"], r["cross_in"], r["n_pts"],
            ])
            sink.addFeature(feat, QgsFeatureSink.FastInsert)
        return dest_id

    def _write_banks(self, parameters, context, records, crs):
        sink, dest_id, fields = self._sink(parameters, context, "OUTPUT_BANKS",
                                           BANK_FIELDS, QgsWkbTypes.Point, crs)
        for r in records:
            res = r["result"]
            if res is None or res.geometry is None:
                continue
            g = res.geometry
            for side, xy, dist, edge in (("L", res.left_xy, g.left, g.touches_left_edge),
                                         ("R", res.right_xy, g.right, g.touches_right_edge)):
                feat = QgsFeature(fields)
                feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(*xy)))
                feat.setAttributes([r["sec_id"], side, r["chainage"], dist, g.level,
                                    int(edge)])
                sink.addFeature(feat, QgsFeatureSink.FastInsert)
        return dest_id

    def _write_channel(self, parameters, context, records, crs, from_axis, edge_in_polygon,
                       feedback):
        sink, dest_id, fields = self._sink(parameters, context, "OUTPUT_CHANNEL",
                                           CHANNEL_FIELDS, QgsWkbTypes.Polygon, crs)
        groups = {}
        for r in records:
            key = (r["axis_fid"], r["part"]) if from_axis else (None, 0)
            groups.setdefault(key, []).append(r)
        polygons = []
        for (axis_fid, part), recs in groups.items():
            lefts, rights = [], []
            for r in recs:
                res = r["result"]
                g = res.geometry if res is not None else None
                usable = g is not None and (
                    edge_in_polygon or not (g.touches_left_edge or g.touches_right_edge))
                lefts.append(res.left_xy if usable else None)
                rights.append(res.right_xy if usable else None)
            label = (f"axis {axis_fid} part {part}" if from_axis else "sections")
            try:
                poly = channel_polygon(lefts, rights)
            except ValueError as exc:
                feedback.pushWarning(tr(f"Channel polygon ({label}) not built: {exc}"))
                continue
            feat = QgsFeature(fields)
            feat.setGeometry(QgsGeometry.fromWkt(poly.polygon.wkt))
            feat.setAttributes([axis_fid, part, len(poly.used), len(poly.skipped),
                                int(poly.is_valid),
                                (poly.invalid_reason or "")[:254] or None])
            sink.addFeature(feat, QgsFeatureSink.FastInsert)
            polygons.append((label, poly))
        return dest_id, polygons

    @staticmethod
    def _summary(feedback, records, polygons, canceled):
        counts = Counter(r["status"] for r in records)
        feedback.pushInfo(tr("Sections by status: " + ", ".join(
            f"{status} {n}" for status, n in sorted(counts.items()))))
        n_edge = sum(1 for r in records if r["result"] is not None
                     and r["result"].geometry is not None
                     and (r["result"].geometry.touches_left_edge
                          or r["result"].geometry.touches_right_edge))
        n_ok = counts.get(STATUS_OK, 0)
        msg = tr(f"Sections with a bank on the section edge (edge_l / edge_r): "
                 f"{n_edge} of {n_ok}.")
        if n_edge:
            feedback.pushWarning(msg + " " + tr(
                "Their banks are not inside the section: if they are many, increase the "
                "section width."))
        else:
            feedback.pushInfo(msg)
        n_cross = sum(1 for r in records if r["cross"])
        n_cross_in = sum(1 for r in records if r["cross_in"])
        feedback.pushInfo(tr(f"Crossing sections: cross {n_cross}, cross_in {n_cross_in}."))
        for label, poly in polygons:
            if poly.is_valid:
                feedback.pushInfo(tr(
                    f"Channel polygon ({label}): valid, {len(poly.used)} sections used, "
                    f"{len(poly.skipped)} skipped."))
            else:
                feedback.pushWarning(tr(
                    f"Channel polygon ({label}) is NOT valid: {poly.invalid_reason}. "
                    "It is written as built; check the sections with cross_in = 1."))
        if canceled:
            feedback.pushWarning(tr(
                f"Cancelled: the outputs contain the {len(records)} sections processed."))


class _SilentProgress:
    """Feedback proxy for the section generation: progress mapped to 0-5 %."""

    def __init__(self, feedback):
        self._feedback = feedback

    def setProgress(self, value):
        self._feedback.setProgress(value * 0.05)

    def __getattr__(self, name):
        return getattr(self._feedback, name)