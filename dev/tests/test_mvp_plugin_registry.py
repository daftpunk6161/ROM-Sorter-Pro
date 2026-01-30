from __future__ import annotations

from pathlib import Path

import pytest

from src.plugins.registry import get_plugin_registry


@pytest.mark.integration
def test_plugin_registry_loads_detectors_and_converters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()

    plugin_file = plugin_dir / "sample_plugin.py"
    plugin_file.write_text(
        """
from __future__ import annotations

def register(registry):
    registry.register_detector('sample', lambda name, path: ('PluginSystem', 0.99), priority=1)
    registry.register_converter_rule({
        'converter_id': 'sample_converter',
        'input_kinds': ['RawRom'],
        'output_extension': '.bin',
        'exe_path': 'tool.exe',
        'args_template': ['{input}', '{output}']
    })
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("ROM_SORTER_PLUGIN_PATHS", str(plugin_dir))
    registry = get_plugin_registry(force_reload=True)

    assert registry.detectors
    assert registry.detectors[0].name == "sample"
    assert registry.converter_rules
    assert registry.converter_rules[0]["converter_id"] == "sample_converter"
