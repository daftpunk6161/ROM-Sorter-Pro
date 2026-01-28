"""Security-related path helpers."""

from __future__ import annotations

from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def has_symlink_parent(path: Path) -> bool:
    for parent in path.parents:
        skip_parent = False
        try:
            if not parent.exists():
                skip_parent = True
            elif parent.is_symlink():
                return True
            else:
                try:
                    resolved = parent.resolve(strict=False)
                    absolute = parent.absolute()
                    if resolved != absolute:
                        return True
                except Exception as exc:
                    logger.debug("Symlink parent resolution failed: %s", exc)
                    skip_parent = True
        except Exception as exc:
            logger.debug("Symlink parent check failed: %s", exc)
            skip_parent = True
        if skip_parent:
            continue
    return False
