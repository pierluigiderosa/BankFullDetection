"""Help texts shared by the Processing algorithms."""

AXIS_DIRECTION_HELP = (
    "<p><b>Axis direction.</b> The river axis must be digitised from upstream to "
    "downstream. Left and right in the outputs (fields <i>side</i>, <i>left_d</i>, "
    "<i>right_d</i>, <i>edge_l</i>, <i>edge_r</i>) are the hydrographic left and right, "
    "i.e. looking downstream. With an axis digitised the other way the bankfull level "
    "does not change, but left and right are swapped. Each section goes from the left "
    "end (first vertex) to the right end.</p>"
)

USER_SECTIONS_HELP = (
    "<p><b>Sections supplied by the user.</b> Each section must be digitised from the "
    "hydrographic left bank to the right bank (first vertex = left).</p>"
)

WIDTH_HELP = (
    "Total width of the section, half on each side of the axis. If many sections have a "
    "bank on the section edge (touches_left_edge / touches_right_edge), increase it."
)

CRS_HELP = (
    "<p>The axis layer must be in a projected CRS in metres; the outputs use the same "
    "CRS.</p>"
)

CITATION_HELP = (
    "<p>Method: De Rosa, P., Fredduzzi, A., Cencetti, C. (2019). A GIS-based tool for "
    "automatic bankfull detection from airborne high resolution DEM. ISPRS International "
    "Journal of Geo-Information, 8(11), 480. https://doi.org/10.3390/ijgi8110480</p>"
)
