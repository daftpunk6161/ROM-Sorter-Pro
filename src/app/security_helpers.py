"""Security-related path helpers."""

from __future__ import annotations

from pathlib import Path


def has_symlink_parent(path: Path) -> bool:
    for parent in path.parents:
        try:
            if not parent.exists():
                continue
            if parent.is_symlink():
                return True
            try:
                resolved = parent.resolve(strict=False)
                absolute = parent.absolute()
                if resolved != absolute:
                    return True
            except Exception:
                continue
        except Exception:
            continue
    return False
