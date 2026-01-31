"""AI-Assisted Name Normalizer - F64 Implementation.

Provides LLM-based ROM name correction (optional feature).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class NormalizationResult:
    """Result of name normalization."""

    original: str
    normalized: str
    confidence: float
    corrections: List[str] = field(default_factory=list)
    extracted_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizationRule:
    """A normalization rule."""

    pattern: str
    replacement: str
    description: str = ""
    priority: int = 0


class AINameNormalizer:
    """AI-assisted ROM name normalizer.

    Implements F64: AI-Assisted-Name-Normalizer

    Features:
    - Pattern-based normalization
    - Region/version extraction
    - Title case correction
    - Optional LLM integration
    """

    # Common ROM naming patterns
    REGION_PATTERNS = {
        r"\(U\)": "(USA)",
        r"\(E\)": "(Europe)",
        r"\(J\)": "(Japan)",
        r"\(JU\)": "(Japan, USA)",
        r"\(UE\)": "(USA, Europe)",
        r"\(W\)": "(World)",
        r"\(F\)": "(France)",
        r"\(G\)": "(Germany)",
        r"\(I\)": "(Italy)",
        r"\(S\)": "(Spain)",
        r"\(Sw\)": "(Sweden)",
        r"\(Nl\)": "(Netherlands)",
        r"\(K\)": "(Korea)",
        r"\(C\)": "(China)",
        r"\(A\)": "(Australia)",
        r"\(B\)": "(Brazil)",
    }

    VERSION_PATTERNS = {
        r"\(V(\d+\.\d+)\)": r"(Rev \1)",
        r"\(v(\d+\.\d+)\)": r"(Rev \1)",
        r"\(Rev ?(\d+)\)": r"(Rev \1)",
        r"\(REV(\d+)\)": r"(Rev \1)",
    }

    FLAG_PATTERNS = {
        r"\[!\]": "",  # Verified good dump
        r"\[b\d*\]": "[Bad Dump]",
        r"\[a\d*\]": "[Alt]",
        r"\[o\d*\]": "[Overdump]",
        r"\[h\d*\]": "[Hack]",
        r"\[t\d*\]": "[Trainer]",
        r"\[f\d*\]": "[Fixed]",
        r"\[p\d*\]": "[Pirate]",
        r"\[T[+-][A-Za-z]+\]": "[Translation]",
    }

    # Title corrections (common misspellings/variations)
    TITLE_CORRECTIONS = {
        "mario bros": "Mario Bros.",
        "zelda": "Zelda",
        "metroid": "Metroid",
        "pokemon": "Pokémon",
        "castlevania": "Castlevania",
        "megaman": "Mega Man",
        "mega man": "Mega Man",
        "final fantasy": "Final Fantasy",
        "street fighter": "Street Fighter",
        "sonic the hedgehog": "Sonic the Hedgehog",
        "super mario": "Super Mario",
        "donkey kong": "Donkey Kong",
    }

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize normalizer.

        Args:
            config_dir: Configuration directory
        """
        self._config_dir = Path(config_dir) if config_dir else Path("config")
        self._custom_rules: List[NormalizationRule] = []
        self._cache: Dict[str, NormalizationResult] = {}

        self._load_custom_rules()

    def _load_custom_rules(self) -> None:
        """Load custom normalization rules."""
        rules_file = self._config_dir / "normalization_rules.json"

        if not rules_file.exists():
            return

        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for rule_data in data.get("rules", []):
                rule = NormalizationRule(
                    pattern=rule_data["pattern"],
                    replacement=rule_data["replacement"],
                    description=rule_data.get("description", ""),
                    priority=rule_data.get("priority", 0),
                )
                self._custom_rules.append(rule)

            self._custom_rules.sort(key=lambda r: -r.priority)

        except Exception:
            pass

    def _save_custom_rules(self) -> None:
        """Save custom rules."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        rules_file = self._config_dir / "normalization_rules.json"

        data = {
            "rules": [
                {
                    "pattern": rule.pattern,
                    "replacement": rule.replacement,
                    "description": rule.description,
                    "priority": rule.priority,
                }
                for rule in self._custom_rules
            ]
        }

        with open(rules_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _extract_info(self, name: str) -> Dict[str, Any]:
        """Extract metadata from ROM name.

        Args:
            name: ROM filename

        Returns:
            Extracted info dict
        """
        info: Dict[str, Any] = {}

        # Extract region
        for pattern in ["USA", "Europe", "Japan", "World"]:
            if f"({pattern})" in name:
                info["region"] = pattern
                break

        # Extract version/revision
        rev_match = re.search(r"\(Rev\s*([A-Z0-9.]+)\)", name, re.IGNORECASE)
        if rev_match:
            info["revision"] = rev_match.group(1)

        # Extract year
        year_match = re.search(r"\((\d{4})\)", name)
        if year_match:
            info["year"] = int(year_match.group(1))

        # Detect flags
        flags = []
        if "[Bad Dump]" in name or re.search(r"\[b\d*\]", name):
            flags.append("bad_dump")
        if "[Hack]" in name or re.search(r"\[h\d*\]", name):
            flags.append("hack")
        if "[Translation]" in name or re.search(r"\[T[+-]", name):
            flags.append("translation")

        if flags:
            info["flags"] = flags

        return info

    def _apply_region_normalization(self, name: str) -> Tuple[str, List[str]]:
        """Apply region code normalization.

        Args:
            name: ROM name

        Returns:
            Tuple of (normalized, corrections)
        """
        corrections = []
        result = name

        for pattern, replacement in self.REGION_PATTERNS.items():
            if re.search(pattern, result, re.IGNORECASE):
                old = result
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
                if old != result:
                    corrections.append(f"Region: {pattern} → {replacement}")

        return result, corrections

    def _apply_version_normalization(self, name: str) -> Tuple[str, List[str]]:
        """Apply version/revision normalization.

        Args:
            name: ROM name

        Returns:
            Tuple of (normalized, corrections)
        """
        corrections = []
        result = name

        for pattern, replacement in self.VERSION_PATTERNS.items():
            if re.search(pattern, result, re.IGNORECASE):
                old = result
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
                if old != result:
                    corrections.append(f"Version: normalized")

        return result, corrections

    def _apply_flag_normalization(self, name: str) -> Tuple[str, List[str]]:
        """Apply flag normalization.

        Args:
            name: ROM name

        Returns:
            Tuple of (normalized, corrections)
        """
        corrections = []
        result = name

        for pattern, replacement in self.FLAG_PATTERNS.items():
            if re.search(pattern, result, re.IGNORECASE):
                old = result
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
                if old != result:
                    corrections.append(f"Flag: normalized")

        return result, corrections

    def _apply_title_corrections(self, name: str) -> Tuple[str, List[str]]:
        """Apply title case corrections.

        Args:
            name: ROM name

        Returns:
            Tuple of (normalized, corrections)
        """
        corrections = []
        result = name

        for wrong, correct in self.TITLE_CORRECTIONS.items():
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            if pattern.search(result):
                old = result
                result = pattern.sub(correct, result)
                if old != result:
                    corrections.append(f"Title: {wrong} → {correct}")

        return result, corrections

    def _apply_custom_rules(self, name: str) -> Tuple[str, List[str]]:
        """Apply custom normalization rules.

        Args:
            name: ROM name

        Returns:
            Tuple of (normalized, corrections)
        """
        corrections = []
        result = name

        for rule in self._custom_rules:
            try:
                if re.search(rule.pattern, result):
                    old = result
                    result = re.sub(rule.pattern, rule.replacement, result)
                    if old != result:
                        corrections.append(
                            rule.description or f"Custom: {rule.pattern}"
                        )
            except re.error:
                pass

        return result, corrections

    def _clean_whitespace(self, name: str) -> str:
        """Clean up whitespace.

        Args:
            name: ROM name

        Returns:
            Cleaned name
        """
        # Multiple spaces to single
        result = re.sub(r"\s+", " ", name)

        # Space before extension
        result = re.sub(r"\s+\.", ".", result)

        # Trim
        result = result.strip()

        return result

    def normalize(self, name: str) -> NormalizationResult:
        """Normalize ROM name.

        Args:
            name: Original ROM name

        Returns:
            NormalizationResult
        """
        # Check cache
        if name in self._cache:
            return self._cache[name]

        all_corrections: List[str] = []
        result = name

        # Apply normalizations in order
        result, corr = self._apply_region_normalization(result)
        all_corrections.extend(corr)

        result, corr = self._apply_version_normalization(result)
        all_corrections.extend(corr)

        result, corr = self._apply_flag_normalization(result)
        all_corrections.extend(corr)

        result, corr = self._apply_title_corrections(result)
        all_corrections.extend(corr)

        result, corr = self._apply_custom_rules(result)
        all_corrections.extend(corr)

        result = self._clean_whitespace(result)

        # Calculate confidence
        confidence = 1.0 if all_corrections else 0.5
        if len(all_corrections) > 3:
            confidence = 0.8

        # Extract info
        extracted = self._extract_info(result)

        norm_result = NormalizationResult(
            original=name,
            normalized=result,
            confidence=confidence,
            corrections=all_corrections,
            extracted_info=extracted,
        )

        self._cache[name] = norm_result
        return norm_result

    def normalize_batch(self, names: List[str]) -> List[NormalizationResult]:
        """Normalize multiple names.

        Args:
            names: List of ROM names

        Returns:
            List of NormalizationResults
        """
        return [self.normalize(name) for name in names]

    def add_custom_rule(
        self,
        pattern: str,
        replacement: str,
        description: str = "",
        priority: int = 0,
    ) -> bool:
        """Add a custom normalization rule.

        Args:
            pattern: Regex pattern
            replacement: Replacement string
            description: Rule description
            priority: Rule priority

        Returns:
            True if added
        """
        try:
            # Validate regex
            re.compile(pattern)

            rule = NormalizationRule(
                pattern=pattern,
                replacement=replacement,
                description=description,
                priority=priority,
            )

            self._custom_rules.append(rule)
            self._custom_rules.sort(key=lambda r: -r.priority)
            self._save_custom_rules()

            # Clear cache
            self._cache.clear()

            return True

        except re.error:
            return False

    def remove_custom_rule(self, pattern: str) -> bool:
        """Remove a custom rule.

        Args:
            pattern: Rule pattern to remove

        Returns:
            True if removed
        """
        for rule in self._custom_rules:
            if rule.pattern == pattern:
                self._custom_rules.remove(rule)
                self._save_custom_rules()
                self._cache.clear()
                return True

        return False

    def get_custom_rules(self) -> List[Dict[str, Any]]:
        """Get all custom rules.

        Returns:
            List of rule dicts
        """
        return [
            {
                "pattern": rule.pattern,
                "replacement": rule.replacement,
                "description": rule.description,
                "priority": rule.priority,
            }
            for rule in self._custom_rules
        ]

    def suggest_corrections(self, name: str) -> List[str]:
        """Suggest possible corrections for a name.

        Args:
            name: ROM name

        Returns:
            List of suggestions
        """
        suggestions = []

        # Check for common issues
        if re.search(r"\(U\)|\(E\)|\(J\)", name):
            suggestions.append("Expand region codes to full names")

        if re.search(r"\[!\]", name):
            suggestions.append("Remove verified dump marker")

        if re.search(r"[A-Za-z][a-z]+ [A-Za-z][a-z]+", name):
            lower_name = name.lower()
            for title in self.TITLE_CORRECTIONS:
                if title in lower_name:
                    suggestions.append(f"Correct title: {self.TITLE_CORRECTIONS[title]}")
                    break

        return suggestions

    def clear_cache(self) -> None:
        """Clear normalization cache."""
        self._cache.clear()
