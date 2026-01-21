#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - ROM Models

This module contains the central data models for ROM files.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from pathlib import Path


@dataclass
class ROMMetadata:
    """Detailed metadata for ROM files."""

# Basic fields
    filename: str
    path: Path
    size: int = 0

# Console information
    console: str = "Unknown"
    console_folder: str = "Unknown"

# File metadata
    extension: str = ""
    md5_hash: str = ""
    crc32: str = ""
    sha1: str = ""

# Game information
    title: str = ""
    region: str = "Unknown"
    languages: List[str] = field(default_factory=list)
    year: int = 0
    publisher: str = "Unknown"
    developer: str = "Unknown"

# Special flags
    is_verified: bool = False
    is_homebrew: bool = False
    is_demo: bool = False
    is_beta: bool = False
    is_hack: bool = False

# Reviews and metadata
    rating: float = 0.0
    tags: List[str] = field(default_factory=list)
    detection_confidence: float = 0.0

# System information
    last_modified: datetime = field(default_factory=datetime.now)
    processing_history: List[str] = field(default_factory=list)

    def add_processing_entry(self, entry: str) -> None:
        """Adds an entry to the processing history."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.processing_history.append(f"[{timestamp}] {entry}")

    @property
    def is_processed(self) -> bool:
        """Indicates whether the ROM has already been processed."""
        return len(self.processing_history) > 0

    @property
    def file_exists(self) -> bool:
        """Checks if the file exists."""
        return Path(self.path).exists() if self.path else False


@dataclass
class EnhancedROM(ROMMetadata):
    """Enhanced ROM class with additional features."""

# More metadata
    box_art_url: str = ""
    screenshot_url: str = ""
    description: str = ""
    genres: List[str] = field(default_factory=list)
    release_dates: Dict[str, str] = field(default_factory=dict)
    alternative_titles: List[str] = field(default_factory=list)

# Reviews and community information
    community_rating: float = 0.0
    download_count: int = 0
    popularity_score: float = 0.0

# Technical details
    rom_format: str = "Unknown"  # z.B. "No-Intro", "Redump", "TOSEC"
    rom_status: str = "Unknown"  # z.B. "Good", "Bad", "Verified"
    requires_bios: bool = False
    bios_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert the rome into a dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedROM':
        """Creates a rome from a dictionary."""
# Make sure that Path objects are created correctly
        if 'path' in data and isinstance(data['path'], str):
            data['path'] = Path(data['path'])

# Convert dateTime objects
        if 'last_modified' in data and isinstance(data['last_modified'], str):
            try:
                data['last_modified'] = datetime.fromisoformat(data['last_modified'])
            except ValueError:
                data['last_modified'] = datetime.now()

# Create instance
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class ROMCollection:
    """Collection of ROMS with search functions."""

    roms: List[EnhancedROM] = field(default_factory=list)
    name: str = "ROM Collection"
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def add_rom(self, rom: EnhancedROM) -> None:
        """Adds a rom to the collection."""
        self.roms.append(rom)
        self.last_updated = datetime.now()

    def find_by_console(self, console: str) -> List[EnhancedROM]:
        """Find of all roms for a specific console."""
        return [rom for rom in self.roms if rom.console.lower() == console.lower()]

    def find_by_title(self, title_fragment: str) -> List[EnhancedROM]:
        """Finds all roms with a specific title fragment."""
        return [rom for rom in self.roms if title_fragment.lower() in rom.title.lower()]

    def find_duplicates(self) -> Dict[str, List[EnhancedROM]]:
        """Finds duplicates based on MD5 hash."""
        hash_map: Dict[str, List[EnhancedROM]] = {}

        for rom in self.roms:
            if rom.md5_hash:
                if rom.md5_hash not in hash_map:
                    hash_map[rom.md5_hash] = []
                hash_map[rom.md5_hash].append(rom)

# Only return entries with more than one Rome
        return {hash_val: rom_list for hash_val, rom_list in hash_map.items() if len(rom_list) > 1}

    def get_statistics(self) -> Dict[str, Any]:
        """Returns statistics about the collection."""
        console_counts: Dict[str, int] = {}
        total_size = 0
        regions: Set[str] = set()

        for rom in self.roms:
            if rom.console not in console_counts:
                console_counts[rom.console] = 0
            console_counts[rom.console] += 1

            total_size += rom.size
            if rom.region:
                regions.add(rom.region)

        return {
            "total_roms": len(self.roms),
            "consoles": len(console_counts),
            "console_distribution": console_counts,
            "total_size_bytes": total_size,
            "regions": list(regions),
            "updated_at": self.last_updated.isoformat()
        }
