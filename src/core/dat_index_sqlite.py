"""SQLite-backed DAT index (incremental, portable)."""

from __future__ import annotations

import os
import sqlite3
import hashlib
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple
import xml.etree.ElementTree as ET

from .index_lock import acquire_index_lock, release_index_lock
from .dat_index import _normalize_system_name
from ..config import Config, load_config


@dataclass(frozen=True)
class DatHashRow:
    dat_id: int
    platform_id: Optional[str]
    rom_name: Optional[str]
    set_name: Optional[str]
    crc32: Optional[str]
    sha1: Optional[str]
    size_bytes: Optional[int]


class DatIndexSqlite:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._apply_pragmas()
        self._init_schema()

    @classmethod
    def from_config(cls, config: Optional[Config] = None) -> "DatIndexSqlite":
        cfg = config or load_config()
        dat_cfg = cfg.get("dats", {}) or {}
        index_path = dat_cfg.get("index_path") or os.path.join("data", "index", "romsorter_dat_index.sqlite")
        return cls(Path(index_path))

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            return

    def _apply_pragmas(self) -> None:
        cur = self.conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA temp_store=MEMORY")
        cur.execute("PRAGMA cache_size=10000")
        self.conn.commit()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dat_files (
                dat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT UNIQUE NOT NULL,
                mtime INTEGER,
                size_bytes INTEGER,
                content_hash TEXT,
                active INTEGER DEFAULT 1
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS rom_hashes (
                dat_id INTEGER NOT NULL,
                platform_id TEXT,
                rom_name TEXT,
                set_name TEXT,
                crc32 TEXT,
                sha1 TEXT,
                size_bytes INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS game_names (
                dat_id INTEGER NOT NULL,
                platform_id TEXT,
                game_name TEXT
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rom_hashes_crc_size ON rom_hashes(crc32, size_bytes)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rom_hashes_dat_id ON rom_hashes(dat_id)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_rom_hashes_sha1 ON rom_hashes(sha1) WHERE sha1 IS NOT NULL")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_game_names_dat_id ON game_names(dat_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_game_names_name ON game_names(game_name)")
        self.conn.commit()

    def _file_signature(self, path: Path) -> Tuple[int, int, Optional[str]]:
        stat = path.stat()
        mtime = int(stat.st_mtime)
        size = int(stat.st_size)
        return mtime, size, None

    def _iter_dat_files(self, paths: Iterable[str]) -> Iterator[Path]:
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

    def _ensure_dat_file(self, path: Path) -> Tuple[Optional[int], bool]:
        cur = self.conn.cursor()
        cur.execute("SELECT dat_id, mtime, size_bytes FROM dat_files WHERE source_path=?", (str(path),))
        row = cur.fetchone()
        mtime, size, _ = self._file_signature(path)
        if row:
            if int(row["mtime"] or 0) == mtime and int(row["size_bytes"] or 0) == size:
                return int(row["dat_id"]), False
            cur.execute("UPDATE dat_files SET mtime=?, size_bytes=?, active=1 WHERE dat_id=?", (mtime, size, int(row["dat_id"])))
            return int(row["dat_id"]), True
        cur.execute(
            "INSERT INTO dat_files (source_path, mtime, size_bytes, active) VALUES (?, ?, ?, 1)",
            (str(path), mtime, size),
        )
        return int(cur.lastrowid), True

    def _clear_dat_rows(self, dat_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM rom_hashes WHERE dat_id=?", (dat_id,))
        cur.execute("DELETE FROM game_names WHERE dat_id=?", (dat_id,))

    def _insert_rows(self, rows: List[DatHashRow]) -> None:
        cur = self.conn.cursor()
        cur.executemany(
            "INSERT INTO rom_hashes (dat_id, platform_id, rom_name, set_name, crc32, sha1, size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(r.dat_id, r.platform_id, r.rom_name, r.set_name, r.crc32, r.sha1, r.size_bytes) for r in rows],
        )

    def ingest(self, paths: Iterable[str], *, cancel_event: Optional[object] = None) -> Dict[str, int]:
        processed = 0
        skipped = 0
        inserted = 0

        for file_path in self._iter_dat_files(paths):
            if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
                break
            if not file_path.exists() or not file_path.is_file():
                continue
            dat_id, changed = self._ensure_dat_file(file_path)
            if not dat_id:
                continue

            if not changed:
                skipped += 1
                continue

            self._clear_dat_rows(dat_id)
            rows = list(self._parse_dat_file(file_path, dat_id))
            processed += 1
            for i in range(0, len(rows), 10000):
                self._insert_rows(rows[i : i + 10000])
                inserted += len(rows[i : i + 10000])
            self.conn.commit()

        return {"processed": processed, "skipped": skipped, "inserted": inserted}

    def _parse_dat_file(self, path: Path, dat_id: int) -> Iterator[DatHashRow]:
        suffix = path.suffix.lower()
        if suffix == ".zip":
            with zipfile.ZipFile(str(path), "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    name = info.filename.lower()
                    if not (name.endswith(".dat") or name.endswith(".xml")):
                        continue
                    with zf.open(info, "r") as fh:
                        head = fh.read(64)
                    is_xml = name.endswith(".xml") or head.lstrip().startswith(b"<")
                    with zf.open(info, "r") as fh:
                        yield from (
                            self._parse_logiqx_xml_stream(fh, dat_id)
                            if is_xml
                            else self._parse_clrmamepro_text_stream(fh, dat_id)
                        )
            return

        with open(path, "rb") as f:
            head = f.read(64)
        is_xml = head.lstrip().startswith(b"<") or suffix == ".xml"
        with open(path, "rb") as f:
            yield from (
                self._parse_logiqx_xml_stream(f, dat_id)
                if is_xml
                else self._parse_clrmamepro_text_stream(f, dat_id)
            )

    def _parse_logiqx_xml_stream(self, stream, dat_id: int) -> Iterator[DatHashRow]:
        context = ET.iterparse(stream, events=("start", "end"))
        _, root = next(context)
        current_game_name: Optional[str] = None
        dat_name: Optional[str] = None
        platform_id: Optional[str] = None
        for event, elem in context:
            tag = elem.tag.lower() if isinstance(elem.tag, str) else ""
            if event == "end" and tag.endswith("name") and elem.text and elem.text.strip():
                if dat_name is None:
                    dat_name = elem.text.strip()
                    platform_id, _ = _normalize_system_name(dat_name)
            if event == "start" and tag.endswith("game"):
                current_game_name = (elem.attrib.get("name") or "").strip() or None
                if current_game_name:
                    cur = self.conn.cursor()
                    cur.execute(
                        "INSERT INTO game_names (dat_id, platform_id, game_name) VALUES (?, ?, ?)",
                        (dat_id, platform_id, current_game_name.lower()),
                    )
            if event == "end" and tag.endswith("rom"):
                rom_name = (elem.attrib.get("name") or "").strip() or None
                crc = (elem.attrib.get("crc") or "").strip().lower() or None
                sha1 = (elem.attrib.get("sha1") or "").strip().lower() or None
                size = elem.attrib.get("size")
                size_val = int(size) if size and str(size).isdigit() else None
                yield DatHashRow(dat_id, platform_id, rom_name, current_game_name, crc, sha1, size_val)
                elem.clear()
            if event == "end" and tag.endswith("game"):
                current_game_name = None
                elem.clear()

    def _parse_clrmamepro_text_stream(self, stream, dat_id: int) -> Iterator[DatHashRow]:
        import re
        re_rom = re.compile(r"^\s*rom\s*\(", re.I)
        re_name = re.compile(r"\bname\s+\"([^\"]+)\"", re.I)
        re_crc = re.compile(r"\bcrc\s+([0-9a-fA-F]{1,8})\b", re.I)
        re_sha1 = re.compile(r"\bsha1\s+([0-9a-fA-F]{40})\b", re.I)
        re_size = re.compile(r"\bsize\s+([0-9]+)\b", re.I)
        re_header = re.compile(r"^\s*(clrmamepro|header)\s*\(", re.I)
        game_name: Optional[str] = None
        dat_name: Optional[str] = None
        platform_id: Optional[str] = None
        for raw in stream:
            line = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else str(raw)
            if re_header.search(line) and "name" in line.lower():
                m = re_name.search(line)
                if m:
                    dat_name = m.group(1).strip()
                    platform_id, _ = _normalize_system_name(dat_name)
            if line.strip().lower().startswith("game"):
                m = re_name.search(line)
                if m:
                    game_name = m.group(1).strip()
                    cur = self.conn.cursor()
                    cur.execute(
                        "INSERT INTO game_names (dat_id, platform_id, game_name) VALUES (?, ?, ?)",
                        (dat_id, platform_id, game_name.lower()),
                    )
            if re_rom.search(line):
                rn = re_name.search(line)
                rc = re_crc.search(line)
                rs = re_sha1.search(line)
                rz = re_size.search(line)
                yield DatHashRow(
                    dat_id,
                    platform_id,
                    rn.group(1).strip() if rn else None,
                    game_name,
                    rc.group(1).lower() if rc else None,
                    rs.group(1).lower() if rs else None,
                    int(rz.group(1)) if rz else None,
                )

    def lookup_sha1(self, sha1: str) -> Optional[DatHashRow]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM rom_hashes WHERE sha1=? LIMIT 1", (sha1.lower(),))
        row = cur.fetchone()
        if not row:
            return None
        return DatHashRow(
            dat_id=row["dat_id"],
            platform_id=row["platform_id"],
            rom_name=row["rom_name"],
            set_name=row["set_name"],
            crc32=row["crc32"],
            sha1=row["sha1"],
            size_bytes=row["size_bytes"],
        )

    def lookup_crc_size(self, crc32: str, size_bytes: int) -> Optional[DatHashRow]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM rom_hashes WHERE crc32=? AND size_bytes=? LIMIT 1", (crc32.lower(), int(size_bytes)))
        row = cur.fetchone()
        if not row:
            return None
        return DatHashRow(
            dat_id=row["dat_id"],
            platform_id=row["platform_id"],
            rom_name=row["rom_name"],
            set_name=row["set_name"],
            crc32=row["crc32"],
            sha1=row["sha1"],
            size_bytes=row["size_bytes"],
        )

    def lookup_crc_size_when_sha1_missing(self, crc32: str, size_bytes: int) -> Optional[DatHashRow]:
        row = self.lookup_crc_size(crc32, size_bytes)
        if row and not row.sha1:
            return row
        return None

    def lookup_game(self, game_name: str) -> Optional[Tuple[str, int]]:
        if not game_name:
            return None
        cur = self.conn.cursor()
        cur.execute(
            "SELECT platform_id, dat_id FROM game_names WHERE game_name=? LIMIT 1",
            (str(game_name).lower(),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return (row["platform_id"] or "Unknown", int(row["dat_id"]))


def build_index_from_config(config: Optional[Config] = None, *, cancel_event: Optional[object] = None) -> Dict[str, int]:
    cfg = config or load_config()
    dat_cfg = cfg.get("dats", {}) or {}
    paths = dat_cfg.get("import_paths") or []
    if isinstance(paths, str):
        paths = [p.strip() for p in paths.split(";") if p.strip()]

    index = DatIndexSqlite.from_config(cfg)
    lock_path = Path(dat_cfg.get("lock_path") or os.path.join("data", "index", "romsorter_dat_index.lock"))
    lock_info = acquire_index_lock(lock_path, index.db_path)
    try:
        result = index.ingest(paths, cancel_event=cancel_event)
        return result
    finally:
        release_index_lock(lock_path)
        index.close()
