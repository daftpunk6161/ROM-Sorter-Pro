"""Execution helpers for sort operations."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Protocol, Tuple


class CancelTokenProtocol(Protocol):
    def is_cancelled(self) -> bool: ...


def _is_cancelled(token: Optional[CancelTokenProtocol]) -> bool:
    return bool(token and token.is_cancelled())


def atomic_copy_with_cancel(
    src: Path,
    dst: Path,
    *,
    allow_replace: bool,
    cancel_token: Optional[CancelTokenProtocol],
    buffer_size: int = 1024 * 1024,
) -> bool:
    """Copy src -> dst atomically with cancellation support."""

    if _is_cancelled(cancel_token):
        return False

    if dst.exists() and not allow_replace:
        raise FileExistsError(str(dst))

    tmp = dst.with_name(dst.name + ".part")

    try:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                os.remove(str(tmp))

        cancelled_midway = False

        with open(src, "rb") as fsrc, open(tmp, "wb") as fdst:
            while True:
                if _is_cancelled(cancel_token):
                    cancelled_midway = True
                    break

                chunk = fsrc.read(buffer_size)
                if not chunk:
                    break
                fdst.write(chunk)

            if not cancelled_midway:
                try:
                    fdst.flush()
                    os.fsync(fdst.fileno())
                except Exception:
                    pass

        if cancelled_midway or _is_cancelled(cancel_token):
            return False

        os.replace(str(tmp), str(dst))

        try:
            shutil.copystat(src, dst, follow_symlinks=True)
        except Exception:
            pass

        return True

    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                try:
                    os.remove(str(tmp))
                except Exception:
                    pass


def run_conversion_with_cancel(
    cmd: List[str],
    cancel_token: Optional[CancelTokenProtocol],
) -> Tuple[bool, bool]:
    if _is_cancelled(cancel_token):
        return False, True

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return False, False

    while True:
        if _is_cancelled(cancel_token):
            try:
                process.terminate()
            except Exception:
                pass
            try:
                process.wait(timeout=2)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
            return False, True

        code = process.poll()
        if code is not None:
            return code == 0, False
        time.sleep(0.1)
