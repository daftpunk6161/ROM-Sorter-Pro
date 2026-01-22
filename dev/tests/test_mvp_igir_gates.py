import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import external_tools

pytestmark = pytest.mark.integration


def _make_config(tmp_path: Path, *, dry_run_never_runs: bool = True) -> dict:
    exe_path = tmp_path / "igir_fake.cmd"
    exe_path.write_text("@echo off\r\n", encoding="utf-8")
    return {
        "exe_path": str(exe_path),
        "args_templates": {
            "plan": ["{input}", "--report", "{report_dir}", "--output", "{output_dir}"],
            "execute": ["{input}", "--output", "{output_dir}"],
        },
        "dry_run_never_runs_igir": dry_run_never_runs,
        "require_plan_before_execute": True,
        "execute_requires_explicit_user_action": True,
        "enforce_dest_root": True,
    }


def test_igir_plan_dry_run_skips_external(monkeypatch, tmp_path):
    config = _make_config(tmp_path, dry_run_never_runs=True)
    monkeypatch.setattr(external_tools, "_get_igir_yaml_config", lambda: config)

    called = {"value": False}

    def _fake_run(*_args, **_kwargs):
        called["value"] = True
        return 0, "", "", False, False

    monkeypatch.setattr(external_tools, "_run_external_process", _fake_run)

    result = external_tools.igir_plan(
        input_path=str(tmp_path / "input"),
        output_dir=str(tmp_path / "out"),
        dest_root=str(tmp_path),
        report_dir=str(tmp_path / "reports"),
        temp_dir=str(tmp_path / "temp"),
        dry_run=True,
    )

    assert result.ok is True
    assert "dry-run" in result.message
    assert called["value"] is False


def test_igir_plan_runs_when_not_dry_run(monkeypatch, tmp_path):
    config = _make_config(tmp_path, dry_run_never_runs=True)
    monkeypatch.setattr(external_tools, "_get_igir_yaml_config", lambda: config)

    called = {"value": False}

    def _fake_run(*_args, **_kwargs):
        called["value"] = True
        return 0, "ok", "", False, False

    monkeypatch.setattr(external_tools, "_run_external_process", _fake_run)

    result = external_tools.igir_plan(
        input_path=str(tmp_path / "input"),
        output_dir=str(tmp_path / "out"),
        dest_root=str(tmp_path),
        report_dir=str(tmp_path / "reports"),
        temp_dir=str(tmp_path / "temp"),
        dry_run=False,
    )

    assert result.ok is True
    assert called["value"] is True


def test_igir_execute_requires_plan(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    monkeypatch.setattr(external_tools, "_get_igir_yaml_config", lambda: config)

    result = external_tools.igir_execute(
        input_path=str(tmp_path / "input"),
        output_dir=str(tmp_path / "out"),
        dest_root=str(tmp_path),
        temp_dir=str(tmp_path / "temp"),
        plan_confirmed=False,
        explicit_user_action=True,
    )

    assert result.success is False
    assert "plan required" in result.message


def test_igir_execute_requires_explicit_action(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    monkeypatch.setattr(external_tools, "_get_igir_yaml_config", lambda: config)

    result = external_tools.igir_execute(
        input_path=str(tmp_path / "input"),
        output_dir=str(tmp_path / "out"),
        dest_root=str(tmp_path),
        temp_dir=str(tmp_path / "temp"),
        plan_confirmed=True,
        explicit_user_action=False,
    )

    assert result.success is False
    assert "explicit user action" in result.message
