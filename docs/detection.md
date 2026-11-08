# Channel geometry at bankfull (`bankfull_core/detection.py`)

Derives the channel geometry from the bankfull level of `compute_bankfull_level`
(`bankfull_core/level.py`). Pure Python (numpy, Shapely 2), no QGIS. Tests: `tests/test_detection.py`.

## Functions
| Function | Returns |
|---|---|
| `bank_geometry(points, level, options=None)` | `BankGeometry` at a given level |
| `detect_bankfull(points, options=None, line_coords=None)` | `BankfullDetection`: `BankfullLevel` + `BankGeometry` + bank points in map coordinates |
| `channel_polygon(left_points, right_points)` | `ChannelPolygon`: channel outline from several sections |

All result dataclasses are frozen; the input points are never modified.

## What `bank_geometry` computes
The wet polygons are built as in `hydraulic_curve`: the section closed at the top
(`max z + 1`) intersected with the box from `min z` to the level. Of the chosen wet polygon:

- `left`, `right`: section distances of its ends (the banks); `width = right − left`;
- `area`; `mean_depth = area / width`; `max_depth = level − min z`;
- `n_wet_polygons`: number of disjoint wet polygons in the whole section at that level;
- `wet_polygon`: the polygon itself, in section coordinates (distance, z).

The level must satisfy `min z < level <= max z`. At a level equal to a flat bank top the
water stops at the first point at that elevation (it does not spread over the flat).

## Which polygon, and why
The polygon containing the **lowest point of the section** (if the lowest elevation occurs in
several polygons, the first in Shapely's order), for both `multichannel` options. This is the
main channel: it is the polygon whose A/W is used with `multichannel="thalweg"`, and a wide
flooded floodplain cannot take its place.

The original `mainFun` (`wet_area_stats` in `golden_tools/original_mainfun.py`) took the
polygon with the **largest area**. The two rules differ only when another wet polygon is larger
than the one with the thalweg; on all 22 valid rows of `tests/data/golden/bankfull.csv` they
choose the same polygon, and banks and number of polygons match the golden data within 1e-12.

## Edge flags
`touches_left_edge` / `touches_right_edge` are True when the chosen polygon reaches the first /
last point of the section (within 1e-9). The bank on that side lies outside the section: the
section is too short, `width` and `area` are lower bounds and the bank distance is the end of
the section, not a bank. Such results should be reported, not used as they are.

## Map coordinates
With `line_coords`, the (x, y) vertices of the section line from its first to its last point,
each bank distance is taken as a distance along the line (as in
`golden_tools/export_sections_qgis.py`) and converted with `LineString.interpolate`; this works
on polylines too. Distances up to 1e-3 map units beyond the ends (rounding of exported
distances) are clamped; farther ones raise `ValueError`, as do lines with fewer than 2 points or
zero length. Without a bankfull level `geometry`, `left_xy` and `right_xy` are None and `status`
gives the reason.

## Channel polygon
`channel_polygon` joins the left banks in input order, then the right banks in reverse order.
A section with a missing bank (`None`) is skipped and listed in `skipped`; fewer than 2 remaining
sections raise `ValueError`. Sections must be ordered along the river and drawn in the same
direction (left bank on the same side); otherwise the outline can cross itself. The polygon is
never repaired: `is_valid` is False and `invalid_reason` gives
`shapely.validation.explain_validity`.