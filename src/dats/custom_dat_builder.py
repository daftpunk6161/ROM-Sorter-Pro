"""Custom DAT builder utilities (MVP)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from typing import Any, cast

try:
    from defusedxml import ElementTree as ET  # type: ignore
except Exception:
    import xml.etree.ElementTree as ET  # nosec B405

ET_ANY = cast(Any, ET)

from ..app.models import ScanItem, ScanResult
from ..core.file_utils import calculate_file_hash, calculate_file_hashes_parallel
from ..security.security_utils import validate_file_operation


@dataclass(frozen=True)
class DatBuildReport:
    output_path: str
    total_items: int
    hashed_items: int


def _iter_items(scan: ScanResult) -> Iterable[ScanItem]:
    return scan.items or []


def build_custom_dat(
    scan: ScanResult,
    output_path: str,
    *,
    dat_name: Optional[str] = None,
    include_sha1: bool = True,
) -> DatBuildReport:
    """Build a simple Logiqx-style DAT from a ScanResult."""
    out_path = Path(output_path)
    validate_file_operation(out_path, allow_read=False, allow_write=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    dat_title = dat_name or "ROM-Sorter-Pro Custom DAT"
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")

    root = ET_ANY.Element("datafile")
    header = ET_ANY.SubElement(root, "header")
    ET_ANY.SubElement(header, "name").text = dat_title
    ET_ANY.SubElement(header, "description").text = dat_title
    ET_ANY.SubElement(header, "version").text = now
    ET_ANY.SubElement(header, "author").text = "ROM-Sorter-Pro"

    items = list(_iter_items(scan))
    hash_map: dict[str, Optional[str]] = {}
    if include_sha1 and items:
        try:
            hash_map = calculate_file_hashes_parallel(
                [Path(str(item.input_path)) for item in items],
                algorithm="sha1",
            )
        except Exception:
            hash_map = {}

    hashed = 0
    for item in items:
        input_path = Path(str(item.input_path))
        game = ET_ANY.SubElement(root, "game", name=input_path.stem)
        size = 0
        try:
            size = int(input_path.stat().st_size)
        except Exception:
            size = 0
        rom_attrib = {
            "name": input_path.name,
            "size": str(size),
        }
        if include_sha1:
            sha1 = hash_map.get(str(input_path))
            if sha1 is None:
                sha1 = calculate_file_hash(input_path, algorithm="sha1")
            if sha1:
                rom_attrib["sha1"] = sha1
                hashed += 1
        ET_ANY.SubElement(game, "rom", attrib=rom_attrib)

    tree = ET_ANY.ElementTree(root)
    tree.write(str(out_path), encoding="utf-8", xml_declaration=True)

    return DatBuildReport(output_path=str(out_path), total_items=len(scan.items), hashed_items=hashed)
