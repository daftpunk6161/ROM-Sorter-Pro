"""ROM verification and audit module.

Features:
- F71: Bad-Dump Scanner ([b], [!], [o], [h] flags)
- F72: Intro/Trainer Detection ([t], [f], [a] flags)
- F73: Overdump Detection (size mismatch)
- F74: ROM Integrity Reports
"""

from .rom_verifier import (
    RomVerifier,
    VerificationResult,
    RomFlag,
    FlagType,
)
from .integrity_report import IntegrityReportGenerator, IntegrityReport

__all__ = [
    "RomVerifier",
    "VerificationResult",
    "RomFlag",
    "FlagType",
    "IntegrityReportGenerator",
    "IntegrityReport",
]
