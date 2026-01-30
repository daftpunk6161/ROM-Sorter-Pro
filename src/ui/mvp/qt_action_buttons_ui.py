from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..i18n import translate


@dataclass(frozen=True)
class ActionButtonsUI:
    btn_scan: Any
    btn_preview: Any
    btn_execute: Any
    btn_resume: Any
    btn_retry_failed: Any
    btn_cancel: Any
    btn_execute_convert: Any
    btn_audit: Any
    btn_export_scan_csv: Any
    btn_export_scan_json: Any
    btn_export_plan_csv: Any
    btn_export_plan_json: Any
    btn_export_audit_csv: Any
    btn_export_audit_json: Any
    btn_export_frontend_es: Any
    btn_export_frontend_launchbox: Any


def build_action_buttons_ui(QtWidgets, label_func: Callable[[str, str], str]) -> ActionButtonsUI:
    btn_scan = QtWidgets.QPushButton(label_func(translate("scan"), "scan"))
    btn_preview = QtWidgets.QPushButton(label_func(translate("preview"), "preview"))
    btn_execute = QtWidgets.QPushButton(label_func(translate("execute"), "execute"))
    btn_resume = QtWidgets.QPushButton(translate("resume"))
    btn_retry_failed = QtWidgets.QPushButton(translate("retry_failed"))
    btn_cancel = QtWidgets.QPushButton(label_func(translate("cancel"), "cancel"))

    btn_execute_convert = QtWidgets.QPushButton(translate("convert_execute"))
    btn_audit = QtWidgets.QPushButton(translate("convert_audit"))

    btn_export_scan_csv = QtWidgets.QPushButton("Scan CSV")
    btn_export_scan_json = QtWidgets.QPushButton("Scan JSON")
    btn_export_plan_csv = QtWidgets.QPushButton("Plan CSV")
    btn_export_plan_json = QtWidgets.QPushButton("Plan JSON")
    btn_export_audit_csv = QtWidgets.QPushButton("Audit CSV")
    btn_export_audit_json = QtWidgets.QPushButton("Audit JSON")
    btn_export_frontend_es = QtWidgets.QPushButton("Frontend EmulationStation")
    btn_export_frontend_launchbox = QtWidgets.QPushButton("Frontend LaunchBox")

    return ActionButtonsUI(
        btn_scan=btn_scan,
        btn_preview=btn_preview,
        btn_execute=btn_execute,
        btn_resume=btn_resume,
        btn_retry_failed=btn_retry_failed,
        btn_cancel=btn_cancel,
        btn_execute_convert=btn_execute_convert,
        btn_audit=btn_audit,
        btn_export_scan_csv=btn_export_scan_csv,
        btn_export_scan_json=btn_export_scan_json,
        btn_export_plan_csv=btn_export_plan_csv,
        btn_export_plan_json=btn_export_plan_json,
        btn_export_audit_csv=btn_export_audit_csv,
        btn_export_audit_json=btn_export_audit_json,
        btn_export_frontend_es=btn_export_frontend_es,
        btn_export_frontend_launchbox=btn_export_frontend_launchbox,
    )


def configure_action_buttons_ui(action_buttons: ActionButtonsUI, button_row: Any) -> None:
    action_buttons.btn_execute_convert.setToolTip("Führt Sortierung inkl. Konvertierung aus")
    action_buttons.btn_audit.setToolTip("Prüft Konvertierungen ohne Änderungen")
    action_buttons.btn_scan.setDefault(True)
    action_buttons.btn_preview.setObjectName("secondary")
    action_buttons.btn_execute.setObjectName("primary")
    action_buttons.btn_cancel.setObjectName("danger")

    for btn in (
        action_buttons.btn_scan,
        action_buttons.btn_preview,
        action_buttons.btn_execute,
        action_buttons.btn_execute_convert,
        action_buttons.btn_audit,
        action_buttons.btn_export_audit_csv,
        action_buttons.btn_export_audit_json,
        action_buttons.btn_export_scan_csv,
        action_buttons.btn_export_scan_json,
        action_buttons.btn_export_plan_csv,
        action_buttons.btn_export_plan_json,
        action_buttons.btn_export_frontend_es,
        action_buttons.btn_export_frontend_launchbox,
        action_buttons.btn_resume,
        action_buttons.btn_retry_failed,
        action_buttons.btn_cancel,
    ):
        btn.setMinimumHeight(28)
        if btn in (action_buttons.btn_scan, action_buttons.btn_preview, action_buttons.btn_execute):
            btn.setMinimumWidth(200)

    action_buttons.btn_cancel.setEnabled(False)
    action_buttons.btn_resume.setEnabled(False)
    action_buttons.btn_retry_failed.setEnabled(False)

    button_row.addWidget(action_buttons.btn_scan, 0, 0)
    button_row.addWidget(action_buttons.btn_preview, 0, 1)
    button_row.addWidget(action_buttons.btn_execute, 0, 2)
    button_row.addWidget(action_buttons.btn_resume, 1, 0)
    button_row.addWidget(action_buttons.btn_retry_failed, 1, 1)
    button_row.addWidget(action_buttons.btn_cancel, 1, 2)
    button_row.setColumnStretch(3, 1)
