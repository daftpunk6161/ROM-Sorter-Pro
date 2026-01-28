"""Index lockfile handling (PID + process start time)."""

from __future__ import annotations

import json
import os
import socket
import getpass
import time
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class LockInfo:
    pid: int
    process_start_time_utc: str
    created_at_utc: str
    hostname: str
    user: str
    index_path: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_process_start_time_psutil(pid: int) -> Optional[str]:
    try:
        import psutil  # type: ignore
    except Exception:
        return None
    try:
        proc = psutil.Process(pid)
        start_ts = proc.create_time()
        return datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _get_process_start_time_windows(pid: int) -> Optional[str]:
    if os.name != "nt":
        import subprocess  # nosec B404
    try:
        cmd = (
            "Get-Process -Id "
            + str(int(pid))
            + " | Select-Object -ExpandProperty StartTime"
        )
        out = subprocess.check_output([
            "powershell",
            "-NoProfile",
            "-Command",
            cmd,
        ], text=True, stderr=subprocess.DEVNULL, timeout=3)
        raw = out.strip()
        if not raw:
            return None
        # PowerShell returns local time; normalize to UTC ISO if possible.
        try:
            dt = datetime.fromisoformat(raw)
        except Exception:
            try:
                dt = datetime.strptime(raw, "%m/%d/%Y %H:%M:%S")
            except Exception:
                return None
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def get_process_start_time(pid: int) -> Optional[str]:
    return _get_process_start_time_psutil(pid) or _get_process_start_time_windows(pid)


def _read_lock(path: Path) -> Optional[LockInfo]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return LockInfo(
            pid=int(payload.get("pid")),
            process_start_time_utc=str(payload.get("process_start_time_utc")),
            created_at_utc=str(payload.get("created_at_utc")),
            hostname=str(payload.get("hostname")),
            user=str(payload.get("user")),
            index_path=str(payload.get("index_path")),
        )
    except Exception:
        return None


def _is_lock_valid(lock: LockInfo) -> bool:
    if not lock or not lock.pid:
        return False
    start = get_process_start_time(lock.pid)
    if not start:
        return False
    return str(start) == str(lock.process_start_time_utc)


def acquire_index_lock(lock_path: Path, index_path: Path) -> LockInfo:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    start = get_process_start_time(pid) or _utc_now()
    info = LockInfo(
        pid=pid,
        process_start_time_utc=start,
        created_at_utc=_utc_now(),
        hostname=socket.gethostname(),
        user=getpass.getuser(),
        index_path=str(index_path),
    )

    while True:
        try:
            # Exclusive create
            with lock_path.open("x", encoding="utf-8") as f:
                json.dump(info.__dict__, f, indent=2)
            return info
        except FileExistsError:
            existing = _read_lock(lock_path)
            if existing and _is_lock_valid(existing):
                raise RuntimeError(
                    f"DAT-Index läuft bereits (pid={existing.pid})."
                )
            # stale lock: take over
            try:
                lock_path.unlink(missing_ok=True)
            except Exception:
                time.sleep(0.2)
        except Exception as exc:
            raise RuntimeError(f"Lockfile konnte nicht erstellt werden: {exc}")


def release_index_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        return
