"""Soft-Patching Support - F82 Implementation.

Provides runtime patching without modifying original ROM files.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Tuple, Union

from .patcher import Patcher, PatchFormat


@dataclass
class PatchHunk:
    """A single patch hunk (modification)."""

    offset: int
    original_data: bytes
    patched_data: bytes


class PatchedRomStream:
    """A read-only stream that applies patches on-the-fly.

    Provides a file-like interface that returns patched data
    without modifying the original ROM file.
    """

    def __init__(
        self,
        rom_path: str,
        patches: List[PatchHunk],
        patched_size: Optional[int] = None,
    ):
        """Initialize patched ROM stream.

        Args:
            rom_path: Path to original ROM
            patches: List of patch hunks to apply
            patched_size: Size after patching (for extensions)
        """
        self._rom_path = rom_path
        self._patches = sorted(patches, key=lambda p: p.offset)
        self._position = 0

        # Get original size
        self._original_size = Path(rom_path).stat().st_size
        self._patched_size = patched_size or self._original_size

        # Build patch index for fast lookup
        self._patch_index: Dict[int, PatchHunk] = {}
        for hunk in self._patches:
            for i, byte in enumerate(hunk.patched_data):
                self._patch_index[hunk.offset + i] = hunk

        # Open ROM file
        self._file: Optional[BinaryIO] = None

    def __enter__(self) -> "PatchedRomStream":
        self._file = open(self._rom_path, "rb")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._file:
            self._file.close()
            self._file = None

    def read(self, size: int = -1) -> bytes:
        """Read bytes from patched ROM.

        Args:
            size: Number of bytes to read (-1 for all)

        Returns:
            Patched bytes
        """
        if self._file is None:
            raise ValueError("Stream not opened. Use 'with' statement.")

        if size == -1:
            size = self._patched_size - self._position

        if self._position >= self._patched_size:
            return b""

        # Cap size at remaining bytes
        size = min(size, self._patched_size - self._position)

        result = bytearray(size)
        bytes_read = 0

        while bytes_read < size:
            current_pos = self._position + bytes_read

            # Check if we're in a patched region
            patched_byte = self._get_patched_byte(current_pos)
            if patched_byte is not None:
                result[bytes_read] = patched_byte
                bytes_read += 1
            else:
                # Read from original file
                if current_pos < self._original_size:
                    self._file.seek(current_pos)
                    chunk_size = min(size - bytes_read, self._original_size - current_pos)

                    # Check how many consecutive unpatched bytes we can read
                    for i in range(chunk_size):
                        if self._get_patched_byte(current_pos + i) is not None:
                            chunk_size = i
                            break

                    if chunk_size > 0:
                        chunk = self._file.read(chunk_size)
                        result[bytes_read : bytes_read + len(chunk)] = chunk
                        bytes_read += len(chunk)
                    else:
                        # Single patched byte
                        result[bytes_read] = self._get_patched_byte(current_pos) or 0
                        bytes_read += 1
                else:
                    # Beyond original file (extension)
                    result[bytes_read] = 0
                    bytes_read += 1

        self._position += bytes_read
        return bytes(result)

    def seek(self, offset: int, whence: int = 0) -> int:
        """Seek to position.

        Args:
            offset: Offset to seek
            whence: 0=start, 1=current, 2=end

        Returns:
            New position
        """
        if whence == 0:
            self._position = offset
        elif whence == 1:
            self._position += offset
        elif whence == 2:
            self._position = self._patched_size + offset

        self._position = max(0, min(self._position, self._patched_size))
        return self._position

    def tell(self) -> int:
        """Get current position."""
        return self._position

    def _get_patched_byte(self, offset: int) -> Optional[int]:
        """Get patched byte at offset if it exists."""
        for hunk in self._patches:
            if hunk.offset <= offset < hunk.offset + len(hunk.patched_data):
                return hunk.patched_data[offset - hunk.offset]
        return None

    @property
    def size(self) -> int:
        """Get patched size."""
        return self._patched_size


class SoftPatcher:
    """Soft-patching engine for runtime ROM patching.

    Implements F82: Soft-Patching-Support

    Benefits:
    - Original ROM stays unmodified
    - Multiple patches can be applied
    - Memory-efficient streaming
    - Perfect for emulator integration
    """

    def __init__(self):
        """Initialize soft patcher."""
        self._patcher = Patcher(verify_checksums=False)

    def create_patched_stream(
        self,
        rom_path: str,
        patch_path: str,
    ) -> Optional[PatchedRomStream]:
        """Create a patched ROM stream.

        Args:
            rom_path: Path to original ROM
            patch_path: Path to patch file

        Returns:
            PatchedRomStream or None if failed
        """
        # Detect format
        patch_format = self._patcher.detect_format(patch_path)
        if patch_format == PatchFormat.UNKNOWN:
            return None

        try:
            # Parse patch to get hunks
            hunks, patched_size = self._parse_patch(rom_path, patch_path, patch_format)

            return PatchedRomStream(rom_path, hunks, patched_size)

        except Exception:
            return None

    def create_multi_patched_stream(
        self,
        rom_path: str,
        patch_paths: List[str],
    ) -> Optional[PatchedRomStream]:
        """Create stream with multiple patches applied in order.

        Args:
            rom_path: Original ROM path
            patch_paths: Patch paths in order

        Returns:
            PatchedRomStream or None
        """
        if not patch_paths:
            return None

        all_hunks: List[PatchHunk] = []
        current_size = Path(rom_path).stat().st_size

        for patch_path in patch_paths:
            patch_format = self._patcher.detect_format(patch_path)
            if patch_format == PatchFormat.UNKNOWN:
                continue

            try:
                hunks, new_size = self._parse_patch(rom_path, patch_path, patch_format)
                all_hunks.extend(hunks)
                if new_size > current_size:
                    current_size = new_size
            except Exception:
                continue

        if not all_hunks:
            return None

        return PatchedRomStream(rom_path, all_hunks, current_size)

    def get_patched_bytes(
        self,
        rom_path: str,
        patch_path: str,
    ) -> Optional[bytes]:
        """Get fully patched ROM as bytes.

        Note: For large ROMs, prefer create_patched_stream().

        Args:
            rom_path: ROM path
            patch_path: Patch path

        Returns:
            Patched ROM bytes or None
        """
        stream = self.create_patched_stream(rom_path, patch_path)
        if not stream:
            return None

        with stream:
            return stream.read()

    def _parse_patch(
        self,
        rom_path: str,
        patch_path: str,
        patch_format: PatchFormat,
    ) -> Tuple[List[PatchHunk], int]:
        """Parse patch file to extract hunks.

        Args:
            rom_path: ROM path
            patch_path: Patch path
            patch_format: Patch format

        Returns:
            Tuple of (hunks, patched_size)
        """
        # Read original ROM
        with open(rom_path, "rb") as f:
            original_data = f.read()

        original_size = len(original_data)

        if patch_format == PatchFormat.IPS:
            return self._parse_ips_hunks(original_data, patch_path)
        elif patch_format == PatchFormat.BPS:
            return self._parse_bps_hunks(original_data, patch_path)
        elif patch_format == PatchFormat.UPS:
            return self._parse_ups_hunks(original_data, patch_path)
        else:
            return [], original_size

    def _parse_ips_hunks(
        self,
        original_data: bytes,
        patch_path: str,
    ) -> Tuple[List[PatchHunk], int]:
        """Parse IPS patch to hunks."""
        hunks: List[PatchHunk] = []
        patched_size = len(original_data)

        with open(patch_path, "rb") as f:
            # Skip header
            header = f.read(5)
            if header != b"PATCH":
                return [], patched_size

            while True:
                offset_bytes = f.read(3)
                if offset_bytes == b"EOF" or len(offset_bytes) < 3:
                    break

                offset = int.from_bytes(offset_bytes, "big")
                size = int.from_bytes(f.read(2), "big")

                if size == 0:
                    # RLE
                    rle_size = int.from_bytes(f.read(2), "big")
                    rle_byte = f.read(1)
                    patched_data = rle_byte * rle_size

                    # Get original data
                    if offset < len(original_data):
                        orig_end = min(offset + rle_size, len(original_data))
                        original = original_data[offset:orig_end]
                        if orig_end < offset + rle_size:
                            original += b"\x00" * (offset + rle_size - orig_end)
                    else:
                        original = b"\x00" * rle_size

                    hunks.append(PatchHunk(offset, original, patched_data))
                    patched_size = max(patched_size, offset + rle_size)
                else:
                    patched_data = f.read(size)

                    # Get original data
                    if offset < len(original_data):
                        orig_end = min(offset + size, len(original_data))
                        original = original_data[offset:orig_end]
                        if orig_end < offset + size:
                            original += b"\x00" * (offset + size - orig_end)
                    else:
                        original = b"\x00" * size

                    hunks.append(PatchHunk(offset, original, patched_data))
                    patched_size = max(patched_size, offset + size)

        return hunks, patched_size

    def _parse_bps_hunks(
        self,
        original_data: bytes,
        patch_path: str,
    ) -> Tuple[List[PatchHunk], int]:
        """Parse BPS patch to hunks.

        BPS is complex - for soft-patching, we apply the full patch
        and extract differences.
        """
        # Apply full patch and compare
        result = self._patcher.apply(
            # Need to create temp file or use in-memory
            str(Path(patch_path).parent / "_temp_rom"),
            patch_path,
        )

        # For BPS, we need to fully apply and diff
        # This is a simplified approach - full implementation would
        # parse BPS actions directly
        try:
            patched_data = bytearray(original_data)
            patched_data, _ = self._patcher._apply_bps(patched_data, patch_path)

            return self._diff_to_hunks(original_data, bytes(patched_data))
        except Exception:
            return [], len(original_data)

    def _parse_ups_hunks(
        self,
        original_data: bytes,
        patch_path: str,
    ) -> Tuple[List[PatchHunk], int]:
        """Parse UPS patch to hunks."""
        try:
            patched_data = bytearray(original_data)
            patched_data, _ = self._patcher._apply_ups(patched_data, patch_path)

            return self._diff_to_hunks(original_data, bytes(patched_data))
        except Exception:
            return [], len(original_data)

    def _diff_to_hunks(
        self,
        original: bytes,
        patched: bytes,
    ) -> Tuple[List[PatchHunk], int]:
        """Convert difference between two byte arrays to hunks."""
        hunks: List[PatchHunk] = []
        max_len = max(len(original), len(patched))

        i = 0
        while i < max_len:
            # Find start of difference
            while i < max_len:
                orig_byte = original[i] if i < len(original) else 0
                patch_byte = patched[i] if i < len(patched) else 0
                if orig_byte != patch_byte:
                    break
                i += 1

            if i >= max_len:
                break

            # Find end of difference
            start = i
            while i < max_len:
                orig_byte = original[i] if i < len(original) else 0
                patch_byte = patched[i] if i < len(patched) else 0
                if orig_byte == patch_byte:
                    # Check for short same-run
                    same_count = 0
                    j = i
                    while j < max_len and same_count < 4:
                        o = original[j] if j < len(original) else 0
                        p = patched[j] if j < len(patched) else 0
                        if o == p:
                            same_count += 1
                            j += 1
                        else:
                            break
                    if same_count >= 4:
                        break
                i += 1

            # Create hunk
            orig_data = bytes(
                original[start:i] if start < len(original) else b""
            )
            if len(orig_data) < i - start:
                orig_data += b"\x00" * (i - start - len(orig_data))

            patch_data = bytes(
                patched[start:i] if start < len(patched) else b""
            )
            if len(patch_data) < i - start:
                patch_data += b"\x00" * (i - start - len(patch_data))

            hunks.append(PatchHunk(start, orig_data, patch_data))

        return hunks, len(patched)


def soft_patch(rom_path: str, patch_path: str) -> Optional[PatchedRomStream]:
    """Convenience function for soft-patching.

    Args:
        rom_path: ROM path
        patch_path: Patch path

    Returns:
        PatchedRomStream or None
    """
    patcher = SoftPatcher()
    return patcher.create_patched_stream(rom_path, patch_path)
