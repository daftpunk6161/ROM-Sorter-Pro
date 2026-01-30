from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from src.config.models import validate_config


def test_validate_config_minimal() -> None:
    payload = {
        "gui_settings": {"default_conflict_policy": "overwrite"},
        "scanner": {"use_high_performance": True, "max_threads": 2},
        "ui": {"theme": "system"},
    }
    model = validate_config(payload)
    assert model.gui_settings is not None
    assert model.gui_settings.default_conflict_policy == "overwrite"
    assert model.scanner is not None
    assert model.scanner.max_threads == 2
    assert model.ui is not None
    assert model.ui.theme == "system"
