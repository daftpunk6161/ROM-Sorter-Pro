#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""ROM Sorter Pro - DAT index

Goal: allow accurate identification using external DATs (No-Intro/Redump/TOSEC/MAME/etc.).

- No external dependencies (stdlib only).
- Streaming parse for large XML DATs.
- Supports both:
    - Logiqx XML DATs
    - ClrMamePro-style text DATs (best-effort)
- Supports .zip containers with .dat/.xml inside.

Provides lookups:
- by game name (for archives like MAME .zip sets)
- by hashes (crc32/md5/sha1) for single-file ROMs

Loading is designed to be lazy/background by default so the GUI remains responsive.
The index is cached on disk and reused when DAT files are unchanged.
"""

from __future__ import annotations

import logging
import os
import pickle  # nosec B403
import re
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, IO, Iterator, List, Optional, Sequence, Tuple
try:
    from defusedxml import ElementTree as ET  # type: ignore
except Exception:
    import xml.etree.ElementTree as ET  # nosec B405

logger = logging.getLogger(__name__)


def _canon(text: str) -> str:
    return " ".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in (text or "")).split()
    )


def _normalize_system_name(header_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (system, dat_title).

    `system` is a stable identifier used for sorting folders.
    `dat_title` is the original DAT header name for provenance.

    Heuristic rules:
    - No-Intro/Redump often embed platform in the title (e.g. "Nintendo - Nintendo DS").
    - MAME/FBNeo/arcade DATs map to "Arcade".
    - Pinball-oriented DATs map to "Pinball".
    """
    title = (header_name or "").strip() or None
    if not title:
        return None, None

    c = _canon(title)

    # Arcade / emulation set families
    if any(k in c for k in ("mame", "finalburn", "fbneo", "arcade")):
        return "Arcade", title
    if "pinball" in c:
        return "Pinball", title
    if "tosec" in c:
        # TOSEC is cross-platform; we keep as a family bucket unless we can infer a platform.
        # Specific platform mapping can be added later.
        pass

    # Platform mappings (extend as needed)
    mapping = {
        # Nintendo
        "nintendo entertainment system": "NES",
        "nintendo nes": "NES",
        "famicom": "NES",
        "super nintendo entertainment system": "SNES",
        "super nintendo": "SNES",
        "super famicom": "SNES",
        "nintendo 64": "N64",
        "game boy advance": "GBA",
        "gameboy advance": "GBA",
        "game boy color": "GBC",
        "gameboy color": "GBC",
        "game boy": "GB",
        "gameboy": "GB",
        "nintendo ds": "NDS",
        "nintendo 3ds": "3DS",
        "nintendo switch": "SWITCH",

        # Sega
        "sega genesis": "Genesis",
        "mega drive": "Genesis",
        "sega mega drive": "Genesis",
        "sega 32x": "32X",
        "sega cd": "SegaCD",
        "mega cd": "SegaCD",
        "sega dreamcast": "Dreamcast",

        # Sony
        "sony playstation": "PSX",
        "playstation": "PSX",
        "sony playstation 2": "PS2",
        "playstation 2": "PS2",
        "sony playstation portable": "PSP",
        "playstation portable": "PSP",

        # NEC
        "pc engine": "PC Engine",
        "turbografx 16": "PC Engine",
        "pc fx": "PC-FX",

        # SNK
        "neo geo": "NeoGeo",
        "neo geo pocket": "NeoGeo Pocket",
    }

    # Try direct substring matches
    for key, system in mapping.items():
        if key in c:
            return system, title

    # Try matching against enhanced console database by key or folder name
    try:
        from ..database.console_db import ENHANCED_CONSOLE_DATABASE

        # Exact key match
        for console_key in ENHANCED_CONSOLE_DATABASE.keys():
            if _canon(console_key) == c:
                return console_key, title

        # Folder-name containment match
        for console_key, meta in ENHANCED_CONSOLE_DATABASE.items():
            folder = _canon(getattr(meta, "folder_name", "") or "")
            if folder and folder in c:
                return console_key, title
    except Exception:
        pass

    return None, title


def _norm_hash(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip().lower()
    if not value:
        return None
    return value


def _norm_crc(value: Optional[str]) -> Optional[str]:
    value = _norm_hash(value)
    if not value:
        return None
    # Logiqx uses 8-hex CRC32. Normalize to exactly 8 lower-hex.
    value = value.lower().lstrip("0x")
    if len(value) > 8:
        value = value[-8:]
    return value.zfill(8)


@dataclass(frozen=True)
class DatMatch:
    system: str
    confidence: float
    source: str
    dat_name: Optional[str] = None
    game_name: Optional[str] = None
    rom_name: Optional[str] = None


class DatIndex:
    """In-memory index for one or more DAT files."""

    def __init__(self) -> None:
        self._game_to_system: Dict[str, DatMatch] = {}
        self._crc_to_system: Dict[str, DatMatch] = {}
        self._md5_to_system: Dict[str, DatMatch] = {}
        self._sha1_to_system: Dict[str, DatMatch] = {}

        self._pending_paths: List[str] = []
        self._load_started = False
        self._load_done = False
        self._sources_total = 0
        self._sources_loaded = 0
        self._last_warning: Optional[str] = None
        self._lock = threading.Lock()

    def _get_cache_file(self) -> Path:
        cache_dir = Path(os.getcwd()) / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "dat_index.pkl"

    def _compute_signature(self, dat_files: Sequence[Path]) -> List[Dict[str, Any]]:
        signature: List[Dict[str, Any]] = []
        for p in dat_files:
            try:
                stat = p.stat()
                signature.append({
                    "path": str(p),
                    "mtime": int(stat.st_mtime),
                    "size": int(stat.st_size),
                })
            except Exception:
                signature.append({"path": str(p), "mtime": 0, "size": 0})
        signature.sort(key=lambda x: x["path"])
        return signature

    def _load_cache(self, dat_files: Sequence[Path]) -> bool:
        cache_file = self._get_cache_file()
        if not cache_file.exists():
            return False
        try:
            with cache_file.open("rb") as f:
                payload = pickle.load(f)  # nosec B301
            if not isinstance(payload, dict):
                return False
            signature = payload.get("signature")
            if signature != self._compute_signature(dat_files):
                return False
            self._game_to_system = payload.get("game_to_system", {}) or {}
            self._crc_to_system = payload.get("crc_to_system", {}) or {}
            self._md5_to_system = payload.get("md5_to_system", {}) or {}
            self._sha1_to_system = payload.get("sha1_to_system", {}) or {}
            return True
        except Exception as exc:
            logger.debug("DAT cache load failed: %s", exc)
            return False

    def _save_cache(self, dat_files: Sequence[Path]) -> None:
        cache_file = self._get_cache_file()
        try:
            payload = {
                "signature": self._compute_signature(dat_files),
                "game_to_system": self._game_to_system,
                "crc_to_system": self._crc_to_system,
                "md5_to_system": self._md5_to_system,
                "sha1_to_system": self._sha1_to_system,
            }
            with cache_file.open("wb") as f:
                pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as exc:
            logger.debug("DAT cache save failed: %s", exc)

    def get_load_status(self) -> Dict[str, Any]:
        """Return a small, UI-friendly status snapshot.

        States:
        - not_configured: no paths
        - pending: paths configured but load not started
        - loading: load started but not done
        - ready: load completed
        """
        with self._lock:
            has_paths = bool(self._pending_paths)
            started = bool(self._load_started)
            done = bool(self._load_done)
            total = int(self._sources_total)
            loaded = int(self._sources_loaded)
            last_warning = self._last_warning

        if not has_paths:
            state = "not_configured"
        elif not started:
            state = "pending"
        elif not done:
            state = "loading"
        else:
            state = "ready"

        return {
            "state": state,
            "started": started,
            "done": done,
            "sources_loaded": loaded,
            "sources_total": total,
            "last_warning": last_warning,
        }

    @staticmethod
    def _iter_dat_files(paths: Sequence[str]) -> Iterator[Path]:
        for raw in paths:
            if not raw:
                continue
            p = Path(raw)
            if p.is_dir():
                for child in p.rglob("*.dat"):
                    yield child
                for child in p.rglob("*.xml"):
                    yield child
                for child in p.rglob("*.zip"):
                    yield child
            else:
                yield p

    @staticmethod
    def _coerce_paths(value: object) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value if v]
        if isinstance(value, str):
            # allow semicolon or newline separated on Windows
            parts: List[str] = []
            for chunk in value.replace("\n", ";").split(";"):
                chunk = chunk.strip()
                if chunk:
                    parts.append(chunk)
            return parts
        return [str(value)]

    @classmethod
    def from_config(cls, config) -> "DatIndex":
        """Create a DAT index from Config.

        Expected config keys:
        - dat_matching.enabled: bool
        - dat_matching.dat_paths: list[str] | str

        Also supports env var ROM_SORTER_DAT_PATHS (semicolon-separated).
        """
        enabled = True
        lazy_load = True
        auto_load = True
        dat_paths: List[str] = []

        try:
            dat_cfg = config.get("dat_matching", {}) or {}
            enabled = bool(dat_cfg.get("enabled", True))
            lazy_load = bool(dat_cfg.get("lazy_load", True))
            auto_load = bool(dat_cfg.get("auto_load", True))
            dat_paths.extend(cls._coerce_paths(dat_cfg.get("dat_paths")))
        except Exception:
            # Config shape can vary; keep best-effort
            enabled = True

        env_paths = os.environ.get("ROM_SORTER_DAT_PATHS", "").strip()
        if env_paths:
            dat_paths.extend(cls._coerce_paths(env_paths))

        dat_paths = [p for p in dat_paths if p]
        index = cls()
        if enabled and dat_paths:
            index._pending_paths = dat_paths
            if auto_load:
                if lazy_load:
                    index.start_background_load()
                else:
                    index.load_paths(dat_paths)
        return index

    def start_background_load(self) -> None:
        with self._lock:
            if self._load_started or self._load_done or not self._pending_paths:
                return
            self._load_started = True

        def _bg() -> None:
            try:
                self.load_paths(self._pending_paths)
            except Exception as exc:
                logger.warning("DAT background load failed: %s", exc)

        threading.Thread(target=_bg, daemon=True, name="DatIndexLoader").start()

    def load_paths(self, paths: Sequence[str]) -> None:
        with self._lock:
            # Ensure state is consistent even for synchronous loads
            self._load_started = True
            self._sources_total = 0
            self._sources_loaded = 0

        dat_files = [p for p in self._iter_dat_files(paths) if p.exists() and p.is_file()]
        with self._lock:
            self._sources_total = len(dat_files)

        if dat_files and self._load_cache(dat_files):
            with self._lock:
                self._sources_loaded = len(dat_files)
                self._sources_total = len(dat_files)
                self._load_done = True
            return

        for file_path in dat_files:
            try:
                self._load_dat_file(file_path)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                with self._lock:
                    self._last_warning = str(exc)
                logger.warning("Failed to load DAT %s: %s", file_path, exc)
            finally:
                with self._lock:
                    self._sources_loaded += 1

        with self._lock:
            self._load_done = True

        if dat_files:
            self._save_cache(dat_files)

    def _load_dat_file(self, file_path: Path) -> None:
        suffix = file_path.suffix.lower()
        if suffix == ".zip":
            self._load_dat_zip(file_path)
            return

        with open(file_path, "rb") as f:
            head = f.read(64)
        is_xml = head.lstrip().startswith(b"<") or suffix == ".xml"

        if is_xml:
            with open(file_path, "rb") as f:
                self._load_logiqx_xml_stream(f, source_label=str(file_path))
        else:
            with open(file_path, "rb") as f:
                self._load_clrmamepro_text_stream(f, source_label=str(file_path))

    def _load_dat_zip(self, file_path: Path) -> None:
        with zipfile.ZipFile(str(file_path), "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                lower = name.lower()
                if not (lower.endswith(".dat") or lower.endswith(".xml")):
                    continue

                # Decide parse mode cheaply.
                is_xml = lower.endswith(".xml")
                if not is_xml:
                    with zf.open(info, "r") as fh:
                        head = fh.read(64)
                    is_xml = head.lstrip().startswith(b"<")

                with zf.open(info, "r") as fh:
                    source_label = f"{file_path.name}:{name}"
                    if is_xml:
                        self._load_logiqx_xml_stream(fh, source_label=source_label)
                    else:
                        self._load_clrmamepro_text_stream(fh, source_label=source_label)

    def _load_logiqx_xml_stream(self, stream: IO[bytes], source_label: str) -> None:
        dat_name: Optional[str] = None
        normalized_system: Optional[str] = None

        # streaming parse
        context = ET.iterparse(stream, events=("start", "end"))  # nosec B314
        _, root = next(context)  # grab root

        current_game_name: Optional[str] = None

        for event, elem in context:
            tag = elem.tag.lower() if isinstance(elem.tag, str) else ""

            if event == "end" and tag.endswith("name") and elem.text and elem.text.strip():
                # header/name or other/name; we only set dat_name the first time we see header/name
                # Logiqx typically has <header><name>..</name></header>
                if dat_name is None:
                    dat_name = elem.text.strip()
                    if dat_name:
                        normalized_system, _ = _normalize_system_name(dat_name)

            if event == "start" and tag.endswith("game"):
                current_game_name = (elem.attrib.get("name") or "").strip() or None
                if current_game_name and (normalized_system or dat_name):
                    key = current_game_name.lower()
                    self._game_to_system.setdefault(
                        key,
                        DatMatch(
                            system=(normalized_system or dat_name or "Unknown"),
                            confidence=0.98,
                            source="dat-game",
                            dat_name=dat_name,
                            game_name=current_game_name,
                        ),
                    )

            if event == "end" and tag.endswith("rom"):
                # rom attributes: name, crc, md5, sha1
                rom_name = (elem.attrib.get("name") or "").strip() or None
                crc = _norm_crc(elem.attrib.get("crc"))
                md5 = _norm_hash(elem.attrib.get("md5"))
                sha1 = _norm_hash(elem.attrib.get("sha1"))

                if normalized_system or dat_name:
                    match = DatMatch(
                        system=(normalized_system or dat_name or "Unknown"),
                        confidence=0.99,
                        source="dat-hash",
                        dat_name=dat_name,
                        game_name=current_game_name,
                        rom_name=rom_name,
                    )
                    if crc:
                        self._crc_to_system.setdefault(crc, match)
                    if md5:
                        self._md5_to_system.setdefault(md5, match)
                    if sha1:
                        self._sha1_to_system.setdefault(sha1, match)

                # aggressively clear to keep memory lower
                elem.clear()
                continue

            if event == "end" and tag.endswith("game"):
                current_game_name = None
                elem.clear()

        if dat_name:
            label = normalized_system or dat_name
            logger.info("Loaded DAT: %s (%s)", label, source_label)

    def _load_clrmamepro_text_stream(self, stream: IO[bytes], source_label: str) -> None:
        """Best-effort parser for ClrMamePro text DATs.

        Typical structure:
        - clrmamepro ( name "..." ... )
        - game/machine ( name "..." description "..." rom ( crc ... md5 ... sha1 ... ) )
        """
        # regexes
        re_block_start = re.compile(r"^\s*(clrmamepro|header|game|machine)\s*\(\s*$", re.I)
        re_block_end = re.compile(r"^\s*\)\s*$")
        re_name = re.compile(r"\bname\s+\"([^\"]+)\"", re.I)
        re_desc = re.compile(r"\bdescription\s+\"([^\"]+)\"", re.I)
        re_rom_name = re.compile(r"\bname\s+\"([^\"]+)\"", re.I)
        re_crc = re.compile(r"\bcrc\s+([0-9a-fA-F]{1,8})\b", re.I)
        re_md5 = re.compile(r"\bmd5\s+([0-9a-fA-F]{32})\b", re.I)
        re_sha1 = re.compile(r"\bsha1\s+([0-9a-fA-F]{40})\b", re.I)
        re_rom_line = re.compile(r"^\s*rom\s*\(", re.I)

        dat_name: Optional[str] = None
        normalized_system: Optional[str] = None

        in_header = False
        in_game = False
        game_name: Optional[str] = None
        game_desc: Optional[str] = None

        def _system_match() -> Optional[DatMatch]:
            if not (normalized_system or dat_name):
                return None
            return DatMatch(
                system=(normalized_system or dat_name or "Unknown"),
                confidence=0.99,
                source="dat-text",
                dat_name=dat_name,
            )

        for raw in stream:
            if isinstance(raw, bytes):
                line = raw.decode("utf-8", errors="ignore")
                if not line and raw:
                    line = raw.decode("latin-1", errors="ignore")
            else:
                line = str(raw)

            if not line.strip():
                continue

            m_start = re_block_start.match(line)
            if m_start:
                block = m_start.group(1).lower()
                if block in ("clrmamepro", "header"):
                    in_header = True
                    continue
                if block in ("game", "machine"):
                    in_game = True
                    game_name = None
                    game_desc = None
                    continue

            if re_block_end.match(line):
                if in_game:
                    in_game = False
                    game_name = None
                    game_desc = None
                    continue
                if in_header:
                    in_header = False
                    continue

            if in_header and dat_name is None:
                m = re_name.search(line)
                if m:
                    dat_name = m.group(1).strip()
                    if dat_name:
                        normalized_system, _ = _normalize_system_name(dat_name)
                    continue

            if in_game:
                if game_name is None:
                    m = re_name.search(line)
                    if m:
                        game_name = m.group(1).strip() or None
                        if game_name and (normalized_system or dat_name):
                            self._game_to_system.setdefault(
                                game_name.lower(),
                                DatMatch(
                                    system=(normalized_system or dat_name or "Unknown"),
                                    confidence=0.98,
                                    source="dat-game",
                                    dat_name=dat_name,
                                    game_name=game_name,
                                ),
                            )

                if game_desc is None:
                    m = re_desc.search(line)
                    if m:
                        game_desc = m.group(1).strip() or None
                        if game_desc and (normalized_system or dat_name):
                            self._game_to_system.setdefault(
                                game_desc.lower(),
                                DatMatch(
                                    system=(normalized_system or dat_name or "Unknown"),
                                    confidence=0.90,
                                    source="dat-desc",
                                    dat_name=dat_name,
                                    game_name=game_name or game_desc,
                                ),
                            )

                if re_rom_line.match(line):
                    match = _system_match()
                    if not match:
                        continue
                    m_rom_name = re_rom_name.search(line)
                    rom_name = m_rom_name.group(1).strip() if m_rom_name else None
                    m_crc = re_crc.search(line)
                    m_md5 = re_md5.search(line)
                    m_sha1 = re_sha1.search(line)
                    crc = _norm_crc(m_crc.group(1) if m_crc else None)
                    md5 = _norm_hash(m_md5.group(1) if m_md5 else None)
                    sha1 = _norm_hash(m_sha1.group(1) if m_sha1 else None)
                    if crc:
                        self._crc_to_system.setdefault(
                            crc,
                            DatMatch(
                                system=match.system,
                                confidence=match.confidence,
                                source=match.source,
                                dat_name=match.dat_name,
                                game_name=game_name,
                                rom_name=rom_name,
                            ),
                        )
                    if md5:
                        self._md5_to_system.setdefault(
                            md5,
                            DatMatch(
                                system=match.system,
                                confidence=match.confidence,
                                source=match.source,
                                dat_name=match.dat_name,
                                game_name=game_name,
                                rom_name=rom_name,
                            ),
                        )
                    if sha1:
                        self._sha1_to_system.setdefault(
                            sha1,
                            DatMatch(
                                system=match.system,
                                confidence=match.confidence,
                                source=match.source,
                                dat_name=match.dat_name,
                                game_name=game_name,
                                rom_name=rom_name,
                            ),
                        )

        if dat_name is None:
            # fallback: use the container label
            base = source_label.split(":", 1)[0]
            dat_name = os.path.basename(base) or base
            normalized_system, _ = _normalize_system_name(dat_name)

        label = normalized_system or dat_name
        if label:
            logger.info("Loaded DAT: %s (%s)", label, source_label)

    def lookup_game(self, name: str) -> Optional[DatMatch]:
        if not name:
            return None
        return self._game_to_system.get(name.strip().lower())

    def lookup_hashes(
        self,
        *,
        crc: Optional[str] = None,
        crc32: Optional[str] = None,
        md5: Optional[str] = None,
        sha1: Optional[str] = None,
    ) -> Optional[DatMatch]:
        md5n = _norm_hash(md5)
        sha1n = _norm_hash(sha1)
        crcn = _norm_crc(crc32 or crc)

        if sha1n and sha1n in self._sha1_to_system:
            return self._sha1_to_system[sha1n]
        if md5n and md5n in self._md5_to_system:
            return self._md5_to_system[md5n]
        if crcn and crcn in self._crc_to_system:
            return self._crc_to_system[crcn]
        return None
