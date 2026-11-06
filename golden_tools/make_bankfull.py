"""
Step 3 of the golden pipeline: bankfull choice with the original Python logic.

For each section and each minVdep in MINVDEPS, applies to the R local maxima the rule of
the original mainFun: first maximum (in R order) with hydraulic depth >= minVdep;
if R returned no maxima, the original fallback [x[-1]], [y[-1]] (last curve point) is used.
The wet area at that level gives the banks (bounds of the largest polygon) and the
number of channels, exactly as in mainFun.

Output tests/data/golden/bankfull.csv:
  source_file, section_id, minVdep, bankfull_z, left_dist, right_dist, n_channels, error,
  bankfull_hyd_depth, note
error codes: curve_error, r_error, r_no_local_max (R roots found but none is a maximum:
the original fails), no_max_ge_minvdep (IndexError in the original).
note: fallback_last_point, terrace_crash (the original mainFun would raise on terrace[0]).
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_curves import GOLDEN_DIR, SECTIONS_DIR, read_sections
from original_mainfun import build_polygons, wet_area_stats

MINVDEPS = (1.0, 0.2)


def read_csv(name):
    with open(GOLDEN_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def key(row):
    return row["source_file"], int(row["section_id"])


def main():
    meta = {key(r): r for r in read_csv("curves_meta.csv")}
    summary = {key(r): r for r in read_csv("r_summary.csv")}
    maxima = {}
    for r in read_csv("r_maxima.csv"):
        maxima.setdefault(key(r), []).append((int(r["k"]), float(r["x"]), float(r["y"])))
    last_point = {}
    for r in read_csv("r_fitted.csv"):  # rows are in point order: keep the last one
        last_point[key(r)] = (float(r["x"]), float(r["y"]))

    out = []
    for path in sorted(SECTIONS_DIR.glob("*.csv")):
        for sid, points in read_sections(path).items():
            k = (path.name, sid)
            m = meta.get(k)
            s = summary.get(k)
            notes = []
            if m is not None and m["terrace_ok"] == "0":
                notes.append("terrace_crash")
            for minVdep in MINVDEPS:
                row = {"source_file": path.name, "section_id": sid, "minVdep": minVdep,
                       "bankfull_z": "", "left_dist": "", "right_dist": "", "n_channels": "",
                       "error": "", "bankfull_hyd_depth": "", "note": ""}
                local_notes = list(notes)
                if m is None or m["error"]:
                    row["error"] = "curve_error"
                elif s is None or s["status"] != "ok":
                    row["error"] = "r_error"
                elif s["out_kind"] == "list_empty":
                    # len(out) == 2 in rpy2, so runAlg skips its fallback and returns
                    # empty R vectors: the `>= minVdep` filter fails in the original.
                    row["error"] = "r_no_local_max"
                else:
                    lm = sorted(maxima.get(k, []))
                    if lm:
                        deptsLM = [x for _, x, _ in lm]
                        HydDeptLM = [y for _, _, y in lm]
                    else:
                        # runAlg: `return [x[-1]], [y[-1]], spar[0]`
                        deptsLM = [last_point[k][0]]
                        HydDeptLM = [last_point[k][1]]
                        local_notes.append("fallback_last_point")
                    max_loc_filtered = [i for i in range(len(HydDeptLM))
                                        if HydDeptLM[i] >= minVdep]
                    if not max_loc_filtered:
                        row["error"] = "no_max_ge_minvdep"
                    else:
                        bankfullIndex = max_loc_filtered[0]
                        h = deptsLM[bankfullIndex]
                        orig, _, polyXS = build_polygons(points)
                        left, right, nchannel, _ = wet_area_stats(orig, polyXS, h)
                        row.update(bankfull_z=repr(h), left_dist=repr(float(left)),
                                   right_dist=repr(float(right)), n_channels=nchannel,
                                   bankfull_hyd_depth=repr(HydDeptLM[bankfullIndex]))
                row["note"] = ";".join(local_notes)
                out.append(row)

    with open(GOLDEN_DIR / "bankfull.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    n_err = sum(1 for r in out if r["error"])
    print(f"{len(out)} rows, {n_err} with error -> {GOLDEN_DIR / 'bankfull.csv'}")


if __name__ == "__main__":
    main()