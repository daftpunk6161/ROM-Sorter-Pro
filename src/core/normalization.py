"""Normalization helpers (config-driven, emulator-safe).

Classifies inputs and validates track sets/folder sets without performing writes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

from ..security.security_utils import InvalidPathError, validate_file_operation
from ..config.schema import JSONSCHEMA_AVAILABLE, validate_config_schema

InputKind = Literal[
    "RawRom",
    "ArchiveSet",
    "DiscImage",
    "DiscTrackSet",
    "GameFolderSet",
]


@dataclass(frozen=True)
class NormalizationIssue:
    code: str
    message: str


@dataclass(frozen=True)
class NormalizationItem:
    input_path: str
    input_kind: InputKind
    platform_id: Optional[str]
    status: str
    issues: Tuple[NormalizationIssue, ...]
    action: str
    output_path: Optional[str]
    converter_id: Optional[str] = None
    tool_path: Optional[str] = None
    args: Optional[List[str]] = None


@dataclass(frozen=True)
class NormalizationPlan:
    items: List[NormalizationItem]
    cancelled: bool = False


@dataclass(frozen=True)
class NormalizationReport:
    processed: int
    succeeded: int
    failed: int
    errors: List[str]
    cancelled: bool


def _platform_formats_path() -> Path:
    override = os.environ.get("ROM_SORTER_PLATFORM_FORMATS", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "platforms" / "platform_formats.yaml"


def _platform_formats_schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "platforms" / "platform_formats.schema.json"


def _converters_path() -> Path:
    override = os.environ.get("ROM_SORTER_CONVERTERS", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "conversion" / "converters.yaml"


def _converters_schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "conversion" / "converters.schema.json"


def _load_yaml_or_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except Exception:
        yaml = None
    if yaml is not None:
        try:
            data = yaml.safe_load(raw)
            return data if isinstance(data, dict) else None
        except Exception:
            return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _basic_validate_converters(data: Dict[str, Any]) -> bool:
    converters = data.get("converters")
    if not isinstance(converters, list):
        return False
    for entry in converters:
        if not isinstance(entry, dict):
            return False
        if not entry.get("converter_id"):
            return False
        if not entry.get("input_kinds") or not isinstance(entry.get("input_kinds"), list):
            return False
        if not entry.get("output_extension"):
            return False
        if not entry.get("exe_path"):
            return False
        args_template = entry.get("args_template")
        if args_template is None or not isinstance(args_template, list):
            return False
    return True


def _basic_validate_formats(data: Dict[str, Any]) -> bool:
    formats = data.get("formats")
    if not isinstance(formats, list):
        return False
    for entry in formats:
        if not isinstance(entry, dict):
            return False
        if not entry.get("platform_id"):
            return False
        input_kinds = entry.get("input_kinds")
        if input_kinds is not None and not isinstance(input_kinds, list):
            return False
    return True


def load_platform_formats() -> List[Dict[str, Any]]:
    data = _load_yaml_or_json(_platform_formats_path()) or {}
    if JSONSCHEMA_AVAILABLE:
        try:
            is_valid, error = validate_config_schema(data, schema_path=str(_platform_formats_schema_path()))
        except Exception:
            is_valid, error = False, "validation-error"
        if not is_valid:
            return []
    else:
        if not _basic_validate_formats(data):
            return []
    formats = data.get("formats")
    return list(formats) if isinstance(formats, list) else []


def load_converters() -> List[Dict[str, Any]]:
    data = _load_yaml_or_json(_converters_path()) or {}
    if JSONSCHEMA_AVAILABLE:
        try:
            is_valid, error = validate_config_schema(data, schema_path=str(_converters_schema_path()))
        except Exception:
            is_valid, error = False, "validation-error"
        if not is_valid:
            return []
    else:
        if not _basic_validate_converters(data):
            return []
    converters = data.get("converters")
    return list(converters) if isinstance(converters, list) else []


def classify_input(path: str) -> InputKind:
    p = Path(str(path or ""))
    if p.is_dir():
        return "GameFolderSet"

    name = p.name.lower()
    if name.endswith((".tar.gz", ".tar.bz2")):
        return "ArchiveSet"

    ext = p.suffix.lower()
    if ext in (".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"):
        return "ArchiveSet"
    if ext in (".cue", ".gdi"):
        return "DiscTrackSet"
    if ext in (".iso", ".bin", ".img", ".mdf", ".nrg", ".cdi", ".chd", ".gcz", ".rvz", ".wbfs"):
        return "DiscImage"
    return "RawRom"


def _parse_cue_files(cue_path: Path) -> List[str]:
    files: List[str] = []
    try:
        text = cue_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return files
    pattern = re.compile(r"^\s*FILE\s+\"(?P<name>[^\"]+)\"", re.IGNORECASE)
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            files.append(match.group("name").strip())
    return files


def _parse_gdi_files(gdi_path: Path) -> List[str]:
    files: List[str] = []
    try:
        text = gdi_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return files
    for line in text.splitlines()[1:]:
        parts = line.strip().split()
        if len(parts) >= 5:
            files.append(parts[-1])
    return files


def validate_trackset(path: str) -> List[str]:
    p = Path(path)
    if not p.exists():
        return [str(p)]
    if p.suffix.lower() == ".cue":
        files = _parse_cue_files(p)
    elif p.suffix.lower() == ".gdi":
        files = _parse_gdi_files(p)
    else:
        return []

    missing: List[str] = []
    for name in files:
        candidate = (p.parent / name).resolve()
        if not candidate.exists():
            missing.append(name)
    return missing


def validate_folderset(path: str, platform_id: Optional[str], formats: List[Dict[str, Any]]) -> List[str]:
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return [str(p)]

    if not platform_id:
        return []

    missing: List[str] = []
    for entry in formats:
        try:
            if str(entry.get("platform_id") or "").strip() != platform_id:
                continue
            input_kinds = entry.get("input_kinds") or []
            if "GameFolderSet" not in input_kinds:
                continue
            required = entry.get("required_manifests") or []
            for rel in required:
                rel_path = Path(str(rel))
                if rel_path.is_absolute():
                    continue
                candidate = (p / rel_path).resolve()
                if not candidate.exists():
                    missing.append(str(rel_path))
        except Exception:
            continue

    return missing


def _resolve_platform_id(raw: Optional[str], formats: List[Dict[str, Any]]) -> Optional[str]:
    if not raw:
        return None
    value = "-".join(str(raw).strip().lower().split())
    if not value:
        return None
    known = {str(entry.get("platform_id")) for entry in formats if entry.get("platform_id")}
    return value if value in known else None


def normalize_input(
    input_path: str,
    *,
    platform_hint: Optional[str] = None,
) -> NormalizationItem:
    formats = load_platform_formats()
    kind = classify_input(input_path)
    platform_id = _resolve_platform_id(platform_hint, formats)

    issues: List[NormalizationIssue] = []
    status = "ok"

    if kind == "DiscTrackSet":
        missing = validate_trackset(input_path)
        if missing:
            status = "failed"
            issues.append(
                NormalizationIssue(
                    code="missing-track-file",
                    message=f"Missing track files: {', '.join(missing)}",
                )
            )
    elif kind == "GameFolderSet":
        missing = validate_folderset(input_path, platform_id, formats)
        if missing:
            status = "failed"
            issues.append(
                NormalizationIssue(
                    code="missing-manifest",
                    message=f"Missing required files: {', '.join(missing)}",
                )
            )

    return NormalizationItem(
        input_path=str(input_path),
        input_kind=kind,
        platform_id=platform_id,
        status=status,
        issues=tuple(issues),
        action="none",
        output_path=None,
    )


def _match_converter(
    *,
    input_kind: InputKind,
    platform_id: Optional[str],
    input_path: str,
    converters: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    ext = Path(input_path).suffix.lower()
    for entry in converters:
        try:
            if not entry or not isinstance(entry, dict):
                continue
            if not bool(entry.get("enabled", True)):
                continue
            input_kinds = entry.get("input_kinds") or []
            if input_kind not in input_kinds:
                continue
            platforms = entry.get("platform_ids") or []
            if platforms and platform_id not in platforms:
                continue
            exts = entry.get("extensions") or []
            if exts:
                norm_exts = {str(e).lower() if str(e).startswith(".") else f".{str(e).lower()}" for e in exts}
                if ext not in norm_exts:
                    continue
            if not entry.get("output_extension"):
                continue
            if not entry.get("exe_path"):
                continue
            return entry
        except Exception:
            continue
    return None


def _build_converter_args(entry: Dict[str, Any], *, input_path: str, output_path: str, temp_dir: str) -> List[str]:
    template = entry.get("args_template") or []
    if isinstance(template, str):
        template = [template]
    args: List[str] = []
    for raw in template:
        value = str(raw)
        value = value.replace("{input}", str(input_path))
        value = value.replace("{output}", str(output_path))
        value = value.replace("{output_dir}", str(Path(output_path).parent))
        value = value.replace("{temp_dir}", str(temp_dir))
        if value:
            args.append(value)
    return args


def plan_normalization(
    inputs: Iterable[NormalizationItem],
    *,
    output_root: Optional[str] = None,
    temp_root: Optional[str] = None,
) -> NormalizationPlan:
    converters = load_converters()
    out_root = Path(output_root) if output_root else None
    tmp_root = Path(temp_root) if temp_root else None

    planned: List[NormalizationItem] = []

    for item in inputs:
        if item.status != "ok":
            planned.append(item)
            continue

        converter = _match_converter(
            input_kind=item.input_kind,
            platform_id=item.platform_id,
            input_path=item.input_path,
            converters=converters,
        )

        if not converter:
            planned.append(item)
            continue

        output_ext = str(converter.get("output_extension")).strip()
        output_ext = output_ext if output_ext.startswith(".") else f".{output_ext}"

        src_path = Path(item.input_path)
        target_root = out_root or src_path.parent
        output_path = str((target_root / src_path.stem).with_suffix(output_ext))
        temp_dir = str(tmp_root or (target_root / "_temp"))

        args = _build_converter_args(
            converter,
            input_path=str(src_path),
            output_path=output_path,
            temp_dir=temp_dir,
        )

        planned.append(
            NormalizationItem(
                input_path=item.input_path,
                input_kind=item.input_kind,
                platform_id=item.platform_id,
                status="planned",
                issues=item.issues,
                action="convert",
                output_path=output_path,
                converter_id=str(converter.get("converter_id") or "") or None,
                tool_path=str(converter.get("exe_path") or "") or None,
                args=args,
            )
        )

    return NormalizationPlan(items=planned, cancelled=False)


def execute_normalization(
    plan: NormalizationPlan,
    *,
    cancel_token: Optional[Any] = None,
    dry_run: bool = True,
) -> NormalizationReport:
    processed = 0
    succeeded = 0
    failed = 0
    errors: List[str] = []
    cancelled = False

    for item in plan.items:
        if cancel_token is not None and getattr(cancel_token, "is_cancelled", None):
            try:
                if cancel_token.is_cancelled():
                    cancelled = True
                    break
            except Exception:
                pass

        if item.status != "planned" or item.action != "convert":
            processed += 1
            succeeded += 1
            continue

        if dry_run:
            processed += 1
            succeeded += 1
            continue

        if not item.output_path or not item.args or not item.tool_path:
            processed += 1
            failed += 1
            errors.append(f"Invalid normalization action for {item.input_path}")
            continue

        try:
            src = Path(item.input_path).resolve()
            dst = Path(item.output_path).resolve()
            validate_file_operation(src, base_dir=None, allow_read=True, allow_write=True)
            validate_file_operation(dst, base_dir=dst.parent, allow_read=True, allow_write=True)
        except InvalidPathError as exc:
            processed += 1
            failed += 1
            errors.append(str(exc))
            continue

        exe_path = None
        try:
            exe_path = str(item.tool_path)
        except Exception:
            exe_path = None

        if not exe_path:
            processed += 1
            failed += 1
            errors.append(f"Missing tool for {item.input_path}")
            continue

        cmd = [exe_path] + list(item.args or [])
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            processed += 1
            failed += 1
            errors.append(f"Failed to start converter: {exc}")
            continue

        while proc.poll() is None:
            if cancel_token is not None and getattr(cancel_token, "is_cancelled", None):
                try:
                    if cancel_token.is_cancelled():
                        cancelled = True
                        proc.terminate()
                        break
                except Exception:
                    pass
            time.sleep(0.05)

        if cancelled:
            break

        if proc.returncode != 0:
            processed += 1
            failed += 1
            errors.append(f"Converter failed for {item.input_path}")
            continue

        if not Path(item.output_path).exists():
            processed += 1
            failed += 1
            errors.append(f"Output missing after conversion: {item.output_path}")
            continue

        processed += 1
        succeeded += 1

    return NormalizationReport(
        processed=processed,
        succeeded=succeeded,
        failed=failed,
        errors=errors,
        cancelled=cancelled,
    )
