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
