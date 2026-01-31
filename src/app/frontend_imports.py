"""Frontend import helpers (MVP)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..config import Config
from .identification_overrides import add_identification_overrides_bulk


@dataclass(frozen=True)
class LaunchBoxImportReport:
    total_rows: int
    imported_rows: int
    skipped_rows: int
    override_file: Optional[str]


def import_launchbox_csv_to_overrides(
    csv_path: str,
    *,
    config: Optional[Config] = None,
    path_column: str = "ApplicationPath",
    platform_column: str = "Platform",
) -> LaunchBoxImportReport:
    """Import a LaunchBox CSV and create identification overrides.

    The CSV is expected to contain at least ApplicationPath and Platform columns.
    """
    config_obj = config or Config().load_config()
    path_obj = Path(csv_path)
    raw = path_obj.read_text(encoding="utf-8", errors="ignore")

    rows = list(csv.DictReader(raw.splitlines()))
    total_rows = len(rows)
    skipped_rows = 0

    by_platform: Dict[str, List[str]] = {}
    for row in rows:
        path_value = str(row.get(path_column) or "").strip()
        platform_value = str(row.get(platform_column) or "").strip()
        if not path_value or not platform_value:
            skipped_rows += 1
            continue
        by_platform.setdefault(platform_value, []).append(path_value)

    imported_rows = 0
    override_path: Optional[str] = None
    for platform_id, paths in by_platform.items():
        ok, _message, path = add_identification_overrides_bulk(
            config_obj,
            input_paths=paths,
            platform_id=platform_id,
            name="launchbox-import",
            confidence=0.95,
        )
        if ok:
            imported_rows += len(paths)
            override_path = str(path)
        else:
            skipped_rows += len(paths)

    return LaunchBoxImportReport(
        total_rows=total_rows,
        imported_rows=imported_rows,
        skipped_rows=skipped_rows,
        override_file=override_path,
    )
