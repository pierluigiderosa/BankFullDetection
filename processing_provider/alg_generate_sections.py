"""Processing algorithm: cross-sections along a river axis."""

from qgis.core import (
    QgsFeature,
    QgsFeatureSink,
    QgsFields,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsWkbTypes,
)

from ..bankfull_core.sections import (
    crossing_flags,
    drop_crossing_sections,
    find_crossings,
)
from ..bankfull_core.sections import generate_sections as core_generate_sections
from .qgis_io import (
    check_metric_crs,
    line_geometry_to_shapely,
    make_field,
    polyline_geometry,
    tr,
)
from .texts import AXIS_DIRECTION_HELP, CITATION_HELP, CRS_HELP, WIDTH_HELP

CROSSING_OPTIONS = ("Flag (keep, cross = 1)", "Drop (greedy, along the axis)")
CROSSING_FLAG, CROSSING_DROP = 0, 1


def section_fields():
    """Fields of the generated sections layer."""
    fields = QgsFields()
    fields.append(make_field("sec_id", "int"))
    fields.append(make_field("axis_fid", "long"))
    fields.append(make_field("part", "int"))
    fields.append(make_field("chainage", "double"))
    fields.append(make_field("azimuth", "double"))
    fields.append(make_field("cross", "int"))
    return fields


def add_section_parameters(alg):
    """STEP, WIDTH and the advanced OFFSET, TANGENT_LENGTH, CROSSING (shared with detection)."""
    alg.addParameter(QgsProcessingParameterNumber(
        "STEP", tr("Distance between sections along the axis [m]"),
        QgsProcessingParameterNumber.Double, defaultValue=50.0, minValue=0.01))
    width = QgsProcessingParameterNumber(
        "WIDTH", tr("Section width [m] (total, half on each side)"),
        QgsProcessingParameterNumber.Double, defaultValue=500.0, minValue=0.01)
    width.setHelp(tr(WIDTH_HELP))
    alg.addParameter(width)
    advanced = [
        QgsProcessingParameterNumber(
            "OFFSET", tr("Chainage of the first section [m] (-1 = step / 2)"),
            QgsProcessingParameterNumber.Double, defaultValue=-1.0, minValue=-1.0),
        QgsProcessingParameterNumber(
            "TANGENT_LENGTH", tr("Length of the axis window for the direction [m] (0 = step)"),
            QgsProcessingParameterNumber.Double, defaultValue=0.0, minValue=0.0),
        QgsProcessingParameterEnum(
            "CROSSING", tr("Crossing sections"), options=[tr(o) for o in CROSSING_OPTIONS],
            defaultValue=CROSSING_FLAG),
    ]
    for param in advanced:
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        alg.addParameter(param)


def section_options(alg, parameters, context):
    """(step, width, offset, tangent_length, drop) from the parameters."""
    step = alg.parameterAsDouble(parameters, "STEP", context)
    width = alg.parameterAsDouble(parameters, "WIDTH", context)
    offset = alg.parameterAsDouble(parameters, "OFFSET", context)
    tangent = alg.parameterAsDouble(parameters, "TANGENT_LENGTH", context)
    if offset < 0 and offset != -1:
        raise QgsProcessingException(tr("OFFSET must be >= 0, or -1 for step / 2."))
    drop = alg.parameterAsEnum(parameters, "CROSSING", context) == CROSSING_DROP
    return step, width, (None if offset == -1 else offset), (tangent or None), drop


def generate_from_axis(source, step, width, offset, tangent_length, drop, feedback,
                       progress_span=100.0):
    """Sections of every axis feature, with crossing flags.

    Returns:
        (records, n_crossing, n_dropped): records are dicts with ``axis_fid``, ``section``
        (core Section) and ``cross`` (bool), in axis feature order then chainage.
    """
    total = source.featureCount() or 1
    records = []
    for k, feat in enumerate(source.getFeatures()):
        if feedback.isCanceled():
            break
        axis = line_geometry_to_shapely(feat.geometry())
        if axis is None:
            feedback.pushWarning(tr(f"Axis feature {feat.id()}: empty geometry, skipped."))
            continue
        try:
            secs = core_generate_sections(axis, step, width, offset=offset,
                                          tangent_length=tangent_length)
        except ValueError as exc:
            feedback.pushWarning(tr(f"Axis feature {feat.id()}: {exc}; skipped."))
            continue
        records += [{"axis_fid": feat.id(), "section": s} for s in secs]
        feedback.setProgress(progress_span * (k + 1) / total)

    lines = [r["section"].coords for r in records]
    n_dropped = 0
    if drop and records:
        kept, dropped = drop_crossing_sections(lines)
        n_dropped = len(dropped)
        records = [records[i] for i in kept]
        lines = [lines[i] for i in kept]
    flags = crossing_flags(len(records), find_crossings(lines))
    for rec, flag in zip(records, flags, strict=True):
        rec["cross"] = flag
    return records, sum(flags), n_dropped


class GenerateSectionsAlgorithm(QgsProcessingAlgorithm):
    """Cross-sections perpendicular to a river axis (``bankfull_core.generate_sections``)."""

    def name(self):
        return "generatesections"

    def displayName(self):
        return tr("Generate cross-sections")

    def group(self):
        return ""

    def groupId(self):
        return ""

    def shortHelpString(self):
        return tr(
            "<p>Generates cross-sections perpendicular to a river axis, every <i>step</i> "
            "metres along it, <i>width</i> metres long in total (half on each side). The "
            "direction at each section is averaged over a window along the axis. Contiguous "
            "parts of a multi-part axis with the same direction are merged; the other parts "
            "get their own chainage from 0 (field <i>part</i>).</p>"
            "<p>Sections that cross other sections (tight bends) are flagged with "
            "<i>cross</i> = 1, or dropped in order along the axis if requested.</p>"
            "<p>Use it to check or edit the sections before the bankfull detection.</p>"
        ) + tr(AXIS_DIRECTION_HELP) + tr(CRS_HELP) + tr(CITATION_HELP)

    def createInstance(self):
        return GenerateSectionsAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            "AXIS", tr("River axis (digitised from upstream to downstream)"),
            [QgsProcessing.TypeVectorLine]))
        add_section_parameters(self)
        self.addParameter(QgsProcessingParameterFeatureSink(
            "OUTPUT", tr("Cross-sections"), QgsProcessing.TypeVectorLine))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, "AXIS", context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, "AXIS"))
        crs = source.sourceCrs()
        check_metric_crs(crs, tr("River axis"))
        step, width, offset, tangent, drop = section_options(self, parameters, context)

        records, n_cross, n_dropped = generate_from_axis(
            source, step, width, offset, tangent, drop, feedback, progress_span=90.0)

        fields = section_fields()
        sink, dest_id = self.parameterAsSink(parameters, "OUTPUT", context, fields,
                                             QgsWkbTypes.LineString, crs)
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, "OUTPUT"))
        for sec_id, rec in enumerate(records, start=1):
            if feedback.isCanceled():
                break
            s = rec["section"]
            feat = QgsFeature(fields)
            feat.setGeometry(polyline_geometry(s.coords))
            feat.setAttributes([sec_id, rec["axis_fid"], s.part, s.chainage, s.azimuth,
                                int(rec["cross"])])
            sink.addFeature(feat, QgsFeatureSink.FastInsert)
        feedback.setProgress(100)

        feedback.pushInfo(tr(f"{len(records)} sections generated."))
        if drop:
            feedback.pushInfo(tr(f"{n_dropped} crossing sections dropped."))
        elif n_cross:
            feedback.pushWarning(tr(
                f"{n_cross} sections cross other sections (cross = 1). Consider a smaller "
                "width, a larger step or CROSSING = Drop."))
        if feedback.isCanceled():
            feedback.pushWarning(tr("Cancelled: the output is incomplete."))
        return {"OUTPUT": dest_id}