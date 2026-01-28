"""External tools integration (config-driven)."""

from __future__ import annotations

import os
import csv
import json
import shutil
import re
import subprocess
import threading
import time
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path

from ..security.security_utils import validate_file_operation
from ..config import Config, load_config

logger = logging.getLogger(__name__)

PROBE_INPUT_PATH = r"C:\__romsorter_probe__\does_not_exist.wud"

WUD2APP_VERSION_RE = re.compile(r"^wud2app v(?P<ver>\S+)", re.MULTILINE)
WUD2APP_OPEN_FAIL_RE = re.compile(r"Failed to open (?P<path>.+)!", re.MULTILINE)
WUDCOMPRESS_INVALID_INPUT_RE = re.compile(r"Invalid input file", re.IGNORECASE)

LogCallback = Optional[Callable[[str], None]]
ConfigLike = Union[Config, Dict[str, Any]]


@dataclass(frozen=True)
class Wud2AppProbeResult:
    available: bool
    version: Optional[str]
    probe_status: str
    probe_message: str
    open_failure_path: Optional[str]
    raw_output: str
    exit_code: Optional[int]


@dataclass(frozen=True)
class Wud2AppRunResult:
    success: bool
    cancelled: bool
    message: str
    raw_output: str


@dataclass(frozen=True)
class WudCompressProbeResult:
    available: bool
    version: Optional[str]
    probe_status: str
    probe_message: str
    raw_output: str
    exit_code: Optional[int]


@dataclass(frozen=True)
class WudCompressRunResult:
    success: bool
    cancelled: bool
    message: str
    raw_output: str
    timed_out: bool = False


@dataclass(frozen=True)
class IgirProbeResult:
    available: bool
    version: Optional[str]
    probe_status: str
    probe_message: str
    raw_output: str


    exit_code: Optional[int]


@dataclass(frozen=True)
class IgirRunResult:
    success: bool
    cancelled: bool
    message: str
    raw_output: str
    timed_out: bool = False


@dataclass(frozen=True)
class IgirPlanResult:
    ok: bool
    cancelled: bool
    message: str
    stdout: str
    diff_csv: Optional[str] = None
    diff_json: Optional[str] = None


def _load_cfg(config: Optional[ConfigLike]) -> Config:
    if isinstance(config, Config):
        return config
    if isinstance(config, dict):
        return Config(config)
    try:
        data = load_config()
        if isinstance(data, Config):
            return data
        if isinstance(data, dict):
            return Config(data)
        return Config()
    except Exception:
        return Config()


def _resolve_igir_args_template(cfg: Dict[str, Any], mode: str) -> List[str]:
    profiles = cfg.get("profiles") or {}
    active_profile = str(cfg.get("active_profile") or "").strip()
    if active_profile and isinstance(profiles, dict):
        profile = profiles.get(active_profile)
        if isinstance(profile, dict):
            args = profile.get(mode)
            if isinstance(args, str):
                return [args]
            if isinstance(args, list):
                return [str(arg) for arg in args if str(arg).strip()]
    args_template = (cfg.get("args_templates") or {}).get(mode) or []
    if isinstance(args_template, str):
        return [args_template]
    if isinstance(args_template, list):
        return [str(arg) for arg in args_template if str(arg).strip()]
    return []


def _get_tool_config(config: Optional[ConfigLike], tool_key: str) -> Tuple[str, List[str]]:
    cfg = _load_cfg(config)
    tools_cfg = cfg.get("external_tools", {}) or {}
    tool_cfg = tools_cfg.get(tool_key, {}) or {}
    exe_path = str(tool_cfg.get("exe_path") or "").strip()
    args_template = tool_cfg.get("args_template") or []
    if isinstance(args_template, str):
        args_template = [args_template]
    args_template = [str(arg) for arg in args_template if str(arg).strip()]
    return exe_path, args_template


def _get_wud2app_config(config: Optional[ConfigLike]) -> Tuple[str, List[str]]:
    return _get_tool_config(config, "wud2app")


def _get_wudcompress_config(config: Optional[ConfigLike]) -> Tuple[str, List[str]]:
    return _get_tool_config(config, "wudcompress")


def _get_igir_config(config: Optional[ConfigLike]) -> Tuple[str, List[str]]:
    return _get_tool_config(config, "igir")


def _load_igir_yaml() -> Dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "tools" / "igir.yaml"
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except Exception:
        yaml = None
    if yaml is not None:
        try:
            data = yaml.safe_load(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _get_igir_yaml_config() -> Dict[str, Any]:
    return _load_igir_yaml()


def _format_args(
    template: List[str],
    *,
    input_path: str,
    output_file: str,
    output_dir: str,
    temp_dir: str,
) -> List[str]:
    args: List[str] = []
    for raw in template:
        value = str(raw)
        value = value.replace("{input}", str(input_path))
        value = value.replace("{output_file}", str(output_file))
        value = value.replace("{output_dir}", str(output_dir))
        value = value.replace("{temp_dir}", str(temp_dir))
        if value:
            args.append(value)
    return args


def _quote_arg(value: str) -> str:
    if not value:
        return '""'
    if any(ch in value for ch in (" ", "\t", "\"")):
        return '"' + value.replace('"', '\\"') + '"'
    return value


def _prepare_command(exe_path: str, args: List[str]) -> Tuple[Union[str, List[str]], bool]:
    use_shell = False
    if os.name == "nt" and exe_path.lower().endswith((".cmd", ".bat")):
        use_shell = True
        cmd = " ".join([_quote_arg(exe_path)] + [_quote_arg(arg) for arg in args])

        return cmd, use_shell
    return [exe_path] + list(args), use_shell


def _stringify_command(cmd: Union[str, List[str]]) -> str:
    if isinstance(cmd, str):
        return cmd
    if isinstance(cmd, (list, tuple)):
        return " ".join(_quote_arg(str(part)) for part in cmd)
    return str(cmd)


def _validate_args_template(args_template: List[str], tool_label: str) -> Optional[str]:
    if not args_template:
        return f"{tool_label} args_template not configured"
    if not any("{input}" in str(raw) for raw in args_template):
        return f"{tool_label} args_template missing {{input}}"
    return None


def probe_igir(config: Optional[ConfigLike] = None) -> IgirProbeResult:
    yaml_cfg = _get_igir_yaml_config()
    exe_path = str(yaml_cfg.get("exe_path") or "").strip()
    if not exe_path:
        exe_path, _ = _get_igir_config(config)
    if not exe_path:
        return IgirProbeResult(
            available=False,
            version=None,
            probe_status="not-configured",
            probe_message="igir path not configured",
            raw_output="",
            exit_code=None,
        )
    if not os.path.exists(exe_path):
        return IgirProbeResult(
            available=False,
            version=None,
            probe_status="missing",
            probe_message="igir executable not found",
            raw_output="",
            exit_code=None,
        )

    try:
        exit_code, stdout, stderr, _cancelled, _timed_out = _run_external_process(
            exe_path=exe_path,
            args=["--version"],
            log_cb=None,
            cancel_token=None,
            timeout_sec=5,
            tool_label="igir",
        )
        combined = (stdout or "") + (stderr or "")
        version = None
        for line in (combined or "").splitlines():
            if "igir" in line.lower() and any(ch.isdigit() for ch in line):
                version = line.strip()
                break
        status = "ok" if exit_code == 0 else "error"
        message = "probe ok" if status == "ok" else "probe failed"
        return IgirProbeResult(
            available=True,
            version=version,
            probe_status=status,
            probe_message=message,
            raw_output=combined,
            exit_code=exit_code,
        )
    except Exception as exc:
        return IgirProbeResult(
            available=True,
            version=None,
            probe_status="error",
            probe_message=f"probe failed: {exc}",
            raw_output="",
            exit_code=None,
        )


def _terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return
        except Exception:
            logger.exception("External tools: taskkill failed")
    try:
        process.terminate()
    except Exception:
        logger.exception("External tools: terminate failed")
    try:
        process.wait(timeout=2)
        return
    except Exception:
        logger.exception("External tools: wait after terminate failed")
    try:
        process.kill()
    except Exception:
        logger.exception("External tools: kill failed")


def _run_external_process(
    *,
    exe_path: str,
    args: List[str],
    log_cb: LogCallback,
    cancel_token: Optional[Any],
    timeout_sec: Optional[float],
    tool_label: str,
) -> Tuple[int, str, str, bool, bool]:
    cmd, use_shell = _prepare_command(exe_path, args)
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=use_shell,
        creationflags=creationflags,
    )

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    def _reader(stream, sink, prefix: str) -> None:
        try:
            for line in iter(stream.readline, ""):
                if not line:
                    break
                sink.append(line)
                if log_cb is not None:
                    log_cb(f"{tool_label}{prefix}{line.rstrip()}".rstrip())
        finally:
            try:
                stream.close()
            except Exception:
                logger.exception("External tools: stream close failed")

    threads: List[threading.Thread] = []
    if process.stdout is not None:
        t = threading.Thread(target=_reader, args=(process.stdout, stdout_lines, ": "), daemon=True)
        threads.append(t)
        t.start()
    if process.stderr is not None:
        t = threading.Thread(target=_reader, args=(process.stderr, stderr_lines, " [err]: "), daemon=True)
        threads.append(t)
        t.start()

    start = time.monotonic()
    cancelled = False
    timed_out = False

    while True:
        if cancel_token is not None and getattr(cancel_token, "is_cancelled", None):
            try:
                if cancel_token.is_cancelled():
                    cancelled = True
                    _terminate_process_tree(process)
                    break
            except Exception:
                logger.exception("External tools: cancel check failed")

        if timeout_sec is not None and timeout_sec > 0:
            if (time.monotonic() - start) >= timeout_sec:
                timed_out = True
                _terminate_process_tree(process)
                break

        code = process.poll()
        if code is not None:
            break
        time.sleep(0.05)

    try:
        process.wait(timeout=2)
    except Exception:
        _terminate_process_tree(process)

    for t in threads:
        t.join(timeout=2)

    exit_code = process.returncode if process.returncode is not None else -1
    return exit_code, "".join(stdout_lines), "".join(stderr_lines), cancelled, timed_out


def _capture_process_output(
    process: subprocess.Popen,
    log_cb: LogCallback,
) -> Tuple[str, str]:
    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    def _reader(stream, sink, prefix: str) -> None:
        try:
            for line in iter(stream.readline, ""):
                if not line:
                    break
                sink.append(line)
                if log_cb is not None:
                    log_cb(f"wud2app{prefix}{line.rstrip()}".rstrip())
        finally:
            try:
                stream.close()
            except Exception:
                logger.exception("External tools: stream close failed")

    threads: List[threading.Thread] = []
    if process.stdout is not None:
        t = threading.Thread(target=_reader, args=(process.stdout, stdout_lines, ": "), daemon=True)
        threads.append(t)
        t.start()
    if process.stderr is not None:
        t = threading.Thread(target=_reader, args=(process.stderr, stderr_lines, " [err]: "), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return "".join(stdout_lines), "".join(stderr_lines)


def probe_wud2app(config: Optional[ConfigLike] = None) -> Wud2AppProbeResult:
    exe_path, _ = _get_wud2app_config(config)
    if not exe_path:
        return Wud2AppProbeResult(
            available=False,
            version=None,
            probe_status="missing",
            probe_message="wud2app path not configured",
            open_failure_path=None,
            raw_output="",
            exit_code=None,
        )

    if not os.path.exists(exe_path):
        return Wud2AppProbeResult(
            available=False,
            version=None,
            probe_status="missing",
            probe_message="wud2app executable not found",
            open_failure_path=None,
            raw_output="",
            exit_code=None,
        )

    cmd, use_shell = _prepare_command(exe_path, [PROBE_INPUT_PATH])

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=use_shell,
        )
        stdout, stderr = _capture_process_output(process, None)
        exit_code = process.returncode
    except Exception as exc:
        return Wud2AppProbeResult(
            available=False,
            version=None,
            probe_status="error",
            probe_message=f"probe failed: {exc}",
            open_failure_path=None,
            raw_output="",
            exit_code=None,
        )

    combined = (stdout or "") + (stderr or "")
    version = None
    open_failure_path = None

    vm = WUD2APP_VERSION_RE.search(combined)
    if vm:
        version = vm.group("ver")

    fm = WUD2APP_OPEN_FAIL_RE.search(combined)
    if fm:
        open_failure_path = fm.group("path")
        return Wud2AppProbeResult(
            available=True,
            version=version,
            probe_status="open-failure",
            probe_message=f"Failed to open {open_failure_path}!",
            open_failure_path=open_failure_path,
            raw_output=combined,
            exit_code=exit_code,
        )

    status = "ok" if exit_code == 0 else "error"
    message = "probe ok" if status == "ok" else "probe failed"

    return Wud2AppProbeResult(
        available=True,
        version=version,
        probe_status=status,
        probe_message=message,
        open_failure_path=None,
        raw_output=combined,
        exit_code=exit_code,
    )


def probe_wudcompress(config: Optional[ConfigLike] = None) -> WudCompressProbeResult:
    exe_path, args_template = _get_wudcompress_config(config)
    if not exe_path:
        return WudCompressProbeResult(
            available=False,
            version=None,
            probe_status="missing",
            probe_message="wudcompress path not configured",
            raw_output="",
            exit_code=None,
        )

    if not os.path.exists(exe_path):
        return WudCompressProbeResult(
            available=False,
            version=None,
            probe_status="missing",
            probe_message="wudcompress executable not found",
            raw_output="",
            exit_code=None,
        )

    args = _format_args(
        args_template,
        input_path=PROBE_INPUT_PATH,
        output_file=os.path.join(os.path.dirname(PROBE_INPUT_PATH), "probe.wux"),
        output_dir=os.path.dirname(PROBE_INPUT_PATH),
        temp_dir=os.path.join(os.path.dirname(PROBE_INPUT_PATH), "_temp"),
    )
    if not args:
        args = [PROBE_INPUT_PATH]
    elif not any("{input}" in str(raw) for raw in args_template):
        args.append(PROBE_INPUT_PATH)
    cmd, use_shell = _prepare_command(exe_path, args)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=use_shell,
        )
        stdout, stderr = _capture_process_output(process, None)
        exit_code = process.returncode
    except Exception as exc:
        return WudCompressProbeResult(
            available=False,
            version=None,
            probe_status="error",
            probe_message=f"probe failed: {exc}",
            raw_output="",
            exit_code=None,
        )

    combined = (stdout or "") + (stderr or "")

    if WUDCOMPRESS_INVALID_INPUT_RE.search(combined):
        return WudCompressProbeResult(
            available=True,
            version=None,
            probe_status="invalid-input",
            probe_message="Invalid input file",
            raw_output=combined,
            exit_code=exit_code,
        )

    status = "ok" if exit_code == 0 else "error"
    message = "probe ok" if status == "ok" else "probe failed"

    return WudCompressProbeResult(
        available=True,
        version=None,
        probe_status=status,
        probe_message=message,
        raw_output=combined,
        exit_code=exit_code,
    )


def run_wud2app(
    *,
    input_path: str,
    output_dir: str,
    temp_dir: str,
    config: Optional[ConfigLike] = None,
    log_cb: LogCallback = None,
    cancel_token: Optional[Any] = None,
    dry_run: bool = False,
    timeout_sec: Optional[float] = None,
) -> Wud2AppRunResult:
    if dry_run:
        return Wud2AppRunResult(True, False, "dry-run (no external tool executed)", "")

    exe_path, args_template = _get_wud2app_config(config)
    if not exe_path:
        return Wud2AppRunResult(False, False, "wud2app path not configured", "")
    if not os.path.exists(exe_path):
        return Wud2AppRunResult(False, False, "wud2app executable not found", "")

    template_error = _validate_args_template(args_template, "wud2app")
    if template_error:
        return Wud2AppRunResult(False, False, template_error, "")

    args = _format_args(
        args_template,
        input_path=input_path,
        output_file="",
        output_dir=output_dir,
        temp_dir=temp_dir,
    )

    try:
        exit_code, stdout, stderr, cancelled, timed_out = _run_external_process(
            exe_path=exe_path,
            args=args,
            log_cb=log_cb,
            cancel_token=cancel_token,
            timeout_sec=timeout_sec,
            tool_label="wud2app",
        )
    except Exception as exc:
        return Wud2AppRunResult(False, False, f"Failed to start wud2app: {exc}", "")

    combined = (stdout or "") + (stderr or "")

    if cancelled:
        return Wud2AppRunResult(False, True, "cancelled", combined)
    if timed_out:
        return Wud2AppRunResult(False, False, "timeout", combined)

    fm = WUD2APP_OPEN_FAIL_RE.search(combined)
    if fm:
        path = fm.group("path")
        return Wud2AppRunResult(False, False, f"Input missing or not accessible: {path}", combined)

    if exit_code == 0:
        return Wud2AppRunResult(True, False, "ok", combined)

    return Wud2AppRunResult(False, False, "wud2app failed", combined)


def run_wudcompress(
    *,
    input_path: str,
    output_file: str,
    output_dir: str,
    temp_dir: str,
    config: Optional[ConfigLike] = None,
    log_cb: LogCallback = None,
    cancel_token: Optional[Any] = None,
    dry_run: bool = False,
    timeout_sec: Optional[float] = None,
) -> WudCompressRunResult:
    if dry_run:
        return WudCompressRunResult(True, False, "dry-run (no external tool executed)", "")

    exe_path, args_template = _get_wudcompress_config(config)
    if not exe_path:
        return WudCompressRunResult(False, False, "wudcompress path not configured", "")
    if not os.path.exists(exe_path):
        return WudCompressRunResult(False, False, "wudcompress executable not found", "")

    template_error = _validate_args_template(args_template, "wudcompress")
    if template_error:
        return WudCompressRunResult(False, False, template_error, "")

    args = _format_args(
        args_template,
        input_path=input_path,
        output_file=output_file,
        output_dir=output_dir,
        temp_dir=temp_dir,
    )

    try:
        exit_code, stdout, stderr, cancelled, timed_out = _run_external_process(
            exe_path=exe_path,
            args=args,
            log_cb=log_cb,
            cancel_token=cancel_token,
            timeout_sec=timeout_sec,
            tool_label="wudcompress",
        )
    except Exception as exc:
        return WudCompressRunResult(False, False, f"Failed to start wudcompress: {exc}", "")

    combined = (stdout or "") + (stderr or "")

    if cancelled:
        return WudCompressRunResult(False, True, "cancelled", combined)
    if timed_out:
        return WudCompressRunResult(False, False, "timeout", combined, timed_out=True)

    if WUDCOMPRESS_INVALID_INPUT_RE.search(combined):
        return WudCompressRunResult(False, False, "Invalid input file", combined)

    if exit_code == 0:
        return WudCompressRunResult(True, False, "ok", combined)

    return WudCompressRunResult(False, False, "wudcompress failed", combined)


def run_igir(
    *,
    input_path: str,
    output_dir: str,
    temp_dir: str,
    config: Optional[ConfigLike] = None,
    log_cb: LogCallback = None,
    cancel_token: Optional[Any] = None,
    dry_run: bool = False,
    timeout_sec: Optional[float] = None,
) -> IgirRunResult:
    if dry_run:
        return IgirRunResult(True, False, "dry-run (no external tool executed)", "")

    exe_path, args_template = _get_igir_config(config)
    if not exe_path:
        return IgirRunResult(False, False, "igir path not configured", "")
    if not os.path.exists(exe_path):
        return IgirRunResult(False, False, "igir executable not found", "")

    template_error = _validate_args_template(args_template, "igir")
    if template_error:
        return IgirRunResult(False, False, template_error, "")

    args = _format_args(
        args_template,
        input_path=input_path,
        output_file="",
        output_dir=output_dir,
        temp_dir=temp_dir,
    )

    try:
        exit_code, stdout, stderr, cancelled, timed_out = _run_external_process(
            exe_path=exe_path,
            args=args,
            log_cb=log_cb,
            cancel_token=cancel_token,
            timeout_sec=timeout_sec,
            tool_label="igir",
        )
    except Exception as exc:
        return IgirRunResult(False, False, f"Failed to start igir: {exc}", "")

    combined = (stdout or "") + (stderr or "")

    if cancelled:
        return IgirRunResult(False, True, "cancelled", combined)
    if timed_out:
        return IgirRunResult(False, False, "timeout", combined, timed_out=True)

    if exit_code == 0:
        return IgirRunResult(True, False, "ok", combined)

    return IgirRunResult(False, False, "igir failed", combined)


def _write_igir_diff_reports(report_dir: str, stdout: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        os.makedirs(report_dir, exist_ok=True)
    except Exception:
        return None, None

    rows: List[Dict[str, str]] = []
    for line in (stdout or "").splitlines():
        if "->" in line or "=>" in line:
            parts = line.replace("=>", "->").split("->")
            if len(parts) >= 2:
                rows.append(
                    {
                        "op": "unknown",
                        "src": parts[0].strip(),
                        "dst": parts[1].strip(),
                        "collision": "",
                        "policy_action": "",
                        "notes": "parsed-from-stdout",
                    }
                )

    csv_path = os.path.join(report_dir, "igir_safety_diff.csv")
    json_path = os.path.join(report_dir, "igir_safety_diff.json")

    try:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["op", "src", "dst", "collision", "policy_action", "notes"])
            for row in rows:
                writer.writerow([
                    row.get("op"),
                    row.get("src"),
                    row.get("dst"),
                    row.get("collision"),
                    row.get("policy_action"),
                    row.get("notes"),
                ])
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"rows": rows}, f, indent=2)
        return csv_path, json_path
    except Exception:
        return None, None


def igir_plan(
    *,
    input_path: str,
    output_dir: str,
    dest_root: Optional[str] = None,
    report_dir: str,
    temp_dir: str,
    log_cb: LogCallback = None,
    cancel_token: Optional[Any] = None,
    dry_run: bool = False,
    timeout_sec: Optional[float] = None,
) -> IgirPlanResult:
    cfg = _get_igir_yaml_config()
    if dry_run and cfg.get("dry_run_never_runs_igir", True):
        return IgirPlanResult(True, False, "dry-run (no external tool executed)", "")

    exe_path = str(cfg.get("exe_path") or "").strip()
    args_template = _resolve_igir_args_template(cfg, "plan")
    if not exe_path:
        return IgirPlanResult(False, False, "igir path not configured", "")
    if not os.path.exists(exe_path):
        return IgirPlanResult(False, False, "igir executable not found", "")

    if cfg.get("enforce_dest_root", True):
        if not dest_root:
            return IgirPlanResult(False, False, "dest_root required", "")
        validate_file_operation(output_dir, base_dir=dest_root, allow_read=True, allow_write=True)

    try:
        os.makedirs(report_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
    except Exception as exc:
        return IgirPlanResult(False, False, f"failed to prepare directories: {exc}", "")

    template_error = _validate_args_template(args_template, "igir")
    if template_error:
        return IgirPlanResult(False, False, template_error, "")

    args = _format_args(
        args_template,
        input_path=input_path,
        output_file="",
        output_dir=output_dir,
        temp_dir=temp_dir,
    )
    args = [arg.replace("{report_dir}", report_dir) for arg in args]

    try:
        exit_code, stdout, stderr, cancelled, timed_out = _run_external_process(
            exe_path=exe_path,
            args=args,
            log_cb=log_cb,
            cancel_token=cancel_token,
            timeout_sec=timeout_sec,
            tool_label="igir-plan",
        )
    except Exception as exc:
        return IgirPlanResult(False, False, f"Failed to start igir: {exc}", "")

    combined = (stdout or "") + (stderr or "")
    if cancelled:
        return IgirPlanResult(False, True, "cancelled", combined)
    if timed_out:
        return IgirPlanResult(False, False, "timeout", combined)

    diff_csv, diff_json = _write_igir_diff_reports(report_dir, combined)
    if exit_code == 0:
        return IgirPlanResult(True, False, "ok", combined, diff_csv=diff_csv, diff_json=diff_json)

    return IgirPlanResult(False, False, "igir plan failed", combined, diff_csv=diff_csv, diff_json=diff_json)


def igir_execute(
    *,
    input_path: str,
    output_dir: str,
    dest_root: Optional[str] = None,
    temp_dir: str,
    log_cb: LogCallback = None,
    cancel_token: Optional[Any] = None,
    plan_confirmed: bool = False,
    explicit_user_action: bool = False,
    copy_first: Optional[bool] = None,
    timeout_sec: Optional[float] = None,
) -> IgirRunResult:
    cfg = _get_igir_yaml_config()
    if cfg.get("require_plan_before_execute", True) and not plan_confirmed:
        return IgirRunResult(False, False, "plan required before execute", "")
    if cfg.get("execute_requires_explicit_user_action", True) and not explicit_user_action:
        return IgirRunResult(False, False, "explicit user action required", "")
    exe_path = str(cfg.get("exe_path") or "").strip()
    args_template = _resolve_igir_args_template(cfg, "execute")
    if not exe_path:
        return IgirRunResult(False, False, "igir path not configured", "")
    if not os.path.exists(exe_path):
        return IgirRunResult(False, False, "igir executable not found", "")

    if cfg.get("enforce_dest_root", True):
        if not dest_root:
            return IgirRunResult(False, False, "dest_root required", "")
        validate_file_operation(output_dir, base_dir=dest_root, allow_read=True, allow_write=True)

    try:
        os.makedirs(temp_dir, exist_ok=True)
    except Exception as exc:
        return IgirRunResult(False, False, f"failed to prepare temp dir: {exc}", "")

    copy_first_enabled = bool(copy_first) if copy_first is not None else bool(cfg.get("copy_first", False))
    stage_dir: Optional[str] = None
    effective_output_dir = output_dir
    if copy_first_enabled:
        stage_dir = os.path.join(temp_dir, "igir_copy_first")
        try:
            os.makedirs(stage_dir, exist_ok=True)
        except Exception as exc:
            return IgirRunResult(False, False, f"failed to prepare staging dir: {exc}", "")
        effective_output_dir = stage_dir

    template_error = _validate_args_template(args_template, "igir")
    if template_error:
        return IgirRunResult(False, False, template_error, "")

    args = _format_args(
        args_template,
        input_path=input_path,
        output_file="",
        output_dir=effective_output_dir,
        temp_dir=temp_dir,
    )

    try:
        exit_code, stdout, stderr, cancelled, timed_out = _run_external_process(
            exe_path=exe_path,
            args=args,
            log_cb=log_cb,
            cancel_token=cancel_token,
            timeout_sec=timeout_sec,
            tool_label="igir-execute",
        )
    except Exception as exc:
        return IgirRunResult(False, False, f"Failed to start igir: {exc}", "")

    combined = (stdout or "") + (stderr or "")

    if cancelled:
        return IgirRunResult(False, True, "cancelled", combined)
    if timed_out:
        return IgirRunResult(False, False, "timeout", combined, timed_out=True)

    if exit_code == 0:
        if copy_first_enabled and stage_dir:
            try:
                if not os.path.exists(stage_dir):
                    return IgirRunResult(False, False, "copy-first staging missing", combined)
                shutil.copytree(stage_dir, output_dir, dirs_exist_ok=True)
            except Exception as exc:
                return IgirRunResult(False, False, f"copy-first failed: {exc}", combined)
        return IgirRunResult(True, False, "ok", combined)

    return IgirRunResult(False, False, "igir failed", combined)


def build_external_command(
    *,
    tool_key: str,
    input_path: str,
    output_file: str,
    output_dir: str,
    temp_dir: str,
    config: Optional[ConfigLike] = None,
) -> Tuple[Optional[str], Optional[str]]:
    exe_path, args_template = _get_tool_config(config, tool_key)
    if not exe_path:
        return None, f"{tool_key} path not configured"
    if not os.path.exists(exe_path):
        return None, f"{tool_key} executable not found"

    template_error = _validate_args_template(args_template, tool_key)
    if template_error:
        return None, template_error

    args = _format_args(
        args_template,
        input_path=input_path,
        output_file=output_file,
        output_dir=output_dir,
        temp_dir=temp_dir,
    )
    cmd, _ = _prepare_command(exe_path, args)
    return _stringify_command(cmd), None
