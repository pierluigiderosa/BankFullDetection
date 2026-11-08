"""Consistency checks of the expert bankfull estimates (tests/data/expert)."""

import csv
import math

import pytest
from conftest import DATA_DIR, SECTIONS_DIR, read_sections

EXPERT_CSV = DATA_DIR / "expert" / "expert_bankfull.csv"
COLUMNS = ["source_file", "section_id", "z_expert", "note"]
SYNTHETIC = "synthetic.csv"


@pytest.fixture(scope="module")
def expert_rows():
    with open(EXPERT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)
    return header, rows


@pytest.fixture(scope="module")
def real_sections():
    """{(source_file, section_id): points} for the real (non-synthetic) sections."""
    out = {}
    for path in sorted(SECTIONS_DIR.glob("*.csv")):
        if path.name == SYNTHETIC:
            continue
        for sid, pts in read_sections(path).items():
            out[(path.name, sid)] = pts
    return out


def _key(row):
    return row["source_file"], int(row["section_id"])


def test_columns(expert_rows):
    header, rows = expert_rows
    assert header == COLUMNS
    assert all(None not in row for row in rows), "rows with extra fields"


def test_sections_exist_and_unique(expert_rows, real_sections):
    _, rows = expert_rows
    keys = [_key(r) for r in rows]
    missing = [k for k in keys if k not in real_sections]
    assert not missing, f"sections not found in tests/data/sections: {missing}"
    duplicated = sorted({k for k in keys if keys.count(k) > 1})
    assert not duplicated, f"duplicated sections: {duplicated}"


def test_one_row_per_real_section_sorted(expert_rows, real_sections):
    _, rows = expert_rows
    keys = [_key(r) for r in rows]
    assert keys == sorted(real_sections)


def test_z_expert_empty_or_within_section(expert_rows, real_sections):
    _, rows = expert_rows
    for row in rows:
        text = row["z_expert"].strip()
        if not text:
            continue
        z = float(text)
        assert math.isfinite(z), f"{_key(row)}: z_expert not finite"
        zs = [p[1] for p in real_sections[_key(row)]]
        assert min(zs) <= z <= max(zs), (
            f"{_key(row)}: z_expert {z} outside [{min(zs)}, {max(zs)}]"
        )