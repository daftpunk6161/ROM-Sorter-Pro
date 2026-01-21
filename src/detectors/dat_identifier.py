"""DAT/Hash-first identification helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

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
    sha1 = calculate_file_hash(path, algorithm="sha1")
    if sha1:
        row = index.lookup_sha1(sha1)
        if row:
            return IdentificationResult(
                platform_id=row.platform_id or "Unknown",
                confidence=1000.0,
                is_exact=True,
                signals=["DAT_MATCH_SHA1"],
                candidates=[row.platform_id or "Unknown"],
                reason="sha1-exact",
                input_kind="RawRom",
            )

    # CRC32+size fallback only if sha1 missing in DAT row
    try:
        size_bytes = Path(path).stat().st_size
    except Exception:
        size_bytes = 0
    crc32 = calculate_crc32(path)
    if crc32 and size_bytes:
        row = index.lookup_crc_size_when_sha1_missing(crc32, size_bytes)
        if row:
            return IdentificationResult(
                platform_id=row.platform_id or "Unknown",
                confidence=1000.0,
                is_exact=True,
                signals=["DAT_MATCH_CRC_SIZE"],
                candidates=[row.platform_id or "Unknown"],
                reason="crc32-size-exact",
                input_kind="RawRom",
            )
    return None
