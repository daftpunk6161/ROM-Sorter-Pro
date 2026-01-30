from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.security.security_utils import InvalidPathError, resolve_path_safe, validate_file_operation


pytestmark = pytest.mark.integration


MALICIOUS_PATHS = [
    "../etc/passwd",
    "..\\..\\windows\\system32",
    "../../../../",
    "C:\\Windows\\System32\\config\\SAM",
    "C:\\Program Files\\..\\Windows",
    "\\\\\\\\..\\..\\",
]


def test_security_fuzzing_paths(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir(parents=True, exist_ok=True)
    safe_file = base_dir / "safe.txt"
    safe_file.write_text("ok", encoding="utf-8")

    # Safe path passes
    assert validate_file_operation(safe_file, base_dir=base_dir, allow_read=True, allow_write=True)

    for raw in MALICIOUS_PATHS:
        with pytest.raises(InvalidPathError):
            resolve_path_safe(raw)

    # Ensure traversal outside base_dir is blocked
    with pytest.raises(InvalidPathError):
        validate_file_operation(base_dir.parent / "outside.txt", base_dir=base_dir)
