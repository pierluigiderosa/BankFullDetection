"""Compare the options of the bankfull method with the expert estimates.

For every real section with at least one expert estimate
(``tests/data/expert/expert_bankfull.csv``) the bankfull level is computed for all the
combinations of multichannel mode, spar selection, minimum hydraulic depth and criterion
for choosing the maximum, with numpy CV folds and seeds 0-10.

Criteria (among the smoothed maxima with A/W >= min_hyd_depth):
- "first": lowest maximum, as the core (``bankfull_core.smoothing.pick_bankfull``);
- "highest": maximum with the largest smoothed A/W;
- "prominent": maximum with the largest prominence, i.e. its smoothed A/W minus the higher
  of the two adjacent minima of the smoothed curve. The adjacent minimum on each side is
  the minimum of the spline between the maximum and the neighbouring maximum, or the end
  of the curve where there is none.

Outputs ``docs/confronto-opzioni.csv`` and ``docs/confronto-opzioni.md``.
The core is not modified; this script is an analysis tool, not part of the plugin.

Run with the QGIS Python interpreter from the repository root:
    python analysis/compare_expert.py
"""

import csv
import itertools
import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, box

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bankfull_core import BankfullOptions, hydraulic_curve, smooth_curve
from bankfull_core.smoothing import pick_bankfull

SECTIONS_DIR = REPO / "tests" / "data" / "sections"
EXPERT_CSV = REPO / "tests" / "data" / "expert" / "expert_bankfull.csv"
OUT_CSV = REPO / "docs" / "confronto-opzioni.csv"
OUT_MD = REPO / "docs" / "confronto-opzioni.md"

MULTICHANNEL = ("original", "thalweg")
SELECTION = ("min_cv", "one_se")
MIN_HYD_DEPTH = (0.2, 1.0, 2.0, 3.0)
CRITERIA = ("first", "highest", "prominent")
SEEDS = tuple(range(11))
EXPERT_COLS = ("z_expert_low", "z_expert_high")
N_CLOSEST = 6
DIAG_RISE = 0.2

# Same construction as bankfull_core/hydraulics.py (top of the closed section polygon).
_TOP_EXTENSION = 1.0

COMBOS = list(itertools.product(MULTICHANNEL, SELECTION, MIN_HYD_DEPTH, CRITERIA))


# ---------------------------------------------------------------------------- input

def read_sections(path):
    """{section_id: [(distance, z), ...]} in file order."""
    sections = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = int(row["section_id"])
            sections.setdefault(sid, []).append((float(row["distance"]), float(row["z"])))
    return sections


def _float_or_nan(text):
    text = text.strip()
    return float(text) if text else math.nan


def read_expert():
    """Expert rows with at least one estimate, as dicts with float levels."""
    rows = []
    with open(EXPERT_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            levels = {c: _float_or_nan(row[c]) for c in EXPERT_COLS}
            if all(math.isnan(v) for v in levels.values()):
                continue
            rows.append({
                "source_file": row["source_file"],
                "section_id": int(row["section_id"]),
                **levels,
                "note": row["note"].strip(),
            })
    return rows


# ------------------------------------------------------------------------- criteria

def _min_on_interval(spline, a, b):
    """Exact minimum of the spline on [a, b] (end values and interior stationary points)."""
    st = spline.stationary_points()
    cands = np.concatenate([[a, b], st[(st > a) & (st < b)]])
    return float(np.min(spline(cands)))


def prominences(maxima, spline, x):
    """Prominence of each maximum (smoothed A/W minus the higher adjacent minimum)."""
    n = len(maxima)
    out = np.empty(n)
    for i in range(n):
        left = maxima[i - 1, 0] if i > 0 else x[0]
        right = maxima[i + 1, 0] if i < n - 1 else x[-1]
        lev, val = maxima[i]
        lmin = _min_on_interval(spline, left, lev)
        rmin = _min_on_interval(spline, lev, right)
        out[i] = val - max(lmin, rmin)
    return out


def choose(criterion, result, x, y, min_hyd_depth, prom):
    """Bankfull level for a criterion, or None."""
    if criterion == "first":
        level, _, _, _ = pick_bankfull(result.maxima, x, y, min_hyd_depth, "explicit")
        return level
    maxima = result.maxima
    ok = np.flatnonzero(maxima[:, 1] >= min_hyd_depth)
    if ok.size == 0:
        return None
    if criterion == "highest":
        best = ok[np.argmax(maxima[ok, 1])]
    elif criterion == "prominent":
        best = ok[np.argmax(prom[ok])]
    else:
        raise ValueError(criterion)
    return float(maxima[best, 0])


# ---------------------------------------------------------------------- diagnostics

def _section_polygon(points):
    minx = points[0][0]
    maxx = points[-1][0]
    zs = [p[1] for p in points]
    top = max(zs) + _TOP_EXTENSION
    return Polygon([(minx, top), *points, (maxx, top)]), minx, maxx, min(zs)


def _n_parts(geom):
    if geom.is_empty:
        return 0
    if geom.geom_type == "Polygon":
        return 1
    if geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        return sum(_n_parts(g) for g in geom.geoms)
    return 0


def wet_polygon_count(points, h):
    """Number of wet polygons at level h, same construction as the core."""
    poly, minx, maxx, min_z = _section_polygon(points)
    return _n_parts(poly.intersection(box(minx, min_z, maxx, h)))


def profile_local_minima(points):
    """(z, distance) of the local minima of the profile, ascending z.

    Runs of equal elevation are merged (distance of the first point of the run);
    the ends of the profile count when they are lower than their neighbour.
    """
    runs = [p for i, p in enumerate(points) if i == 0 or p[1] != points[i - 1][1]]
    out = []
    for i, (d, zi) in enumerate(runs):
        lower_left = i == 0 or zi < runs[i - 1][1]
        lower_right = i == len(runs) - 1 or zi < runs[i + 1][1]
        if lower_left and lower_right:
            out.append((zi, d))
    return np.array(sorted(out)).reshape(-1, 2)


# ------------------------------------------------------------------------ computing

def _stats(levels):
    vals = np.array([v for v in levels if v is not None], dtype=float)
    if vals.size == 0:
        return math.nan, math.nan, math.nan, 0
    return float(np.median(vals)), float(vals.min()), float(vals.max()), int(vals.size)


def compute():
    sections = {}
    for path in sorted(SECTIONS_DIR.glob("*.csv")):
        if path.name == "synthetic.csv":
            continue
        for sid, pts in read_sections(path).items():
            sections[(path.name, sid)] = pts

    experts = read_expert()
    rows = []
    for ex in experts:
        key = (ex["source_file"], ex["section_id"])
        pts = sections[key]
        print(f"{key[0]} {key[1]} ...", flush=True)
        per_combo = {c: [] for c in COMBOS}
        for mc in MULTICHANNEL:
            curve = hydraulic_curve(pts, BankfullOptions(multichannel=mc))
            x, y = curve.levels, curve.hyd_depth
            if mc == "original":
                counts = [wet_polygon_count(pts, h) for h in x]
                assert np.array_equal(counts, curve.n_wet_polygons), key
            for sel, seed in itertools.product(SELECTION, SEEDS):
                opts = BankfullOptions(multichannel=mc, selection=sel, seed=seed)
                res = smooth_curve(x, y, opts)
                core_level, _, _, _ = pick_bankfull(res.maxima, x, y, opts.min_hyd_depth)
                assert core_level == res.bankfull_level, (key, mc, sel, seed)
                prom = prominences(res.maxima, res.spline, x)
                for mhd, crit in itertools.product(MIN_HYD_DEPTH, CRITERIA):
                    per_combo[(mc, sel, mhd, crit)].append(
                        choose(crit, res, x, y, mhd, prom)
                    )
        for combo in COMBOS:
            med, lo, hi, n_ok = _stats(per_combo[combo])
            rows.append({
                "source_file": key[0], "section_id": key[1],
                "multichannel": combo[0], "selection": combo[1],
                "min_hyd_depth": combo[2], "criterion": combo[3],
                "z_expert_low": ex["z_expert_low"], "z_expert_high": ex["z_expert_high"],
                "level_median": med, "level_min": lo, "level_max": hi,
                "level_range": hi - lo, "n_seeds": len(SEEDS), "n_seeds_ok": n_ok,
                "err_low": med - ex["z_expert_low"], "err_high": med - ex["z_expert_high"],
            })
    return experts, sections, rows


# -------------------------------------------------------------------------- writing

CSV_COLS = ["source_file", "section_id", "multichannel", "selection", "min_hyd_depth",
            "criterion", "z_expert_low", "z_expert_high", "level_median", "level_min",
            "level_max", "level_range", "n_seeds", "n_seeds_ok", "err_low", "err_high"]


def _fmt(v, nd=3):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def write_csv(rows):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLS)
        for r in rows:
            w.writerow([
                _fmt(r[c], 1) if c == "min_hyd_depth" else _fmt(r[c]) for c in CSV_COLS
            ])


def _label(combo):
    mc, sel, mhd, crit = combo
    return f"{mc} / {sel} / {mhd:.1f} / {crit}"


def _md(v, nd=3):
    s = _fmt(v, nd)
    return s if s else "–"


def summary(rows, est):
    """Per combination metrics against one expert estimate, sorted by MAE."""
    err_col = "err_low" if est == "z_expert_low" else "err_high"
    out = []
    for combo in COMBOS:
        rs = [r for r in rows if (r["multichannel"], r["selection"], r["min_hyd_depth"],
                                  r["criterion"]) == combo and not math.isnan(r[est])]
        errs = np.array([r[err_col] for r in rs if r["n_seeds_ok"] > 0])
        ranges = np.array([r["level_range"] for r in rs if r["n_seeds_ok"] > 0])
        n_none = sum(1 for r in rs if r["n_seeds_ok"] == 0)
        n_partial = sum(1 for r in rs if 0 < r["n_seeds_ok"] < len(SEEDS))
        if errs.size:
            me, mae = float(errs.mean()), float(np.abs(errs).mean())
            rmse = float(np.sqrt(np.mean(errs ** 2)))
            w25 = int(np.sum(np.abs(errs) <= 0.25))
            w50 = int(np.sum(np.abs(errs) <= 0.50))
            rng = float(ranges.mean())
        else:
            me = mae = rmse = rng = math.nan
            w25 = w50 = 0
        out.append({"combo": combo, "n": int(errs.size), "me": me, "mae": mae,
                    "rmse": rmse, "w25": w25, "w50": w50, "none": n_none,
                    "partial": n_partial, "range": rng, "n_sections": len(rs)})
    out.sort(key=lambda s: (math.isnan(s["mae"]), s["mae"]))
    return out


def summary_table(rows, est):
    lines = [
        ("| # | multichannel / selection / min_hyd_depth / criterio | n | errore medio "
         "| errore medio ass. | RMSE | entro 0.25 m | entro 0.50 m | senza bankfull "
         "| seed parziali | ampiezza media seed |"),
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, s in enumerate(summary(rows, est), 1):
        lines.append(
            f"| {i} | {_label(s['combo'])} | {s['n']} | {_md(s['me'])} | {_md(s['mae'])} "
            f"| {_md(s['rmse'])} | {s['w25']} | {s['w50']} | {s['none']} "
            f"| {s['partial']} | {_md(s['range'])} |"
        )
    return lines


def closest_tables(experts, rows):
    lines = []
    for ex in experts:
        key = (ex["source_file"], ex["section_id"])
        rs = [r for r in rows if (r["source_file"], r["section_id"]) == key]
        lines.append(f"### {key[0]} sezione {key[1]}")
        lines.append("")
        lines.append(f"z_expert_low = {_md(ex['z_expert_low'], 2)} m, "
                     f"z_expert_high = {_md(ex['z_expert_high'], 2)} m")
        if ex["note"]:
            lines.append("")
            lines.append(f"Nota: {ex['note']}")
        lines.append("")
        for est, err_col in (("z_expert_low", "err_low"), ("z_expert_high", "err_high")):
            if math.isnan(ex[est]):
                lines.append(f"*{est}: stima assente.*")
                lines.append("")
                continue
            ok = [r for r in rs if r["n_seeds_ok"] > 0]
            ok.sort(key=lambda r: abs(r[err_col]))
            lines.append(f"Più vicine a {est}:")
            lines.append("")
            lines.append("| combinazione | mediana | min–max seed | seed ok | errore |")
            lines.append("|---|---|---|---|---|")
            for r in ok[:N_CLOSEST]:
                combo = (r["multichannel"], r["selection"], r["min_hyd_depth"],
                         r["criterion"])
                lines.append(
                    f"| {_label(combo)} | {_md(r['level_median'])} "
                    f"| {_md(r['level_min'])}–{_md(r['level_max'])} "
                    f"| {r['n_seeds_ok']}/{r['n_seeds']} | {_md(r[err_col])} |"
                )
            lines.append("")
    return lines


def diagnostics_table(experts, sections, rows):
    lines = [
        ("| sezione | selection | min_hyd_depth | z scelto (mediana) | poligoni a z "
         f"| poligoni a z + {DIAG_RISE} | prossimo minimo locale del profilo sopra z "
         "| Δ | distanza del minimo [m] |"),
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for ex in experts:
        key = (ex["source_file"], ex["section_id"])
        pts = sections[key]
        minima = profile_local_minima(pts)
        for sel, mhd in itertools.product(SELECTION, MIN_HYD_DEPTH):
            r = next(r for r in rows if (r["source_file"], r["section_id"]) == key
                     and r["multichannel"] == "original" and r["selection"] == sel
                     and r["min_hyd_depth"] == mhd and r["criterion"] == "first")
            z = r["level_median"]
            name = f"{key[0].removesuffix('.csv')} {key[1]}"
            if math.isnan(z):
                lines.append(f"| {name} | {sel} | {mhd:.1f} | – | – | – | – | – | – |")
                continue
            n0 = wet_polygon_count(pts, z)
            n1 = wet_polygon_count(pts, z + DIAG_RISE)
            above = minima[minima[:, 0] > z]
            nxt, dist = (float(above[0, 0]), float(above[0, 1])) if len(above) else (
                math.nan, math.nan)
            lines.append(
                f"| {name} | {sel} | {mhd:.1f} | {_md(z)} | {n0} | {n1} | {_md(nxt)} "
                f"| {_md(nxt - z)} | {_md(dist, 1)} |"
            )
    return lines


def write_md(experts, sections, rows):
    n = len(experts)
    lines = [
        "# Confronto delle opzioni del metodo con le stime esperte",
        "",
        "Generato da `analysis/compare_expert.py`; dati per riga in `docs/confronto-opzioni.csv`.",
        "",
        (f"**Le sezioni sono solo {n}: i risultati sono indicativi**, non una calibrazione. "
         "Le stime esperte (`tests/data/expert/expert_bankfull.csv`) sono valutazioni "
         "visive dell'autore."),
        "",
        "## Definizioni",
        "",
        ("- Combinazioni: multichannel (original, thalweg) × selection (min_cv, one_se) × "
         "min_hyd_depth (0.2, 1.0, 2.0, 3.0) × criterio (first, highest, prominent) = "
         f"{len(COMBOS)}. Tutti gli altri parametri ai default di `BankfullOptions`."),
        (f"- Fold CV casuali numpy, seed {SEEDS[0]}–{SEEDS[-1]} ({len(SEEDS)} run): i fold "
         "differiscono da quelli di R usati per i dati golden. Per ogni combinazione: "
         "mediana, minimo e massimo del livello sui seed che danno un bankfull."),
        ("- Criteri, tra i massimi della curva lisciata con A/W ≥ min_hyd_depth: "
         "**first** = il più basso (quello del core); **highest** = A/W lisciato più alto; "
         "**prominent** = prominenza più alta, con prominenza = A/W del massimo − il più "
         "alto dei due minimi adiacenti della curva lisciata. Il minimo adiacente di "
         "ciascun lato è il minimo della spline fino al massimo vicino o, se non c'è, fino "
         "all'estremo della curva (al bordo conta quindi il valore di fine curva se la "
         "curva è monotona)."),
        ("- Errore = livello mediano − stima esperta (positivo = metodo più alto). Errore "
         "medio, errore medio assoluto e RMSE sono calcolati sulle sezioni con bankfull "
         "(colonna n)."),
        ("- *Senza bankfull*: nessun seed dà un livello. *Seed parziali*: solo alcuni seed "
         "lo danno (la mediana è sui seed che lo danno). *Ampiezza media seed*: media di "
         "max − min."),
        "",
        "## Riepilogo rispetto a z_expert_low",
        "",
        *summary_table(rows, "z_expert_low"),
        "",
        "## Riepilogo rispetto a z_expert_high",
        "",
        *summary_table(rows, "z_expert_high"),
        "",
        f"## Le {N_CLOSEST} combinazioni più vicine per sezione",
        "",
        *closest_tables(experts, rows),
        "## Diagnostica dei poligoni bagnati (original, first)",
        "",
        ("Ipotesi da verificare: su Arno 3, 5, 6, 7 e 9 il livello scelto cade subito prima "
         "che si allaghi la piana dietro l'argine, più bassa delle sponde (vedi le note nel "
         "CSV esperto, riportate sopra). Per ogni livello scelto (mediana sui seed): numero "
         f"di poligoni bagnati a z e a z + {DIAG_RISE} m (stessa costruzione del core), e "
         "quota del prossimo minimo locale del profilo sopra z, dove si apre un nuovo "
         "poligono (Δ = quota − z)."),
        "",
        *diagnostics_table(experts, sections, rows),
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main():
    experts, sections, rows = compute()
    write_csv(rows)
    write_md(experts, sections, rows)
    print(f"wrote {OUT_CSV.relative_to(REPO)} ({len(rows)} rows) and "
          f"{OUT_MD.relative_to(REPO)}")


if __name__ == "__main__":
    main()
