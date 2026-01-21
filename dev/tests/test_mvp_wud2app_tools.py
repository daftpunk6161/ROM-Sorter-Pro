import os
import sys
import time
import threading
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.controller import CancelToken
from src.utils.external_tools import (
    PROBE_INPUT_PATH,
    probe_wud2app,
    probe_wudcompress,
    run_wud2app,
    run_wudcompress,
)

pytestmark = pytest.mark.integration


def _write_fake_wud2app(tmp_path: Path) -> str:
    tool_py = tmp_path / "wud2app_fake.py"
    tool_py.write_text(
        """#!/usr/bin/env python3
import os
import sys
import time

args = sys.argv[1:]
mode = "wud2app"

for arg in args:
    if arg.startswith("--mode="):
        mode = arg.split("=", 1)[1]

if mode == "wud2app":
    print("wud2app v1.1u3 by FIX94")

sleep_arg = None
marker = None
for arg in args:
    if arg.startswith("--sleep="):
        sleep_arg = float(arg.split("=", 1)[1])
    if arg.startswith("--marker="):
        marker = arg.split("=", 1)[1]

if sleep_arg:
    time.sleep(sleep_arg)

if marker:
    try:
        with open(marker, "w", encoding="utf-8") as f:
            f.write("ran")
    except Exception:
        pass

input_path = args[0] if args else ""
if input_path and not os.path.exists(input_path):
    if mode == "wudcompress":
        sys.stdout.write("Invalid input file\\n")
    else:
        sys.stdout.write(f"Failed to open {input_path}!\\n")
    sys.exit(1)

sys.exit(0)
""",
        encoding="utf-8",
    )

    if os.name == "nt":
        tool_cmd = tmp_path / "wud2app_fake.cmd"
        tool_cmd.write_text(
            f"@echo off\r\n\"{sys.executable}\" \"{tool_py}\" %*\r\n",
            encoding="utf-8",
        )
        return str(tool_cmd)

    tool_py.chmod(tool_py.stat().st_mode | 0o111)
    return str(tool_py)


def test_probe_wud2app_missing_config():
    result = probe_wud2app({"external_tools": {"wud2app": {}}})
    assert result.available is False
    assert result.probe_status == "missing"


def test_probe_wud2app_open_failure_parses_version(tmp_path):
    exe_path = _write_fake_wud2app(tmp_path)
    result = probe_wud2app({"external_tools": {"wud2app": {"exe_path": exe_path}}})
    assert result.available is True
    assert result.version == "1.1u3"
    assert result.probe_status == "open-failure"
    assert result.open_failure_path == PROBE_INPUT_PATH


def test_probe_wudcompress_invalid_input(tmp_path):
    exe_path = _write_fake_wud2app(tmp_path)
    config = {
        "external_tools": {
            "wudcompress": {
                "exe_path": exe_path,
                "args_template": ["{input}", "--mode=wudcompress"],
            }
        }
    }
    result = probe_wudcompress(config)
    assert result.available is True
    assert result.probe_status == "invalid-input"


def test_run_wud2app_dry_run_skips_execution(tmp_path):
    exe_path = _write_fake_wud2app(tmp_path)
    marker = tmp_path / "marker.txt"
    config = {
        "external_tools": {
            "wud2app": {
                "exe_path": exe_path,
                "args_template": ["{input}", "{output_dir}", "{temp_dir}", f"--marker={marker}"],
            }
        }
    }
    result = run_wud2app(
        input_path=str(tmp_path / "does_not_matter.wud"),
        output_dir=str(tmp_path / "out"),
        temp_dir=str(tmp_path / "tmp"),
        config=config,
        dry_run=True,
    )
    assert result.success is True
    assert result.message.startswith("dry-run")
    assert not marker.exists()


def test_run_wudcompress_missing_tool_is_clean_error():
    result = run_wudcompress(
        input_path="missing.wud",
        output_file="out.wux",
        output_dir="out",
        temp_dir="tmp",
        config={"external_tools": {"wudcompress": {}}},
        dry_run=False,
    )
    assert result.success is False
    assert "path not configured" in result.message.lower()


def test_run_wud2app_open_failure_message(tmp_path):
    exe_path = _write_fake_wud2app(tmp_path)
    config = {
        "external_tools": {
            "wud2app": {
                "exe_path": exe_path,
                "args_template": ["{input}", "{output_dir}", "{temp_dir}"],
            }
        }
    }
    result = run_wud2app(
        input_path=str(tmp_path / "missing.wud"),
        output_dir=str(tmp_path / "out"),
        temp_dir=str(tmp_path / "tmp"),
        config=config,
        dry_run=False,
    )
    assert result.success is False
    assert "Input missing or not accessible" in result.message


def test_run_wudcompress_dry_run_skips_execution(tmp_path):
    exe_path = _write_fake_wud2app(tmp_path)
    marker = tmp_path / "marker.txt"
    config = {
        "external_tools": {
            "wudcompress": {
                "exe_path": exe_path,
                "args_template": ["{input}", "{output_file}", "--mode=wudcompress", f"--marker={marker}"],
            }
        }
    }
    result = run_wudcompress(
        input_path=str(tmp_path / "missing.wud"),
        output_file=str(tmp_path / "out.wux"),
        output_dir=str(tmp_path / "out"),
        temp_dir=str(tmp_path / "tmp"),
        config=config,
        dry_run=True,
    )
    assert result.success is True
    assert result.message.startswith("dry-run")
    assert not marker.exists()


def test_run_wud2app_cancel_terminates_process(tmp_path):
    exe_path = _write_fake_wud2app(tmp_path)
    input_path = tmp_path / "present.wud"
    input_path.write_text("x", encoding="utf-8")

    config = {
        "external_tools": {
            "wud2app": {
                "exe_path": exe_path,
                "args_template": ["{input}", "{output_dir}", "{temp_dir}", "--sleep=5"],
            }
        }
    }

    token = CancelToken()
    result_holder = {}

    def _run():
        result_holder["result"] = run_wud2app(
            input_path=str(input_path),
            output_dir=str(tmp_path / "out"),
            temp_dir=str(tmp_path / "tmp"),
            config=config,
            cancel_token=token,
            dry_run=False,
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    time.sleep(0.1)
    token.cancel()
    thread.join(timeout=10)

    result = result_holder.get("result")
    assert result is not None
    assert result.cancelled is True
