"""IPS/BPS/UPS Patcher - F79 Implementation.

Applies ROM patches in common formats:
- IPS (International Patching System)
- BPS (Beat Patching System)
- UPS (Universal Patching System)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum, auto
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional, Tuple, Union
import zlib


class PatchFormat(Enum):
    """Supported patch formats."""

    IPS = auto()  # International Patching System
    BPS = auto()  # Beat Patching System
    UPS = auto()  # Universal Patching System
    UNKNOWN = auto()


@dataclass
class PatchResult:
    """Result of a patch operation."""

    success: bool
    output_path: Optional[str] = None
    original_size: int = 0
    patched_size: int = 0
    format_used: PatchFormat = PatchFormat.UNKNOWN
    error: Optional[str] = None
    checksum_valid: bool = True


class Patcher:
    """ROM Patcher supporting IPS, BPS, and UPS formats.

    Implements F79: IPS/BPS/UPS-Patcher
    """

    # Magic bytes for format detection
    IPS_MAGIC = b"PATCH"
    BPS_MAGIC = b"BPS1"
    UPS_MAGIC = b"UPS1"

    def __init__(self, verify_checksums: bool = True):
        """Initialize patcher.

        Args:
            verify_checksums: Verify checksums for BPS/UPS patches
        """
        self.verify_checksums = verify_checksums

    def detect_format(self, patch_path: str) -> PatchFormat:
        """Detect patch format from file.

        Args:
            patch_path: Path to patch file

        Returns:
            Detected PatchFormat
        """
        try:
            with open(patch_path, "rb") as f:
                header = f.read(5)

            if header == self.IPS_MAGIC:
                return PatchFormat.IPS
            if header[:4] == self.BPS_MAGIC:
                return PatchFormat.BPS
            if header[:4] == self.UPS_MAGIC:
                return PatchFormat.UPS

        except OSError:
            pass

        return PatchFormat.UNKNOWN

    def apply(
        self,
        rom_path: str,
        patch_path: str,
        output_path: Optional[str] = None,
    ) -> PatchResult:
        """Apply a patch to a ROM file.

        Args:
            rom_path: Path to source ROM
            patch_path: Path to patch file
            output_path: Path for patched ROM (default: rom_path with .patched extension)

        Returns:
            PatchResult with status and details
        """
        patch_format = self.detect_format(patch_path)

        if patch_format == PatchFormat.UNKNOWN:
            return PatchResult(
                success=False,
                error=f"Unknown patch format: {patch_path}",
            )

        if output_path is None:
            rom_p = Path(rom_path)
            output_path = str(rom_p.parent / f"{rom_p.stem}.patched{rom_p.suffix}")

        try:
            # Read source ROM
            with open(rom_path, "rb") as f:
                rom_data = bytearray(f.read())

            original_size = len(rom_data)

            # Apply patch based on format
            if patch_format == PatchFormat.IPS:
                patched_data = self._apply_ips(rom_data, patch_path)
            elif patch_format == PatchFormat.BPS:
                patched_data, checksum_valid = self._apply_bps(rom_data, patch_path)
            elif patch_format == PatchFormat.UPS:
                patched_data, checksum_valid = self._apply_ups(rom_data, patch_path)
            else:
                return PatchResult(success=False, error="Unsupported format")

            # Write output
            with open(output_path, "wb") as f:
                f.write(patched_data)

            return PatchResult(
                success=True,
                output_path=output_path,
                original_size=original_size,
                patched_size=len(patched_data),
                format_used=patch_format,
                checksum_valid=checksum_valid if patch_format != PatchFormat.IPS else True,
            )

        except Exception as e:
            return PatchResult(
                success=False,
                error=str(e),
                format_used=patch_format,
            )

    def _apply_ips(self, rom_data: bytearray, patch_path: str) -> bytearray:
        """Apply IPS patch.

        IPS Format:
        - Header: "PATCH" (5 bytes)
        - Records: [offset(3) + size(2) + data(size)] or [offset(3) + 0x0000 + RLE_size(2) + RLE_byte(1)]
        - Footer: "EOF" (3 bytes)
        """
        with open(patch_path, "rb") as f:
            # Skip header
            header = f.read(5)
            if header != self.IPS_MAGIC:
                raise ValueError("Invalid IPS header")

            while True:
                # Read offset (3 bytes, big-endian)
                offset_bytes = f.read(3)
                if offset_bytes == b"EOF" or len(offset_bytes) < 3:
                    break

                offset = int.from_bytes(offset_bytes, "big")

                # Read size (2 bytes, big-endian)
                size_bytes = f.read(2)
                if len(size_bytes) < 2:
                    break

                size = int.from_bytes(size_bytes, "big")

                if size == 0:
                    # RLE record
                    rle_size = int.from_bytes(f.read(2), "big")
                    rle_byte = f.read(1)

                    # Extend ROM if needed
                    if offset + rle_size > len(rom_data):
                        rom_data.extend(b"\x00" * (offset + rle_size - len(rom_data)))

                    # Fill with RLE byte
                    rom_data[offset : offset + rle_size] = rle_byte * rle_size
                else:
                    # Normal record
                    data = f.read(size)

                    # Extend ROM if needed
                    if offset + size > len(rom_data):
                        rom_data.extend(b"\x00" * (offset + size - len(rom_data)))

                    # Apply patch data
                    rom_data[offset : offset + size] = data

        return rom_data

    def _apply_bps(
        self, rom_data: bytearray, patch_path: str
    ) -> Tuple[bytearray, bool]:
        """Apply BPS patch.

        BPS Format uses variable-length integers and delta encoding.
        """
        with open(patch_path, "rb") as f:
            patch_data = f.read()

        # Parse header
        if patch_data[:4] != self.BPS_MAGIC:
            raise ValueError("Invalid BPS header")

        pos = 4
        source_size, pos = _decode_bps_number(patch_data, pos)
        target_size, pos = _decode_bps_number(patch_data, pos)
        metadata_size, pos = _decode_bps_number(patch_data, pos)
        pos += metadata_size  # Skip metadata

        # Verify source size
        if len(rom_data) != source_size:
            raise ValueError(f"Source size mismatch: expected {source_size}, got {len(rom_data)}")

        # Create output buffer
        output = bytearray(target_size)
        output_pos = 0
        source_rel = 0
        target_rel = 0

        # Get checksums from footer
        footer_start = len(patch_data) - 12
        source_crc = int.from_bytes(patch_data[footer_start : footer_start + 4], "little")
        target_crc = int.from_bytes(patch_data[footer_start + 4 : footer_start + 8], "little")
        patch_crc = int.from_bytes(patch_data[footer_start + 8 : footer_start + 12], "little")

        # Process actions
        while pos < footer_start:
            data, pos = _decode_bps_number(patch_data, pos)
            action = data & 3
            length = (data >> 2) + 1

            if action == 0:  # SourceRead
                output[output_pos : output_pos + length] = rom_data[output_pos : output_pos + length]
                output_pos += length

            elif action == 1:  # TargetRead
                output[output_pos : output_pos + length] = patch_data[pos : pos + length]
                pos += length
                output_pos += length

            elif action == 2:  # SourceCopy
                offset_data, pos = _decode_bps_number(patch_data, pos)
                offset = (-1 if offset_data & 1 else 1) * (offset_data >> 1)
                source_rel += offset
                output[output_pos : output_pos + length] = rom_data[source_rel : source_rel + length]
                source_rel += length
                output_pos += length

            elif action == 3:  # TargetCopy
                offset_data, pos = _decode_bps_number(patch_data, pos)
                offset = (-1 if offset_data & 1 else 1) * (offset_data >> 1)
                target_rel += offset
                for _ in range(length):
                    output[output_pos] = output[target_rel]
                    output_pos += 1
                    target_rel += 1

        # Verify checksums
        checksum_valid = True
        if self.verify_checksums:
            actual_source_crc = zlib.crc32(bytes(rom_data)) & 0xFFFFFFFF
            actual_target_crc = zlib.crc32(bytes(output)) & 0xFFFFFFFF

            if actual_source_crc != source_crc:
                checksum_valid = False
            if actual_target_crc != target_crc:
                checksum_valid = False

        return output, checksum_valid

    def _apply_ups(
        self, rom_data: bytearray, patch_path: str
    ) -> Tuple[bytearray, bool]:
        """Apply UPS patch.

        UPS uses XOR-based delta encoding.
        """
        with open(patch_path, "rb") as f:
            patch_data = f.read()

        # Parse header
        if patch_data[:4] != self.UPS_MAGIC:
            raise ValueError("Invalid UPS header")

        pos = 4
        source_size, pos = _decode_ups_number(patch_data, pos)
        target_size, pos = _decode_ups_number(patch_data, pos)

        # Verify source size
        if len(rom_data) != source_size:
            raise ValueError(f"Source size mismatch: expected {source_size}, got {len(rom_data)}")

        # Create output as copy of source
        output = bytearray(rom_data)
        if target_size > len(output):
            output.extend(b"\x00" * (target_size - len(output)))
        elif target_size < len(output):
            output = output[:target_size]

        # Get checksums from footer
        footer_start = len(patch_data) - 12
        source_crc = int.from_bytes(patch_data[footer_start : footer_start + 4], "little")
        target_crc = int.from_bytes(patch_data[footer_start + 4 : footer_start + 8], "little")
        patch_crc = int.from_bytes(patch_data[footer_start + 8 : footer_start + 12], "little")

        # Apply XOR hunks
        output_pos = 0
        while pos < footer_start:
            offset, pos = _decode_ups_number(patch_data, pos)
            output_pos += offset

            while pos < footer_start and patch_data[pos] != 0:
                if output_pos < len(output):
                    output[output_pos] ^= patch_data[pos]
                output_pos += 1
                pos += 1

            pos += 1  # Skip terminator
            output_pos += 1

        # Verify checksums
        checksum_valid = True
        if self.verify_checksums:
            actual_source_crc = zlib.crc32(bytes(rom_data)) & 0xFFFFFFFF
            actual_target_crc = zlib.crc32(bytes(output)) & 0xFFFFFFFF

            if actual_source_crc != source_crc:
                checksum_valid = False
            if actual_target_crc != target_crc:
                checksum_valid = False

        return output, checksum_valid


def _decode_bps_number(data: bytes, pos: int) -> Tuple[int, int]:
    """Decode BPS variable-length number."""
    result = 0
    shift = 1
    while True:
        byte = data[pos]
        pos += 1
        result += (byte & 0x7F) * shift
        if byte & 0x80:
            break
        shift <<= 7
        result += shift
    return result, pos


def _decode_ups_number(data: bytes, pos: int) -> Tuple[int, int]:
    """Decode UPS variable-length number."""
    result = 0
    shift = 1
    while True:
        byte = data[pos]
        pos += 1
        result += (byte & 0x7F) * shift
        if byte & 0x80:
            break
        shift <<= 7
        result += shift
    return result, pos


# Convenience functions
def apply_ips_patch(rom_path: str, patch_path: str, output_path: Optional[str] = None) -> PatchResult:
    """Apply IPS patch to ROM."""
    patcher = Patcher()
    return patcher.apply(rom_path, patch_path, output_path)


def apply_bps_patch(rom_path: str, patch_path: str, output_path: Optional[str] = None) -> PatchResult:
    """Apply BPS patch to ROM."""
    patcher = Patcher()
    return patcher.apply(rom_path, patch_path, output_path)


def apply_ups_patch(rom_path: str, patch_path: str, output_path: Optional[str] = None) -> PatchResult:
    """Apply UPS patch to ROM."""
    patcher = Patcher()
    return patcher.apply(rom_path, patch_path, output_path)


def create_ips_patch(
    original_path: str,
    modified_path: str,
    patch_path: str,
) -> bool:
    """Create IPS patch from two ROM files.

    Args:
        original_path: Path to original ROM
        modified_path: Path to modified ROM
        patch_path: Path for output patch file

    Returns:
        True if patch was created successfully
    """
    try:
        with open(original_path, "rb") as f:
            original = f.read()
        with open(modified_path, "rb") as f:
            modified = f.read()

        # IPS has 24-bit offset limit
        max_size = min(0xFFFFFF, max(len(original), len(modified)))

        with open(patch_path, "wb") as f:
            # Write header
            f.write(b"PATCH")

            # Find and write differences
            i = 0
            while i < max_size:
                # Find start of difference
                while i < max_size:
                    orig_byte = original[i] if i < len(original) else 0
                    mod_byte = modified[i] if i < len(modified) else 0
                    if orig_byte != mod_byte:
                        break
                    i += 1

                if i >= max_size:
                    break

                # Find end of difference (max 0xFFFF bytes)
                start = i
                while i < max_size and i - start < 0xFFFF:
                    orig_byte = original[i] if i < len(original) else 0
                    mod_byte = modified[i] if i < len(modified) else 0
                    if orig_byte == mod_byte:
                        # Check if this is a short same-run
                        same_count = 0
                        j = i
                        while j < max_size and same_count < 6:
                            orig_j = original[j] if j < len(original) else 0
                            mod_j = modified[j] if j < len(modified) else 0
                            if orig_j == mod_j:
                                same_count += 1
                                j += 1
                            else:
                                break
                        if same_count >= 6:
                            break
                    i += 1

                # Write record
                length = i - start
                if length > 0:
                    # Offset (3 bytes)
                    f.write(start.to_bytes(3, "big"))
                    # Size (2 bytes)
                    f.write(length.to_bytes(2, "big"))
                    # Data
                    for j in range(start, start + length):
                        byte = modified[j] if j < len(modified) else 0
                        f.write(bytes([byte]))

            # Write footer
            f.write(b"EOF")

        return True

    except Exception:
        return False
