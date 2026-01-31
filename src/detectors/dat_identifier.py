"""DAT/Hash-first identification helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from ..core.dat_index_sqlite import DatIndexSqlite
from ..core.file_utils import calculate_file_hash
from ..hash_utils import calculate_crc32


@dataclass(frozen=True)
class IdentificationResult:
    platform_id: str
    confidence: float
    is_exact: bool
    signals: List[str]
    candidates: List[str]
    reason: str
    input_kind: str
    normalized_artifact: Optional[str] = None


def identify_by_hash(path: str, index: DatIndexSqlite) -> Optional[IdentificationResult]:
    def _has_bad_dump(rows: Iterable[object]) -> bool:
        for row in rows:
            name = str(getattr(row, "rom_name", "") or "")
            lowered = name.lower()
            if "[b]" in lowered or "(b)" in lowered:
                return True
        return False

    sha1 = calculate_file_hash(path, algorithm="sha1")
    if sha1:
        rows = index.lookup_sha1_all(sha1)
        if rows:
            platforms = [row.platform_id or "Unknown" for row in rows]
            unique_platforms = sorted({p for p in platforms if p})
            counts = {p: platforms.count(p) for p in unique_platforms}
            primary = max(counts, key=counts.get) if counts else "Unknown"
            signals = ["DAT_MATCH_SHA1"]
            if _has_bad_dump(rows):
                signals.append("BAD_DUMP")
            reason = "sha1-exact"
            if len(unique_platforms) > 1 or len(rows) > 1:
                signals.append("DAT_CROSS_CHECK")
                reason = "sha1-cross-check"
            return IdentificationResult(
                platform_id=primary or "Unknown",
                confidence=1000.0,
                is_exact=True,
                signals=signals,
                candidates=unique_platforms or [primary or "Unknown"],
                reason=reason,
                input_kind="RawRom",
            )

    # CRC32+size fallback only if sha1 missing in DAT row
    try:
        size_bytes = Path(path).stat().st_size
    except Exception:
        size_bytes = 0
    crc32 = calculate_crc32(path)
    if crc32 and size_bytes:
        rows = index.lookup_crc_size_all(crc32, size_bytes)
        rows = [row for row in rows if not row.sha1]
        if rows:
            platforms = [row.platform_id or "Unknown" for row in rows]
            unique_platforms = sorted({p for p in platforms if p})
            counts = {p: platforms.count(p) for p in unique_platforms}
            primary = max(counts, key=counts.get) if counts else "Unknown"
            signals = ["DAT_MATCH_CRC_SIZE"]
            if _has_bad_dump(rows):
                signals.append("BAD_DUMP")
            reason = "crc32-size-exact"
            if len(unique_platforms) > 1 or len(rows) > 1:
                signals.append("DAT_CROSS_CHECK")
                reason = "crc32-size-cross-check"
            return IdentificationResult(
                platform_id=primary or "Unknown",
                confidence=1000.0,
                is_exact=True,
                signals=signals,
                candidates=unique_platforms or [primary or "Unknown"],
                reason=reason,
                input_kind="RawRom",
            )
    return None
