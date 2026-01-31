"""DAT auto-updater utilities (MVP)."""

from __future__ import annotations

import hashlib
import logging
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..config import Config
from ..security.security_utils import validate_file_operation

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatUpdateResult:
    name: str
    url: str
    dest: str
    updated: bool
    message: str


@dataclass(frozen=True)
class DatUpdateReport:
    total: int
    updated: int
    skipped: int
    results: List[DatUpdateResult]


def _sha256_file(path: Path) -> str:
    hash_obj = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def _iter_sources(cfg: Config) -> Iterable[Dict[str, Any]]:
    data = cfg.get("dats", {}) if isinstance(cfg, Config) else {}
    if not isinstance(data, dict):
        return []
    auto_cfg = data.get("auto_update", {}) or {}
    if not isinstance(auto_cfg, dict):
        return []
    sources = auto_cfg.get("sources", []) or []
    if isinstance(sources, dict):
        sources = [sources]
    return [src for src in sources if isinstance(src, dict)]


def update_dat_sources(config: Optional[Config] = None) -> DatUpdateReport:
    """Download configured DAT sources and update local copies."""
    cfg = config or Config().load_config()
    results: List[DatUpdateResult] = []
    updated = 0
    skipped = 0

    for source in _iter_sources(cfg):
        name = str(source.get("name") or "DAT").strip() or "DAT"
        url = str(source.get("url") or "").strip()
        dest = str(source.get("dest") or "").strip()
        sha256 = str(source.get("sha256") or "").strip().lower() or None
        if not url or not dest:
            skipped += 1
            results.append(DatUpdateResult(name=name, url=url, dest=dest, updated=False, message="missing url/dest"))
            continue

        dest_path = Path(dest)
        try:
            validate_file_operation(dest_path, allow_read=True, allow_write=True)
        except Exception as exc:
            skipped += 1
            results.append(DatUpdateResult(name=name, url=url, dest=dest, updated=False, message=str(exc)))
            continue

        tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
        try:
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            if url.startswith("file://"):
                src_path = Path(url.replace("file://", "", 1))
                tmp_path.write_bytes(src_path.read_bytes())
            elif os.path.exists(url):
                tmp_path.write_bytes(Path(url).read_bytes())
            else:
                urllib.request.urlretrieve(url, tmp_path)  # nosec B310

            if sha256:
                digest = _sha256_file(tmp_path)
                if digest.lower() != sha256:
                    tmp_path.unlink(missing_ok=True)
                    skipped += 1
                    results.append(
                        DatUpdateResult(name=name, url=url, dest=dest, updated=False, message="sha256 mismatch")
                    )
                    continue

            if dest_path.exists():
                try:
                    if tmp_path.read_bytes() == dest_path.read_bytes():
                        tmp_path.unlink(missing_ok=True)
                        skipped += 1
                        results.append(
                            DatUpdateResult(name=name, url=url, dest=dest, updated=False, message="unchanged")
                        )
                        continue
                except Exception:
                    pass

            tmp_path.replace(dest_path)
            updated += 1
            results.append(DatUpdateResult(name=name, url=url, dest=dest, updated=True, message="updated"))
        except Exception as exc:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            skipped += 1
            results.append(DatUpdateResult(name=name, url=url, dest=dest, updated=False, message=str(exc)))

    total = len(results)
    return DatUpdateReport(total=total, updated=updated, skipped=skipped, results=results)
