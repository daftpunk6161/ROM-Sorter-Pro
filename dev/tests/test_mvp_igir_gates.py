import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import external_tools  # noqa: E402

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


def test_igir_plan_requires_dest_root_when_enforced(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    monkeypatch.setattr(external_tools, "_get_igir_yaml_config", lambda: config)

    result = external_tools.igir_plan(
        input_path=str(tmp_path / "input"),
        output_dir=str(tmp_path / "out"),
        dest_root=None,
        report_dir=str(tmp_path / "reports"),
        temp_dir=str(tmp_path / "temp"),
        dry_run=False,
    )

    assert result.ok is False
    assert "dest_root required" in result.message


def test_igir_execute_requires_dest_root_when_enforced(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    monkeypatch.setattr(external_tools, "_get_igir_yaml_config", lambda: config)

    result = external_tools.igir_execute(
        input_path=str(tmp_path / "input"),
        output_dir=str(tmp_path / "out"),
        dest_root=None,
        temp_dir=str(tmp_path / "temp"),
        plan_confirmed=True,
        explicit_user_action=True,
    )

    assert result.success is False
    assert "dest_root required" in result.message


def test_igir_execute_copy_first_stages_and_copies(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    config["copy_first"] = True
    monkeypatch.setattr(external_tools, "_get_igir_yaml_config", lambda: config)

    captured = {"output_dir": None}

    def _fake_run(*_args, **kwargs):
        args = kwargs.get("args") or []
        out_dir = None
        if "--output" in args:
            idx = args.index("--output") + 1
            if idx < len(args):
                out_dir = args[idx]
        captured["output_dir"] = out_dir
        if out_dir:
            stage = Path(out_dir)
            stage.mkdir(parents=True, exist_ok=True)
            (stage / "out.txt").write_text("ok", encoding="utf-8")
        return 0, "ok", "", False, False

    monkeypatch.setattr(external_tools, "_run_external_process", _fake_run)

    dest = tmp_path / "dest"
    dest.mkdir()
    temp_dir = tmp_path / "temp"

    result = external_tools.igir_execute(
        input_path=str(tmp_path / "input"),
        output_dir=str(dest),
        dest_root=str(tmp_path),
        temp_dir=str(temp_dir),
        plan_confirmed=True,
        explicit_user_action=True,
    )

    assert result.success is True
    assert captured["output_dir"] is not None
    assert str(temp_dir / "igir_copy_first") == captured["output_dir"]
    assert (dest / "out.txt").exists()


def test_igir_plan_uses_active_profile(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    config["profiles"] = {
        "ps2": {
            "plan": ["--profile", "ps2", "{input}"],
            "execute": ["{input}", "--profile", "ps2"],
        }
    }
    config["active_profile"] = "ps2"
    monkeypatch.setattr(external_tools, "_get_igir_yaml_config", lambda: config)

    captured = {"args": None}

    def _fake_run(*_args, **kwargs):
        captured["args"] = kwargs.get("args")
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
    assert captured["args"] is not None
    assert "--profile" in captured["args"]
    assert "ps2" in captured["args"]
