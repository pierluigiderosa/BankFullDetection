"""Shared helpers for loading test sections and golden reference data."""

import csv
from pathlib import Path

import numpy as np
import pytest

DATA_DIR = Path(__file__).resolve().parent / "data"
SECTIONS_DIR = DATA_DIR / "sections"
GOLDEN_DIR = DATA_DIR / "golden"


def read_sections(path):
    """Return {section_id: [(distance, z), ...]} keeping the file order of points."""
    sections = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = int(row["section_id"])
            sections.setdefault(sid, []).append((float(row["distance"]), float(row["z"])))
    return sections


def read_golden_curves():
    """Return {(source_file, section_id): {"depth", "hyd_depth", "hyd_radius"}} arrays."""
    rows = {}
    with open(GOLDEN_DIR / "curves.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["source_file"], int(row["section_id"]))
            rows.setdefault(key, []).append(row)
    curves = {}
    for key, rs in rows.items():
        rs.sort(key=lambda r: int(r["step"]))
        curves[key] = {
            col: np.array([float(r[col]) for r in rs])
            for col in ("depth", "hyd_depth", "hyd_radius")
        }
    return curves


def read_golden_table(name):
    """Return {(source_file, section_id): [row dict, ...]} for a golden CSV, file order."""
    out = {}
    with open(GOLDEN_DIR / name, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.setdefault((row["source_file"], int(row["section_id"])), []).append(row)
    return out


def read_golden_fitted():
    """{key: (x, y, yhat)} from r_fitted.csv, ordered by point_index."""
    out = {}
    for key, rows in read_golden_table("r_fitted.csv").items():
        rows = sorted(rows, key=lambda r: int(r["point_index"]))
        out[key] = tuple(np.array([float(r[c]) for r in rows]) for c in ("x", "y", "yhat"))
    return out


def read_golden_fold_labels():
    """{key: 1-based fold label per point} from r_folds.csv, ordered by point_index."""
    return {
        key: [int(r["fold"]) for r in sorted(rows, key=lambda r: int(r["point_index"]))]
        for key, rows in read_golden_table("r_folds.csv").items()
    }


def read_golden_cv():
    """{key: {"spar", "cv_error", "se"} arrays} from r_cv.csv (grid order)."""
    return {
        key: {c: np.array([float(r[c]) for r in rows]) for c in ("spar", "cv_error", "se")}
        for key, rows in read_golden_table("r_cv.csv").items()
    }


def read_golden_maxima():
    """{key: (N, 2) array of R maxima (x, y)} in R order; sections without maxima absent."""
    return {
        key: np.array([[float(r["x"]), float(r["y"])]
                       for r in sorted(rows, key=lambda r: int(r["k"]))])
        for key, rows in read_golden_table("r_maxima.csv").items()
    }


def read_golden_summary():
    """{key: row dict} from r_summary.csv."""
    return {key: rows[0] for key, rows in read_golden_table("r_summary.csv").items()}


def read_golden_bankfull():
    """{(source_file, section_id, minVdep): row dict} from bankfull.csv."""
    return {
        (key[0], key[1], float(r["minVdep"])): r
        for key, rows in read_golden_table("bankfull.csv").items()
        for r in rows
    }


@pytest.fixture(scope="session")
def all_sections():
    """{(source_file, section_id): points} for every file in tests/data/sections."""
    out = {}
    for path in sorted(SECTIONS_DIR.glob("*.csv")):
        for sid, pts in read_sections(path).items():
            out[(path.name, sid)] = pts
    return out


@pytest.fixture(scope="session")
def synthetic():
    return read_sections(SECTIONS_DIR / "synthetic.csv")
