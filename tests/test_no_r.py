"""Guard test: no R, rpy2, descartes or direct PyQt imports in the repository.

Every ``.py`` file is checked except ``golden_tools/`` (the scripts that produced the golden
data with R). Markdown files are not checked: they cite R legitimately.
"""

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {"golden_tools", ".git", "__pycache__", ".venv", ".pytest_cache",
                 ".ruff_cache", ".idea"}

FORBIDDEN_MODULES = {"rpy2", "descartes", "PyQt4", "PyQt5"}

# Built by concatenation so that this file does not contain the strings it looks for.
FORBIDDEN_STRINGS = ("R" + "script", "R" + ".exe", "R" + " CMD")

# Functions that start external programs.
_RUNNERS = {"run", "call", "check_call", "check_output", "Popen", "system", "popen",
            "spawnl", "spawnv", "startfile"}


def _python_files():
    for path in sorted(REPO.rglob("*.py")):
        rel = path.relative_to(REPO)
        if EXCLUDED_DIRS.intersection(rel.parts[:-1]):
            continue
        yield rel


PY_FILES = list(_python_files())


def _call_name(func):
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _violations(tree):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    out.append(f"line {node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module \
                    and node.module.split(".")[0] in FORBIDDEN_MODULES:
                out.append(f"line {node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Call) and _call_name(node.func) in _RUNNERS:
            for arg in ast.walk(node):
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                        and any(s in arg.value for s in FORBIDDEN_STRINGS):
                    out.append(f"line {node.lineno}: runs {arg.value!r}")
    return out


def test_files_found():
    assert Path("bankfulldetection.py") in PY_FILES
    assert not any(p.parts[0] == "golden_tools" for p in PY_FILES)


@pytest.mark.parametrize("rel", PY_FILES, ids=str)
def test_no_r_descartes_or_direct_pyqt(rel):
    tree = ast.parse((REPO / rel).read_text(encoding="utf-8"), filename=str(rel))
    assert _violations(tree) == []


def test_detector_catches_violations():
    src = (
        "import rpy2.robjects\n"
        "from descartes import PolygonPatch\n"
        "from PyQt5.QtCore import QVariant\n"
        "import subprocess\n"
        f"subprocess.run(['{FORBIDDEN_STRINGS[0]}', 'x.R'])\n"
        "from qgis.PyQt.QtCore import QVariant\n"
    )
    assert len(_violations(ast.parse(src))) == 4
