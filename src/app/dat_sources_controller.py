"""DAT source management helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional

from ..config import Config, load_config, save_config
@dataclass(frozen=True)
class DatSourceReport:
    paths: List[str]
    existing_paths: List[str]
    missing_paths: List[str]
    dat_files: int
    dat_xml_files: int
    dat_zip_files: int



def _normalize_dat_sources(paths: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for raw in paths:
        value = str(raw or "").strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _load_cfg(config: Optional[Config | dict[str, Any]]) -> Config:
    if isinstance(config, Config):
        return config
    if isinstance(config, dict):
        return Config(config)
    return Config(load_config())


def get_dat_sources(config: Optional[Config] = None) -> List[str]:
    cfg = _load_cfg(config)
    dat_cfg = cfg.get("dats", {}) or {}
    paths = dat_cfg.get("import_paths") or []
    if isinstance(paths, str):
        paths = [p.strip() for p in paths.split(";") if p.strip()]
    return _normalize_dat_sources(paths)


def save_dat_sources(paths: Iterable[str], config: Optional[Config] = None) -> List[str]:
    cfg = _load_cfg(config)
    dat_cfg = cfg.get("dats", {}) or {}
    normalized = _normalize_dat_sources(paths)
    dat_cfg["import_paths"] = normalized
    cfg.set("dats", dat_cfg)
    save_config(cfg.config_data)
    return normalized


def analyze_dat_sources(paths: Iterable[str]):
    normalized = _normalize_dat_sources(paths)
    existing: List[str] = []
    missing: List[str] = []
    dat_files = 0
    dat_xml_files = 0
    dat_zip_files = 0

    for raw in normalized:
        path = Path(raw)
        if not path.exists():
            missing.append(raw)
            continue
        existing.append(raw)
        if path.is_dir():
            dat_files += sum(1 for _ in path.rglob("*.dat"))
            dat_xml_files += sum(1 for _ in path.rglob("*.xml"))
            dat_zip_files += sum(1 for _ in path.rglob("*.zip"))
        else:
            suffix = path.suffix.lower()
            if suffix == ".dat":
                dat_files += 1
            elif suffix == ".xml":
                dat_xml_files += 1
            elif suffix == ".zip":
                dat_zip_files += 1

    return DatSourceReport(
        paths=normalized,
        existing_paths=existing,
        missing_paths=missing,
        dat_files=dat_files,
        dat_xml_files=dat_xml_files,
        dat_zip_files=dat_zip_files,
    )
