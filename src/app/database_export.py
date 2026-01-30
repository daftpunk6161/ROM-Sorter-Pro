"""Export scan results into the ROM database."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..database.rom_database import ROMDatabase
from .models import ScanResult

logger = logging.getLogger(__name__)


def export_scan_to_database(scan_result: ScanResult, *, db_path: Optional[str] = None) -> int:
    """Insert scan results into the ROM database.

    Returns the number of inserted/updated rows.
    """
    db = ROMDatabase(db_path=db_path) if db_path else ROMDatabase()
    inserted = 0
    unknown_system = db.get_system_by_name("Unknown") or {}
    unknown_id = int(unknown_system.get("id") or 1)

    for item in scan_result.items:
        try:
            system_name = str(item.detected_system or "Unknown")
            system = db.get_system_by_name(system_name) or {}
            system_id = int(system.get("id") or unknown_id)
            input_path = Path(item.input_path)
            size = input_path.stat().st_size if input_path.exists() else None
            db.add_rom(
                name=input_path.name,
                system_id=system_id,
                file_path=str(input_path),
                size=size,
                metadata={
                    "detection_source": str(item.detection_source or ""),
                    "confidence": str(item.detection_confidence or ""),
                },
            )
            inserted += 1
        except Exception as exc:
            logger.debug("DB export failed for %s: %s", item.input_path, exc)
            continue

    return inserted
