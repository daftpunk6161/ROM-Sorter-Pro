#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROM SARTER PRO-Fuzzy matching functions This module provides functions for fuzzy-string matching that for the ROM detection and similarity comparisons are used."""

import re
import logging
from typing import List, Tuple, TypeVar, Callable, Generic, Optional, Set, Dict, Any, Union
from functools import lru_cache

# Type variable for generic functions
T = TypeVar('T')

# Logger
logger = logging.getLogger(__name__)

# Attempts to import the external fuzzywuzzy module
try:
    from fuzzywuzzy import fuzz, process
    _USE_EXTERNAL_FUZZ = True
    logger.debug("Externe fuzzywuzzy-Bibliothek geladen")
except ImportError:
    # Fallback auf unsere eigene Implementierung
    _USE_EXTERNAL_FUZZ = False
    logger.debug("Fallback auf interne Fuzzy-Matching-Implementierung")


def _process_strings(s1: str, s2: str) -> Tuple[str, str]:
    """Prepares Strings for the similarity comparison. Args: S1: First string S2: second string Return: Tuple with the normalized strings"""
    # Convert to small letters
    s1 = s1.lower()
    s2 = s2.lower()

    # Sonderzeichen entfernen
    s1 = re.sub(r'[^\w\s]', '', s1)
    s2 = re.sub(r'[^\w\s]', '', s2)

    # Mehrfache Leerzeichen entfernen
    s1 = re.sub(r'\s+', ' ', s1).strip()
    s2 = re.sub(r'\s+', ' ', s2).strip()

    return s1, s2


def fuzz_ratio(s1: str, s2: str) -> int:
    """Calculate the similarity between two strings (Levenshtein distance). Args: S1: First string S2: second string Return: Similarity value between 0 and 100"""
    if _USE_EXTERNAL_FUZZ:
        return fuzz.ratio(s1, s2)

    # Simple implementation with a Lack of External Library
    s1, s2 = _process_strings(s1, s2)
    if not s1 or not s2:
        return 0

    # Einfacher Jaccard-Index als Fallback
    set1 = set(s1)
    set2 = set(s2)

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return round((intersection / max(1, union)) * 100)


def fuzz_partial_ratio(s1: str, s2: str) -> int:
    """Calculate the best partial similarity between two strings. Args: S1: First string S2: second string Return: Similarity value between 0 and 100"""
    if _USE_EXTERNAL_FUZZ:
        return fuzz.partial_ratio(s1, s2)

    # Simple implementation for partial comparison
    s1, s2 = _process_strings(s1, s2)

    if not s1 or not s2:
        return 0

    # Use The Shorter String as a Reference
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    # Search for the best agreement area
    best_score = 0
    for i in range(len(s2) - len(s1) + 1):
        substring = s2[i:i+len(s1)]
        score = fuzz_ratio(s1, substring)
        best_score = max(best_score, score)

    return best_score


def fuzz_token_sort_ratio(s1: str, s2: str) -> int:
    """Sort the words in both strings and then compare the sorted strings. Args: S1: First string S2: second string Return: Similarity value between 0 and 100"""
    if _USE_EXTERNAL_FUZZ:
        return fuzz.token_sort_ratio(s1, s2)

    # Eigene Implementierung
    s1, s2 = _process_strings(s1, s2)

    # Sortiere Tokens
    sorted_s1 = ' '.join(sorted(s1.split()))
    sorted_s2 = ' '.join(sorted(s2.split()))

    return fuzz_ratio(sorted_s1, sorted_s2)


def fuzz_token_set_ratio(s1: str, s2: str) -> int:
    """Consider the strings as quantities of tokens and compares them. Args: S1: First string S2: second string Return: Similarity value between 0 and 100"""
    if _USE_EXTERNAL_FUZZ:
        return fuzz.token_set_ratio(s1, s2)

    # Eigene Implementierung
    s1, s2 = _process_strings(s1, s2)

    # Token-Mengen erstellen
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())

    # Gemeinsame Tokens
    intersection = tokens1.intersection(tokens2)

    # Union of the tokens
    union = tokens1.union(tokens2)

    if not union:
        return 0

    # Jaccard coefficient for quantities
    return round((len(intersection) / len(union)) * 100)


class ProcessMatch:
    """Class for extended string-like search."""

    @staticmethod
    def extract(query: str, choices: List[T], limit: int = 5,
               processor: Callable[[T], str] = str,
               scorer: Callable[[str, str], int] = fuzz_ratio,
               score_cutoff: int = 0) -> List[Tuple[T, int]]:
        """Extract the best matches from a list of options. ARGS: Query: The Search String Choices: List of Elements to Be Searched Limit: Maximum Number of Results Processor: Function to Convert the Elements Into Strings Scorer: Similarity Function Score_Cutoff: Minimal Similarity Value Return: List of (element, Similarity Value) Tuber"""
        if _USE_EXTERNAL_FUZZ:
            # Always use the compatible API version without score_cutoff
            results = process.extract(query, choices, limit=None,
                                     processor=processor, scorer=scorer)
            # Filter results manually and limit
            results = [(choice, score) for choice, score in results if score >= score_cutoff]
            results.sort(key=lambda x: x[1], reverse=True)

            # Return only the requested number of results
            return results[:limit] if limit else results

        # Eigene Implementierung
        results = []

        for choice in choices:
            choice_str = processor(choice)
            score = scorer(query, choice_str)

            if score >= score_cutoff:
                results.append((choice, score))

        # Sort according to similarity value (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    @staticmethod
    def extractOne(query: str, choices: List[T],
                  processor: Callable[[T], str] = str,
                  scorer: Callable[[str, str], int] = fuzz_ratio,
                  score_cutoff: int = 0) -> Optional[Tuple[T, int]]:
        """Extract the best match from a list of options. Args: query: The Search String Choices: List of Elements to Be Searched Processor: Function to Convert the Elements Into Strings Scorer: Similarity Function Score_Cutoff: Minimal Similarity Value Return: (Element, Similarity Value) Tupel or None"""
        if _USE_EXTERNAL_FUZZ:
            return process.extractOne(query, choices,
                                     processor=processor, scorer=scorer,
                                     score_cutoff=score_cutoff)

        results = ProcessMatch.extract(query, choices, limit=1,
                                     processor=processor, scorer=scorer,
                                     score_cutoff=score_cutoff)

        return results[0] if results else None
