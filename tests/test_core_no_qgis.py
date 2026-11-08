"""Guard test: the core never imports QGIS (it must run with the bare interpreter)."""

import ast
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parent.parent / "bankfull_core"
CORE_FILES = sorted(CORE.glob("*.py"))


def _qgis_imports(tree):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [a.name for a in node.names if a.name.split(".")[0] == "qgis"]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module \
                and node.module.split(".")[0] == "qgis":
            out.append(node.module)
    return out


def test_core_files_found():
    assert CORE / "detection.py" in CORE_FILES


@pytest.mark.parametrize("path", CORE_FILES, ids=lambda p: p.name)
def test_core_module_does_not_import_qgis(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    assert _qgis_imports(tree) == []
