import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_optional_import_logging_emits_debug(caplog: pytest.LogCaptureFixture) -> None:
    from src.ui.mvp import tk_app

    caplog.set_level("DEBUG")

    # Force import failure by targeting a non-existent module.
    result = tk_app._import_symbol(("nonexistent_mod_xyz",), "MissingSymbol")

    assert result is None
    assert any("Optional import failed" in record.message for record in caplog.records)
