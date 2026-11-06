"""
Generate tests/data/sections/synthetic.csv: four deterministic synthetic cross-sections.

  1  simple trapezoid
  2  trapezoid with an inner bench on the left bank
  3  two side-by-side depressions separated by a bar
  4  smooth parabola, no clear banks

Each profile is defined by breakpoints (distance, z) and sampled every STEP metres
with linear interpolation (section 4 is analytic).
"""
import csv
from pathlib import Path

import numpy as np

STEP = 0.5
OUT = Path(__file__).resolve().parent.parent / "tests" / "data" / "sections" / "synthetic.csv"

# Floodplains rise gently from z=3 to z=4 over 30 m so that the A/W maximum
# is inside the depth range and not at its upper end.
BREAKPOINTS = {
    1: [(0, 4), (30, 3), (36, 0), (46, 0), (52, 3), (82, 4)],
    2: [(0, 4), (30, 3), (33, 1.5), (38, 1.5), (41, 0), (51, 0), (57, 3), (87, 4)],
    3: [(0, 4), (30, 3), (36, 0), (42, 0), (45, 2), (48, 2), (51, 0.5),
        (57, 0.5), (62, 3), (92, 4)],
}


def sample(points):
    d, z = np.array(points, dtype=float).T
    x = np.arange(0.0, d[-1] + STEP / 2, STEP)
    return x, np.interp(x, d, z)


def main():
    rows = []
    for sid, pts in BREAKPOINTS.items():
        x, z = sample(pts)
        rows += [(sid, xi, zi) for xi, zi in zip(x, z)]
    x = np.arange(0.0, 80.0 + STEP / 2, STEP)
    z = 4.0 * ((x - 40.0) / 40.0) ** 2
    rows += [(4, xi, zi) for xi, zi in zip(x, z)]

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["section_id", "distance", "z"])
        for sid, xi, zi in rows:
            w.writerow([sid, f"{xi:.3f}", f"{zi:.3f}"])
    print(f"Written {len(rows)} points to {OUT}")


if __name__ == "__main__":
    main()
