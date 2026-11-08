# Cross-sections and DTM sampling (`bankfull_core/sections.py`, `bankfull_core/sampling.py`)

Generation of cross-sections along a river axis, crossing checks, sampling stations and
NoData handling. Pure Python (numpy, Shapely 2), no QGIS: the QGIS layer only reads the DTM
at the stations. Tests: `tests/test_sections.py`, `tests/test_crossings.py`,
`tests/test_sampling.py`.

## Axis direction, left and right — read this first
- **The axis must be digitised from upstream to downstream.**
- **Left and right** in every result (`Section.coords`, and in the Processing outputs the
  fields `side`, `left_d`, `right_d`, `edge_l`, `edge_r`) are the **hydrographic** left and
  right, i.e. looking downstream.
- With an axis digitised the other way **the bankfull level does not change, but left and
  right are swapped**.
- With sections supplied by the user (Processing parameter `SECTIONS`), **each section must be
  digitised from the hydrographic left bank to the right bank**: its first vertex is the left end.

There is no parameter to reverse the axis: the direction is the user's responsibility.

## Functions
| Function | Returns |
|---|---|
| `generate_sections(axis, step, width, *, offset=None, tangent_length=None)` | tuple of `Section` |
| `find_crossings(section_lines)` | tuple of `Crossing(first, second, points)` |
| `crossing_flags(n_sections, crossings)` | per section: part of a crossing (`cross`) |
| `drop_crossing_sections(section_lines)` | `(kept, dropped)` indices |
| `crossings_inside_banks(section_lines, crossings, bank_intervals)` | per section: crossing between the banks (`cross_in`) |
| `stations(line_coords, spacing)` | `(distances, xy)` sampling stations |
| `trim_nodata(distances, z, valid)` | `SampledSection` or `NoDataError` |

All results are frozen dataclasses or tuples; inputs are never modified.

## Section generation
- **Width**: `width` is the **total** length of the section, `width / 2` on each side of the
  axis. If many sections have a bank on the section edge (`touches_left_edge` /
  `touches_right_edge`), increase it.
- **Position**: chainages `offset + k·step` up to the length of the axis part, `offset` by
  default `step / 2` (every section at least `step / 2` from the ends, where the tangent window
  is truncated). A part shorter than `step` (or than `offset`) gets one section at its midpoint.
- **Direction**: the tangent at chainage `c` is the vector between the axis points at
  `c ± tangent_length / 2` (default `tangent_length = step`), clamped to the ends of the part.
  The section is perpendicular to it. `Section.azimuth` is the axis direction in degrees
  clockwise from north.
- **Multi-part axes**: contiguous parts with the same direction are merged
  (`shapely.line_merge(directed=True)`, GEOS ≥ 3.11). Parts in opposite directions are never
  merged, because that would reverse one of them and swap its left and right. Remaining parts
  are numbered (`part`) in input order, each with its own chainage from 0.
- Z values are ignored. Invalid parameters or an empty, non-linear or zero-length axis raise
  `ValueError`.

### Defects of the legacy `tools/XSGenerator.py` that are not reproduced
- `width` was used on each side: sections were twice as long as the value in the dialog.
- The direction was that of the single axis segment: sections jumped at vertices and were
  skewed on jagged axes (e.g. derived from the DTM). Here a 50 m window keeps the direction
  within 3° on an axis zig-zagging by ±1 m every metre, where the segment direction swings by ±63°.
- `asPolyline()` failed on Multi geometries, which are the norm for axes loaded from shapefile
  or GeoPackage in QGIS 3.
- The chainage was not stored; the memory layers had no CRS.

## Crossings in tight bends
Sections wider than twice the bend radius cross on the inner side of the bend.
`find_crossings` uses an STRtree and reports every intersecting pair (touching included) with
its points (a polyline crossing twice gives two points; a collinear overlap gives the vertices
of the shared stretch).

The bankfull computation of each section is independent of the others, so crossing sections
are **kept and flagged** by default (`cross`). `drop_crossing_sections` removes them greedily
in input order: a section is kept if it crosses none of those already kept, so the earlier one
(lower chainage) wins.

`crossings_inside_banks` (`cross_in`): for each crossing point, the distance along each of the
two sections from its first vertex (the same distance as the section profile) is compared with
that section's bank interval `[left, right]`, closed. If the point lies inside the interval of
at least one of the two sections, both are flagged. Only these crossings can make the channel
polygon invalid; crossings outside the banks are harmless.

## Sampling stations
`stations` splits each segment of the section line into `ceil(length / spacing)` equal parts
and keeps every vertex, as `QgsGeometry.densifyByDistance` (and
`golden_tools/export_sections_qgis.py`). Distances are cumulative 2D distances from the first
vertex; repeated vertices are skipped so that they are strictly increasing.

## NoData
`trim_nodata` (NaN counts as NoData):
- NoData at the **start and end** (the section extends beyond the DTM) are removed. Distances
  keep their origin at the first vertex of the whole line, so bank distances still map to the
  right point with `detect_bankfull(line_coords=...)`. The numbers removed are reported.
- NoData **between valid values** are not interpolated: `NoDataError` with `n_interior`.
- Fewer than 3 valid values: `NoDataError`.

`NoDataError` is a `ValueError`.

A section trimmed at one end may then have its bank on the trimmed edge: `touches_left_edge` /
`touches_right_edge` then mean "the bank is not inside the sampled part of the section".

## End-to-end check without QGIS
`tests/test_sampling.py` generates sections on a straight axis (also rotated by 30°), samples
an analytic trapezoidal channel (bed 10 m, bank top 14 m at 20 m from the axis, plain rising
gently) with leading NoData on the left, and runs `detect_bankfull`: level 13.955 m with the
original and the recommended options, banks at ±19.9 m from the axis on the expected sides.