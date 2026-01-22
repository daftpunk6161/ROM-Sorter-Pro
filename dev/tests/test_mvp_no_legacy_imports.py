import re
import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.integration


LEGACY_IMPORT_PATTERNS = [
    re.compile(r"^\s*from\s+_archive\b"),
    re.compile(r"^\s*import\s+_archive\b"),
    re.compile(r"^\s*from\s+legacy_"),
    re.compile(r"^\s*import\s+legacy_"),
]


def _iter_src_py_files() -> list[Path]:
    src_root = ROOT / "src"
    return [
        path
        for path in src_root.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def test_no_legacy_imports_in_src():
    offenders = []
    for path in _iter_src_py_files():
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for line in text.splitlines():
            if any(pattern.search(line) for pattern in LEGACY_IMPORT_PATTERNS):
                offenders.append(f"{path}: {line.strip()}")
                break

    assert not offenders, "Legacy imports found in src:\n" + "\n".join(offenders)
