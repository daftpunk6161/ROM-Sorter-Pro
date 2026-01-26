"""Export test fixtures into a portable archive."""

from __future__ import annotations

import tarfile
from pathlib import Path
from typing import Optional


def export_fixtures(output_path: Optional[str] = None) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    fixtures_root = repo_root / "dev" / "tests" / "fixtures"
    if output_path:
        out = Path(output_path)
    else:
        out = repo_root / "dev" / "tests" / "fixtures.tar.gz"

    out.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(out, "w:gz") as tf:
        tf.add(fixtures_root, arcname="fixtures")

    return out


if __name__ == "__main__":
    path = export_fixtures()
    print(path)
