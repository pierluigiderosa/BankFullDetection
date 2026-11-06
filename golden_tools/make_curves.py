"""
Step 1 of the golden pipeline: depth -> hydraulic depth (A/W) curves.

Reads every tests/data/sections/*.csv (section_id, distance, z) and reproduces the
depth loop of the original mainFun (see original_mainfun.py), nVsteps = 100.

Outputs (tests/data/golden/):
  curves.csv       source_file, section_id, seq, step, depth, hyd_depth, hyd_radius
  curves_meta.csv  source_file, section_id, seq, n_points, minx, maxx, minY, maxY,
                   terrace_ok, error
`seq` is the 1-based progressive index of the section over all files
(files in alphabetical order, sections in order of first appearance); R uses it for the seed.
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from original_mainfun import hydraulic_curve, terrace_index

NVSTEPS = 100
ROOT = Path(__file__).resolve().parent.parent
SECTIONS_DIR = ROOT / "tests" / "data" / "sections"
GOLDEN_DIR = ROOT / "tests" / "data" / "golden"


def read_sections(path):
    """Return {section_id: [(distance, z), ...]} keeping file order of points."""
    sections = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = int(row["section_id"])
            sections.setdefault(sid, []).append((float(row["distance"]), float(row["z"])))
    return sections


def main():
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    curves, meta = [], []
    seq = 0
    for path in sorted(SECTIONS_DIR.glob("*.csv")):
        for sid, points in read_sections(path).items():
            seq += 1
            d, z = np.array(points).T
            info = {"source_file": path.name, "section_id": sid, "seq": seq,
                    "n_points": len(points), "minx": d.min(), "maxx": d.max(),
                    "minY": z.min(), "maxY": z.max(), "terrace_ok": "", "error": ""}
            try:
                depts, hyd_rad, hyd_dep, _ = hydraulic_curve(points, NVSTEPS)
            except Exception as exc:  # noqa: BLE001 - recorded, the other sections go on
                info["error"] = f"{type(exc).__name__}: {exc}"
                meta.append(info)
                print(f"ERROR {path.name} section {sid}: {info['error']}")
                continue
            try:
                terrace_index(hyd_dep)
                info["terrace_ok"] = 1
            except (IndexError, ValueError):
                info["terrace_ok"] = 0
            for k, (h, hd, hr) in enumerate(zip(depts, hyd_dep, hyd_rad), start=1):
                curves.append((path.name, sid, seq, k, repr(float(h)), repr(float(hd)),
                               repr(float(hr))))
            meta.append(info)

    with open(GOLDEN_DIR / "curves.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_file", "section_id", "seq", "step", "depth", "hyd_depth", "hyd_radius"])
        w.writerows(curves)
    with open(GOLDEN_DIR / "curves_meta.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(meta[0].keys()))
        w.writeheader()
        w.writerows(meta)
    n_err = sum(1 for m in meta if m["error"])
    print(f"{len(meta)} sections, {n_err} errors, {len(curves)} curve rows -> {GOLDEN_DIR}")


if __name__ == "__main__":
    main()
